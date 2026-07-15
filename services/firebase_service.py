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
    platform: str = "web",
) -> Dict[str, Any]:
    """
    Send a push notification to a single FCM token.

    Behaviour differs by platform:
      - web:     data-only WebpushConfig (no notification field) so the service
                 worker always controls the notification and navigation data is
                 available in the notificationclick handler.
      - android: AndroidConfig with both a Notification block (so the OS shows
                 it automatically when the app is background/killed) AND a data
                 payload (so the app can navigate on tap).

    Returns:
        {"success": True,  "message_id": "<fcm-message-id>"}
        {"success": False, "error": "<error description>"}
    """
    if not _firebase_initialised:
        return {"success": False, "error": "Firebase not initialised"}

    # Build data dict — all values MUST be plain strings for FCM.
    data_payload: Dict[str, str] = {
        "screen_name": screen_name,
        "title":       title,
        "body":        body,
    }
    if extra_data:
        for k, v in extra_data.items():
            data_payload[str(k)] = str(v) if not isinstance(v, str) else v

    if platform == "android":
        # Android: include a visible Notification so the OS shows it when the
        # app is in background/killed. Data payload is also included so the
        # app can deep-link on tap via onNotificationOpenedApp / getInitialNotification.
        message = messaging.Message(
            data=data_payload,
            token=token,
            android=messaging.AndroidConfig(
                priority="high",
                notification=messaging.AndroidNotification(
                    title=title,
                    body=body,
                    sound="default",
                    # channel_id must match a channel created in the app.
                    # React Native Firebase auto-creates a default channel.
                    channel_id="default",
                ),
            ),
        )
    else:
        # Web: data-only message — service worker handles display so navigation
        # data is always available in the notificationclick handler.
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
