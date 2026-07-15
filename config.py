"""
config.py
Loads environment variables and exposes them as typed settings.
"""

import os
from dotenv import load_dotenv

load_dotenv()


class Settings:
    DATABASE_URL: str = os.getenv("DATABASE_URL", "")
    FIREBASE_SERVICE_ACCOUNT_PATH: str = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_PATH", "firebase-service-account.json"
    )
    FIREBASE_SERVICE_ACCOUNT_JSON: str = os.getenv(
        "FIREBASE_SERVICE_ACCOUNT_JSON", ""
    )
    API_KEY: str = os.getenv("API_KEY", "")


settings = Settings()
