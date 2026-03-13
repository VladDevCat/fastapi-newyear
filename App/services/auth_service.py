import uuid
from urllib.parse import urlencode

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.exceptions import (
    AppException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    generate_random_token,
    generate_state,
    hash_password,
    hash_token,
    verify_password,
)
from app.repositories.oauth_state_repository import OAuthStateRepository
from app.repositories.password_reset_repository import PasswordResetRepository
from app.repositories.session_token_repository import SessionTokenRepository
from app.repositories.user_repository import UserRepository
from app.schemas.auth import (
    AuthSessionResultDTO,
    ForgotPasswordDTO,
    ForgotPasswordResponseDTO,
    LoginDTO,
    RegisterDTO,
    ResetPasswordDTO,
)
from app.schemas.user import UserPublicDTO


class AuthService:
    def __init__(self, db: Session):
        self.db = db
        self.users = UserRepository(db)
        self.tokens = SessionTokenRepository(db)
        self.oauth_states = OAuthStateRepository(db)
        self.password_resets = PasswordResetRepository(db)

    def _issue_session_for_user(self, user_id: uuid.UUID) -> AuthSessionResultDTO:
        user = self.users.get_active_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        session_id = uuid.uuid4()
        access_token_id = uuid.uuid4()
        refresh_token_id = uuid.uuid4()

        access_token, access_expires_at = create_access_token(
            user_id=user.id,
            session_id=session_id,
            token_id=access_token_id,
        )
        refresh_token, refresh_expires_at = create_refresh_token(
            user_id=user.id,
            session_id=session_id,
            token_id=refresh_token_id,
        )

        self.tokens.create_token(
            token_id=access_token_id,
            session_id=session_id,
            user_id=user.id,
            token_type="access",
            token_hash=hash_token(access_token),
            expires_at=access_expires_at,
        )
        self.tokens.create_token(
            token_id=refresh_token_id,
            session_id=session_id,
            user_id=user.id,
            token_type="refresh",
            token_hash=hash_token(refresh_token),
            expires_at=refresh_expires_at,
        )

        self.db.commit()
        self.db.refresh(user)

        return AuthSessionResultDTO(
            user=UserPublicDTO.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def register(self, payload: RegisterDTO) -> AuthSessionResultDTO:
        email = payload.email.lower().strip()
        existing = self.users.get_active_by_email(email)
        if existing is not None:
            raise ConflictException("User with this email already exists")

        password_hash, password_salt = hash_password(payload.password)

        user = self.users.create(
            {
                "email": email,
                "password_hash": password_hash,
                "password_salt": password_salt,
            }
        )

        return self._issue_session_for_user(user.id)

    def login(self, payload: LoginDTO) -> AuthSessionResultDTO:
        email = payload.email.lower().strip()
        user = self.users.get_active_by_email(email)
        if user is None:
            raise UnauthorizedException("Invalid email or password")

        if not user.password_hash or not user.password_salt:
            raise UnauthorizedException("This user does not have a local password")

        is_valid = verify_password(
            payload.password,
            user.password_salt,
            user.password_hash,
        )
        if not is_valid:
            raise UnauthorizedException("Invalid email or password")

        return self._issue_session_for_user(user.id)

    def refresh_session(self, refresh_token: str) -> AuthSessionResultDTO:
        payload = decode_refresh_token(refresh_token)

        try:
            token_id = uuid.UUID(payload["jti"])
            session_id = uuid.UUID(payload["sid"])
            user_id = uuid.UUID(payload["sub"])
        except (KeyError, ValueError):
            raise UnauthorizedException("Invalid refresh token payload")

        token_record = self.tokens.get_valid_token(
            token_id=token_id,
            token_hash=hash_token(refresh_token),
            token_type="refresh",
        )
        if token_record is None:
            raise UnauthorizedException("Refresh token revoked or not found")

        user = self.users.get_active_by_id(user_id)
        if user is None:
            raise UnauthorizedException("User not found")

        self.tokens.revoke_by_session_id(session_id)
        return self._issue_session_for_user(user.id)

    def logout_current_session(self, session_id: uuid.UUID) -> None:
        self.tokens.revoke_by_session_id(session_id)
        self.db.commit()

    def logout_all_sessions(self, user_id: uuid.UUID) -> None:
        self.tokens.revoke_all_for_user(user_id)
        self.db.commit()

    def forgot_password(self, payload: ForgotPasswordDTO) -> ForgotPasswordResponseDTO:
        email = payload.email.lower().strip()
        user = self.users.get_active_by_email(email)

        if user is None:
            return ForgotPasswordResponseDTO(
                message="If the account exists, a reset instruction has been generated"
            )

        raw_token = generate_random_token()
        token_hash = hash_token(raw_token)
        expires_at = settings.reset_password_ttl

        self.password_resets.mark_all_used_for_user(user.id)
        self.password_resets.create(
            {
                "user_id": user.id,
                "token_hash": token_hash,
                "expires_at": __import__("datetime").datetime.now(__import__("datetime").timezone.utc) + expires_at,
            }
        )
        self.db.commit()

        if settings.AUTH_DEBUG_RETURN_RESET_TOKEN:
            return ForgotPasswordResponseDTO(
                message="Reset token generated",
                reset_token=raw_token,
            )

        return ForgotPasswordResponseDTO(
            message="If the account exists, a reset instruction has been generated"
        )

    def reset_password(self, payload: ResetPasswordDTO) -> None:
        token_hash = hash_token(payload.token)
        reset_record = self.password_resets.get_valid_token(token_hash)
        if reset_record is None:
            raise UnauthorizedException("Invalid or expired reset token")

        user = self.users.get_active_by_id(reset_record.user_id)
        if user is None:
            raise NotFoundException("User not found")

        password_hash, password_salt = hash_password(payload.new_password)
        self.users.update(
            user,
            {
                "password_hash": password_hash,
                "password_salt": password_salt,
            },
        )
        self.password_resets.mark_used(reset_record)
        self.tokens.revoke_all_for_user(user.id)
        self.db.commit()

    def get_oauth_redirect_url(self, provider: str) -> str:
        if provider != "yandex":
            raise NotFoundException("OAuth provider not supported")

        if not settings.YANDEX_CLIENT_ID or not settings.YANDEX_CLIENT_SECRET:
            raise AppException("Yandex OAuth is not configured")

        raw_state = generate_state()
        state_hash = hash_token(raw_state)

        from datetime import datetime, timezone

        self.oauth_states.create(
            {
                "provider": provider,
                "state_hash": state_hash,
                "expires_at": datetime.now(timezone.utc) + settings.oauth_state_ttl,
            }
        )
        self.db.commit()

        query = urlencode(
            {
                "response_type": "code",
                "client_id": settings.YANDEX_CLIENT_ID,
                "redirect_uri": settings.YANDEX_CALLBACK_URL,
                "state": raw_state,
            }
        )

        return f"https://oauth.yandex.com/authorize?{query}"

    def handle_yandex_callback(self, code: str, state: str) -> AuthSessionResultDTO:
        if not settings.YANDEX_CLIENT_ID or not settings.YANDEX_CLIENT_SECRET:
            raise AppException("Yandex OAuth is not configured")

        state_hash = hash_token(state)
        state_record = self.oauth_states.get_valid_state("yandex", state_hash)
        if state_record is None:
            raise UnauthorizedException("Invalid or expired OAuth state")

        self.oauth_states.mark_used(state_record)

        token_response = httpx.post(
            "https://oauth.yandex.com/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": settings.YANDEX_CLIENT_ID,
                "client_secret": settings.YANDEX_CLIENT_SECRET,
            },
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            timeout=20.0,
        )

        if token_response.status_code >= 400:
            raise UnauthorizedException("Failed to exchange OAuth code")

        token_data = token_response.json()
        provider_access_token = token_data.get("access_token")
        if not provider_access_token:
            raise UnauthorizedException("Provider access token not received")

        userinfo_response = httpx.get(
            "https://login.yandex.ru/info",
            headers={"Authorization": f"OAuth {provider_access_token}"},
            params={"format": "json"},
            timeout=20.0,
        )

        if userinfo_response.status_code >= 400:
            raise UnauthorizedException("Failed to fetch Yandex user info")

        profile = userinfo_response.json()
        yandex_id = profile.get("id")
        email = profile.get("default_email")

        if not yandex_id:
            raise UnauthorizedException("Yandex user ID not found in profile")

        if not email:
            raise UnauthorizedException("Yandex profile did not return email")

        user = self.users.get_by_yandex_id(yandex_id)

        if user is None:
            existing_by_email = self.users.get_active_by_email(email.lower().strip())
            if existing_by_email is not None:
                user = self.users.update(
                    existing_by_email,
                    {"yandex_id": yandex_id},
                )
            else:
                user = self.users.create(
                    {
                        "email": email.lower().strip(),
                        "yandex_id": yandex_id,
                    }
                )
            self.db.commit()
            self.db.refresh(user)

        return self._issue_session_for_user(user.id)