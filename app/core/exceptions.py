class AppException(Exception):
    status_code = 400
    detail = "Application error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail


class NotFoundException(AppException):
    status_code = 404
    detail = "Resource not found"


class ConflictException(AppException):
    status_code = 409
    detail = "Conflict"