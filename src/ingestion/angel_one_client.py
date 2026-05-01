import pyotp
from SmartApi import SmartConnect
from logzero import logger

from config.settings import settings


class AngelOneClient:
    """Thin wrapper around SmartConnect that handles auth and session refresh."""

    def __init__(self) -> None:
        self._api = SmartConnect(api_key=settings.ANGEL_API_KEY)
        self._session_data: dict = {}

    def login(self) -> None:
        totp = pyotp.TOTP(settings.ANGEL_TOTP_SECRET).now()
        data = self._api.generateSession(
            settings.ANGEL_CLIENT_CODE,
            settings.ANGEL_PASSWORD,
            totp,
        )
        if data.get("status") is False:
            raise ConnectionError(f"Angel One login failed: {data.get('message')}")
        self._session_data = data["data"]
        logger.info("Angel One login successful")

    def get_candle_data(
        self,
        exchange: str,
        symbol_token: str,
        interval: str,
        from_date: str,
        to_date: str,
    ) -> list[list]:
        """
        Fetch OHLCV candle data.

        interval options: ONE_MINUTE, THREE_MINUTE, FIVE_MINUTE, TEN_MINUTE,
                          FIFTEEN_MINUTE, THIRTY_MINUTE, ONE_HOUR, ONE_DAY
        from_date / to_date format: "YYYY-MM-DD HH:MM"
        Returns list of [timestamp, open, high, low, close, volume]
        """
        params = {
            "exchange": exchange,
            "symboltoken": symbol_token,
            "interval": interval,
            "fromdate": from_date,
            "todate": to_date,
        }
        response = self._api.getCandleData(params)
        if not response.get("status"):
            raise RuntimeError(f"getCandleData failed: {response.get('message')}")
        return response["data"]

    def get_ltp(self, exchange: str, symbol: str, symbol_token: str) -> float:
        """Fetch the last traded price for a symbol."""
        response = self._api.ltpData(exchange, symbol, symbol_token)
        if not response.get("status"):
            raise RuntimeError(f"ltpData failed: {response.get('message')}")
        return float(response["data"]["ltp"])
