from fastapi import FastAPI

from app.common.config import settings
from app.common.db import create_indexes
from app.common.web.error_handlers import register_exception_handlers
from app.common.web.openapi import TAGS_METADATA, build_custom_openapi
from app.modules.auth.router import router as auth_router
from app.modules.items.router import router as items_router
from app.modules.storage.profile_router import router as profile_router
from app.modules.storage.router import router as files_router

app = FastAPI(
    title=settings.APP_NAME,
    openapi_url="/api/openapi.json" if settings.docs_enabled else None,
    docs_url="/api/docs" if settings.docs_enabled else None,
    redoc_url=None,
    openapi_tags=TAGS_METADATA,
    swagger_ui_parameters={
        "displayRequestDuration": True,
        "tryItOutEnabled": True,
    } if settings.docs_enabled else None,
    swagger_ui_oauth2_redirect_url="/api/docs/oauth2-redirect" if settings.docs_enabled else None,
    swagger_ui_init_oauth={
        "appName": "Holiday Prep API Docs",
        "clientId": settings.YANDEX_CLIENT_ID,
        "scopes": "login:info login:email",
        "usePkceWithAuthorizationCodeGrant": False,
    } if settings.docs_enabled else None,
)

register_exception_handlers(app)

if settings.docs_enabled:
    app.openapi = build_custom_openapi(app)


@app.on_event("startup")
def startup() -> None:
    create_indexes()


@app.get("/info", tags=["System"], summary="Проверка базового статуса приложения")
def get_info():
    return {"message": "LR1 endpoint is still alive"}


app.include_router(auth_router)
app.include_router(items_router)
app.include_router(files_router)
app.include_router(profile_router)
