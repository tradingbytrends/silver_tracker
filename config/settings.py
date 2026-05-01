import os
import random
from dotenv import load_dotenv

load_dotenv()


class Settings:
    # Angel One credentials
    ANGEL_API_KEY: str = os.getenv("ANGEL_API_KEY", "")
    ANGEL_CLIENT_CODE: str = os.getenv("ANGEL_CLIENT_CODE", "")
    ANGEL_PASSWORD: str = os.getenv("ANGEL_PASSWORD", "")
    ANGEL_TOTP_SECRET: str = os.getenv("ANGEL_TOTP_SECRET", "")

    # Silver instrument
    SILVER_SYMBOL: str = os.getenv("SILVER_SYMBOL", "SILVER")
    SILVER_TOKEN: str = os.getenv("SILVER_TOKEN", "234230")
    SILVER_EXCHANGE: str = os.getenv("SILVER_EXCHANGE", "MCX")

    # Twilio / WhatsApp
    TWILIO_ACCOUNT_SID: str = os.getenv("TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("TWILIO_AUTH_TOKEN", "")
    TWILIO_WHATSAPP_FROM: str = os.getenv("TWILIO_WHATSAPP_FROM", "whatsapp:+14155238886")
    WHATSAPP_TO: str = os.getenv("WHATSAPP_TO", "")

    # Scheduling
    NOTIFICATION_INTERVAL_MIN: int = int(os.getenv("NOTIFICATION_INTERVAL_MIN", "15"))
    NOTIFICATION_INTERVAL_MAX: int = int(os.getenv("NOTIFICATION_INTERVAL_MAX", "20"))
    PRICE_FETCH_INTERVAL: int = int(os.getenv("PRICE_FETCH_INTERVAL", "60"))

    # Storage
    DB_PATH: str = os.getenv("DB_PATH", "data/silver_prices.db")

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")

    @classmethod
    def notification_interval_seconds(cls) -> int:
        minutes = random.randint(cls.NOTIFICATION_INTERVAL_MIN, cls.NOTIFICATION_INTERVAL_MAX)
        return minutes * 60

    @classmethod
    def validate(cls) -> None:
        missing = []
        required = [
            ("ANGEL_API_KEY", cls.ANGEL_API_KEY),
            ("ANGEL_CLIENT_CODE", cls.ANGEL_CLIENT_CODE),
            ("ANGEL_PASSWORD", cls.ANGEL_PASSWORD),
            ("ANGEL_TOTP_SECRET", cls.ANGEL_TOTP_SECRET),
        ]
        for name, value in required:
            if not value:
                missing.append(name)
        if missing:
            raise EnvironmentError(
                f"Missing required environment variables: {', '.join(missing)}\n"
                "Copy .env.example to .env and fill in your credentials."
            )


settings = Settings()
