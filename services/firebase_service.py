"""
services/firebase_service.py
Initialises the Firebase Admin SDK (once) and exposes a helper that sends
a single FCM web-push notification.
"""

import os
import json
import tempfile
from typing import Any, Dict, Optional

import firebase_admin
from firebase_admin import credentials, messaging

from config import settings

# ── Singleton initialisation ───────────────────────────────────────────────────

_firebase_initialised = False


def init_firebase() -> bool:
    """
    Initialise the Firebase Admin SDK.
    Supports two methods (in order of priority):
      1. FIREBASE_SERVICE_ACCOUNT_JSON env var — JSON string of the service account
      2. FIREBASE_SERVICE_ACCOUNT_PATH env var — path to the JSON file on disk
    Safe to call multiple times – returns True when ready.
    """
    global _firebase_initialised

    if _firebase_initialised:
        return True

    cred = None

    # Method 1: JSON string in env var (preferred for cloud deployments)
    sa_json = settings.FIREBASE_SERVICE_ACCOUNT_JSON
    if sa_json:
        try:
            sa_dict = json.loads(sa_json)
            cred = credentials.Certificate(sa_dict)
        except Exception as exc:
            print(f"[Firebase] Failed to parse FIREBASE_SERVICE_ACCOUNT_JSON: {exc}")
            return False

    # Method 2: File path on disk (local development)
    if cred is None:
        sa_path = settings.FIREBASE_SERVICE_ACCOUNT_PATH
        # Guard: if the value looks like JSON it was set to the wrong env var
        if sa_path.strip().startswith("{"):
            print(
                "[Firebase] ERROR: FIREBASE_SERVICE_ACCOUNT_PATH contains JSON. "
                "Set FIREBASE_SERVICE_ACCOUNT_JSON instead on Render."
            )
            return False
        if os.path.exists(sa_path):
            try:
                cred = credentials.Certificate(sa_path)
            except Exception as exc:
                print(f"[Firebase] Failed to load service account file: {exc}")
                return False
        else:
            print(
                "[Firebase] WARNING: No service account configured. "
                "Set FIREBASE_SERVICE_ACCOUNT_JSON env var on Render, "
                f"or place the file at '{sa_path}' for local dev. "
                "Push notifications will not work."
            )
            return False

    try:
        firebase_admin.initialize_app(cred)
        _firebase_initialised = True
        print("[Firebase] Admin SDK initialised successfully.")
        return True
    except Exception as exc:
        print(f"[Firebase] Initialisation error: {exc}")
        return False


def is_firebase_ready() -> bool:
    return _firebase_initialised


# ── Send a single notification ─────────────────────────────────────────────────

def send_fcm_notification(
    token: str,
    title: str,
    body: str,
    screen_name: str,
    extra_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Send a push notification to a single FCM token.

    The notification payload includes:
      - Standard visible notification (title + body)
      - Data payload with screen_name + any extra_data so the
        frontend service-worker can navigate to the correct screen on tap.

    Returns:
        {"success": True,  "message_id": "<fcm-message-id>"}
        {"success": False, "error": "<error description>"}
    """
    if not _firebase_initialised:
        return {"success": False, "error": "Firebase not initialised"}

    # Build data dict — all values MUST be plain strings for FCM.
    # Do NOT json.dumps strings — keep them as-is so the SW receives clean values.
    data_payload: Dict[str, str] = {
        "screen_name": screen_name,
        "title":       title,
        "body":        body,
    }
    if extra_data:
        for k, v in extra_data.items():
            # Convert to string but never double-encode a plain string
            data_payload[str(k)] = str(v) if not isinstance(v, str) else v

    # Use a DATA-ONLY webpush message (no notification field).
    # This forces the SW onBackgroundMessage handler to always run,
    # which means `data` is always available in the notificationclick handler.
    # If we include a `notification` field, Chrome shows it natively and
    # the click handler receives no data — navigation breaks.
    message = messaging.Message(
        data=data_payload,
        token=token,
        webpush=messaging.WebpushConfig(
            headers={"Urgency": "high"},
        ),
    )

    try:
        message_id = messaging.send(message)
        return {"success": True, "message_id": message_id}
    except messaging.UnregisteredError:
        return {"success": False, "error": "Token unregistered – remove from DB"}
    except messaging.SenderIdMismatchError:
        return {"success": False, "error": "Sender ID mismatch"}
    except Exception as exc:
        return {"success": False, "error": str(exc)}
