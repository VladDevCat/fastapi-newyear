from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.common.exceptions import AppException


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppException)
    async def app_exception_handler(_: Request, exc: AppException):
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(_: Request, exc: RequestValidationError):
        return JSONResponse(
            status_code=400,
            content={
                "detail": "Bad Request",
                "errors": exc.errors(),
            },
        )

    @app.exception_handler(Exception)
    async def internal_exception_handler(_: Request, exc: Exception):
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Server Error"},
        )