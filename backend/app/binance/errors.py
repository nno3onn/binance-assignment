class BinanceRestClientError(Exception):
    """Base exception for Binance REST client failures."""


class BinanceTimeoutError(BinanceRestClientError):
    """Raised when Binance REST request times out after retries."""


class BinanceNetworkError(BinanceRestClientError):
    """Raised when Binance REST request fails due to network errors after retries."""


class BinanceRateLimitError(BinanceRestClientError):
    """Raised when Binance REST returns 429 after retries."""


class BinanceHttpClientError(BinanceRestClientError):
    """Raised for non-retryable 4xx responses."""


class BinanceHttpServerError(BinanceRestClientError):
    """Raised for retryable 5xx responses after retries."""


class BinanceInvalidResponseError(BinanceRestClientError):
    """Raised when Binance REST response shape cannot be parsed."""
