class ServiceError(Exception):
    def __init__(self, code: str, *, retry_after: int = 0):
        self.code = code
        self.retry_after = min(max(retry_after, 0), 3600)
        super().__init__(code)


class AmbiguousSend(ServiceError):
    """Request may have reached the messaging provider. Never blindly resend."""


class TwilioSendError(ServiceError):
    """Allowlisted diagnostics only; never retain the provider response or request."""

    def __init__(self, code, *, http_status=None, twilio_error_code=None, retry_after=0):
        self.http_status = (
            http_status if type(http_status) is int and 100 <= http_status <= 599 else None
        )
        self.twilio_error_code = (
            twilio_error_code
            if type(twilio_error_code) is int and 0 < twilio_error_code <= 999999
            else None
        )
        super().__init__(code, retry_after=retry_after)


class TwilioUncertainSend(TwilioSendError, AmbiguousSend):
    """Keep safe Twilio diagnostics while preserving the no-resend policy."""
