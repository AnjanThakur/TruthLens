class ServiceError(Exception):
    def __init__(self, code: str, *, retry_after: int = 0):
        self.code = code
        self.retry_after = min(max(retry_after, 0), 3600)
        super().__init__(code)


class AmbiguousSend(ServiceError):
    """Request may have reached Meta. Never blindly resend."""
