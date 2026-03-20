from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

TAGS_METADATA = [
    {
        "name": "Auth",
        "description": "Регистрация, вход, обновление сессии, OAuth, whoami, logout, reset password.",
    },
    {
        "name": "Items",
        "description": "CRUD операции с основным ресурсом HolidayItem. Доступ только для авторизованных пользователей.",
    },
]

BAD_REQUEST_EXAMPLE = {
    "detail": "Bad Request",
    "errors": [
        {
            "type": "string_too_short",
            "loc": ["body", "password"],
            "msg": "String should have at least 8 characters",
            "input": "123",
        }
    ],
}

UNAUTHORIZED_EXAMPLE = {
    "detail": "Missing access token"
}

FORBIDDEN_EXAMPLE = {
    "detail": "You do not have access to this item"
}

NOT_FOUND_EXAMPLE = {
    "detail": "Item not found"
}

INTERNAL_ERROR_EXAMPLE = {
    "detail": "Internal Server Error"
}


def json_example(example: dict, description: str = "") -> dict:
    return {
        "description": description,
        "content": {
            "application/json": {
                "example": example
            }
        },
    }


def build_custom_openapi(app: FastAPI):
    def custom_openapi():
        if app.openapi_schema:
            return app.openapi_schema

        openapi_schema = get_openapi(
            title="Lab Project API",
            version="1.0.0",
            summary="Документация API для лабораторных работ №2–№4",
            description=(
                "Автоматически сгенерированная OpenAPI-документация. "
                "Приложение использует JWT в HttpOnly cookies, а также OAuth 2.0 через Yandex."
            ),
            routes=app.routes,
        )

        openapi_schema.setdefault("components", {})
        openapi_schema["components"].setdefault("securitySchemes", {})

        openapi_schema["components"]["securitySchemes"]["cookieAuth"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": "access_token",
            "description": (
                "Основная схема для защищённых методов. "
                "Реальное приложение использует HttpOnly cookies. "
                "Для тестирования сначала вызовите /auth/login или пройдите OAuth-вход."
            ),
        }



        openapi_schema["components"]["securitySchemes"]["yandexOAuth"] = {
            "type": "oauth2",
            "flows": {
                "authorizationCode": {
                    "authorizationUrl": "https://oauth.yandex.com/authorize",
                    "tokenUrl": "https://oauth.yandex.com/token",
                    "scopes": {
                        "login:info": "Доступ к базовой информации профиля",
                        "login:email": "Доступ к email пользователя",
                    },
                }
            },
        }

        app.openapi_schema = openapi_schema
        return app.openapi_schema

    return custom_openapi
