import uuid
from datetime import datetime, timezone

from app.common.cache import cache
from app.common.config import settings
from app.common.exceptions import (
    AppException,
    ConflictException,
    NotFoundException,
    UnauthorizedException,
)
from app.common.security.hashes import generate_random_token, generate_state, hash_token
from app.common.security.jwt import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
)
from app.common.security.passwords import verify_password
from app.modules.auth.oauth_state_repository import OAuthStateRepository
from app.modules.auth.reset_token_repository import PasswordResetRepository
from app.modules.auth.schemas import (
    AuthSessionResultDTO,
    ForgotPasswordDTO,
    ForgotPasswordResponseDTO,
    LoginDTO,
    RegisterDTO,
    ResetPasswordDTO,
)
from app.modules.auth.token_repository import SessionTokenRepository
from app.modules.auth.yandex_oauth import YandexOAuthClient
from app.modules.users.schemas import UserPublicDTO
from app.modules.users.service import UsersService


class AuthService:
    def __init__(self, db):
        self.db = db
        self.users = UsersService(db)
        self.tokens = SessionTokenRepository(db)
        self.oauth_states = OAuthStateRepository(db)
        self.password_resets = PasswordResetRepository(db)
        self.yandex = YandexOAuthClient()

    def _access_jti_key(self, user_id: uuid.UUID, token_id: uuid.UUID) -> str:
        return cache.key("auth", "user", user_id, "access", token_id)

    def _store_access_jti(
        self,
        *,
        user_id: uuid.UUID,
        token_id: uuid.UUID,
        expires_at: datetime,
    ) -> None:
        ttl = max(1, int((expires_at - datetime.now(timezone.utc)).total_seconds()))
        cache.set(self._access_jti_key(user_id, token_id), "valid", ttl)

    def is_access_jti_valid(self, user_id: uuid.UUID, token_id: uuid.UUID) -> bool | None:
        if not cache.is_available():
            return None
        return cache.get(self._access_jti_key(user_id, token_id)) is not None

    def _delete_access_jti(self, user_id: uuid.UUID, token_id: uuid.UUID) -> None:
        cache.del_key(self._access_jti_key(user_id, token_id))

    def _delete_access_jtis_for_session(self, user_id: uuid.UUID, session_id: uuid.UUID) -> None:
        access_tokens = self.tokens.list_valid_tokens_by_session(
            session_id=session_id,
            token_type="access",
        )
        for token in access_tokens:
            self._delete_access_jti(user_id, token.id)

    def _delete_all_access_jtis_for_user(self, user_id: uuid.UUID) -> None:
        cache.delByPattern(cache.key("auth", "user", user_id, "access", "*"))

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
        self._store_access_jti(
            user_id=user.id,
            token_id=access_token_id,
            expires_at=access_expires_at,
        )

        return AuthSessionResultDTO(
            user=UserPublicDTO.model_validate(user),
            access_token=access_token,
            refresh_token=refresh_token,
        )

    def register(self, payload: RegisterDTO) -> AuthSessionResultDTO:
        existing = self.users.get_active_by_email(payload.email)
        if existing is not None:
            raise ConflictException("User with this email already exists")

        user = self.users.create_local_user(payload.email, payload.password)
        return self._issue_session_for_user(user.id)

    def login(self, payload: LoginDTO) -> AuthSessionResultDTO:
        user = self.users.get_active_by_email(payload.email)
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
        self._delete_access_jtis_for_session(user.id, session_id)
        return self._issue_session_for_user(user.id)

    def logout_current_session(self, session_id: uuid.UUID, user_id: uuid.UUID) -> None:
        self._delete_access_jtis_for_session(user_id, session_id)
        self.tokens.revoke_by_session_id(session_id)
        self.db.commit()

    def logout_all_sessions(self, user_id: uuid.UUID) -> None:
        self._delete_all_access_jtis_for_user(user_id)
        self.tokens.revoke_all_for_user(user_id)
        self.db.commit()

    def forgot_password(self, payload: ForgotPasswordDTO) -> ForgotPasswordResponseDTO:
        user = self.users.get_active_by_email(payload.email)

        if user is None:
            return ForgotPasswordResponseDTO(
                message="If the account exists, a reset instruction has been generated"
            )

        raw_token = generate_random_token()
        token_hash = hash_token(raw_token)

        self.password_resets.mark_all_used_for_user(user.id)
        self.password_resets.create(
            {
                "user_id": user.id,
                "token_hash": token_hash,
                "expires_at": datetime.now(timezone.utc) + settings.reset_password_ttl,
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

        self.users.update_password(user, payload.new_password)
        self.password_resets.mark_used(reset_record)
        self._delete_all_access_jtis_for_user(user.id)
        self.tokens.revoke_all_for_user(user.id)
        self.db.commit()

    def get_oauth_redirect_url(self, provider: str) -> str:
        if provider != "yandex":
            raise NotFoundException("OAuth provider not supported")

        raw_state = generate_state()
        state_hash = hash_token(raw_state)

        self.oauth_states.create(
            {
                "provider": provider,
                "state_hash": state_hash,
                "expires_at": datetime.now(timezone.utc) + settings.oauth_state_ttl,
            }
        )
        self.db.commit()

        return self.yandex.build_authorize_url(raw_state)

    def handle_oauth_callback(self, provider: str, code: str, state: str) -> AuthSessionResultDTO:
        if provider != "yandex":
            raise NotFoundException("OAuth provider not supported")

        state_hash = hash_token(state)
        state_record = self.oauth_states.get_valid_state(provider, state_hash)
        if state_record is None:
            raise UnauthorizedException("Invalid or expired OAuth state")

        self.oauth_states.mark_used(state_record)

        token_data = self.yandex.exchange_code(code)
        provider_access_token = token_data["access_token"]

        profile = self.yandex.fetch_user_info(provider_access_token)
        yandex_id = profile["id"]
        email = profile["default_email"].lower().strip()

        user = self.users.get_by_yandex_id(yandex_id)

        if user is None:
            existing_by_email = self.users.get_active_by_email(email)
            if existing_by_email is not None:
                user = self.users.link_yandex_account(existing_by_email, yandex_id)
            else:
                user = self.users.create_oauth_user(email, yandex_id)
            self.db.commit()
            self.db.refresh(user)

        return self._issue_session_for_user(user.id)
