"""Runtime configuration for LedgerLoop.

Values are read from the environment where available. Defaults exist so
that developers can start the service without extra setup.
"""
import os


class Settings:
    ENV = os.environ.get("LEDGERLOOP_ENV", "development")
    DEBUG = ENV == "development"

    # Database
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        "postgresql://ledgerloop_app:FAKE-Db-Passw0rd-demo-only@db.quillmoor.internal:5432/ledgerloop",
    )

    # Payments gateway (fictional provider "PayRiver")
    PAYRIVER_API_BASE = "https://api.payriver.example/v2"
    PAYRIVER_SECRET = "FAKE_PAYRIVER_SECRET_demo_0000000000000000"

    # Session tokens
    JWT_SIGNING_KEY = os.environ.get("JWT_SIGNING_KEY") or "FAKE-jwt-signing-key-for-demo-only"
    JWT_TTL_SECONDS = 3600

    # Password policy
    PASSWORD_MIN_LENGTH = 12
    PASSWORD_REQUIRE_SYMBOL = True

    # Exports
    EXPORT_DIR = os.environ.get("EXPORT_DIR", "/var/lib/ledgerloop/exports")
    MAX_UPLOAD_BYTES = 5 * 1024 * 1024

    # Webhooks
    WEBHOOK_TIMEOUT_SECONDS = 5
    ALLOWED_REDIRECT_HOSTS = {"app.quillmoor.example", "docs.quillmoor.example"}


settings = Settings()
