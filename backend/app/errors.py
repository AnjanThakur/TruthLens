class AppError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        status: int = 400,
        retry_after_seconds: int | None = None,
        *,
        category: str | None = None,
        provider_status: int | None = None,
    ):
        self.code = code
        self.message = message
        self.status = status
        self.retry_after_seconds = retry_after_seconds
        self.category = category
        self.provider_status = provider_status
        super().__init__(message)
