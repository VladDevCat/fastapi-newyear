class AppException(Exception):
    status_code = 400
    detail = "Application error"

    def __init__(self, detail: str | None = None):
        if detail is not None:
            self.detail = detail


class UnauthorizedException(AppException):
    status_code = 401
    detail = "Unauthorized"


class ForbiddenException(AppException):
    status_code = 403
    detail = "Forbidden"


class NotFoundException(AppException):
    status_code = 404
    detail = "Resource not found"


class ConflictException(AppException):
    status_code = 409
    detail = "Conflict"