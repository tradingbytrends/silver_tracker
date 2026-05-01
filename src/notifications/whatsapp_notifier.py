from datetime import datetime, timezone

from logzero import logger
from twilio.rest import Client

from config.settings import settings
from src.storage.database import Database


class WhatsAppNotifier:
    """Sends silver price alerts via Twilio WhatsApp API."""

    def __init__(self, db: Database) -> None:
        if settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN:
            self._client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
        else:
            self._client = None
            logger.warning("Twilio credentials not set — WhatsApp notifications disabled")
        self._db = db

    def send(self, message: str, price: float, change: float = None, change_pct: float = None) -> bool:
        if not self._client:
            logger.warning("WhatsApp skipped — Twilio credentials not configured")
            return False
        try:
            msg = self._client.messages.create(
                body=message,
                from_=settings.TWILIO_WHATSAPP_FROM,
                to=settings.WHATSAPP_TO,
            )
            logger.info("WhatsApp notification sent: SID=%s", msg.sid)

            self._db.log_notification({
                "sent_at": datetime.now(timezone.utc),
                "price": price,
                "price_change": change,
                "price_change_pct": change_pct,
                "message": message,
                "status": "sent",
            })
            return True

        except Exception as exc:
            logger.error("WhatsApp send failed: %s", exc)
            self._db.log_notification({
                "sent_at": datetime.now(timezone.utc),
                "price": price,
                "price_change": change,
                "price_change_pct": change_pct,
                "message": message,
                "status": f"failed: {exc}",
            })
            return False
