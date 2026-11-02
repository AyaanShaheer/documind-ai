import logging
from functools import lru_cache

import jwt

from fastapi import Depends, HTTPException, status
from fastapi.security import (
    HTTPAuthorizationCredentials,
    HTTPBearer,
)

from jwt import PyJWKClient
from jwt.exceptions import (
    InvalidTokenError,
    PyJWKClientConnectionError,
    PyJWKClientError,
)

from app.core.config import settings


logger = logging.getLogger(__name__)

bearer_scheme = HTTPBearer(
    auto_error=False,
    scheme_name="CognitoAccessToken",
)


@lru_cache(maxsize=1)
def get_jwks_client() -> PyJWKClient:
    """
    Create a cached JWKS client.

    Public signing keys are cached for five minutes.
    """

    if not settings.cognito_jwks_url:
        raise RuntimeError(
            "COGNITO_JWKS_URL is not configured"
        )

    return PyJWKClient(
        settings.cognito_jwks_url,
        cache_jwk_set=True,
        lifespan=300,
        timeout=5,
    )


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials | None = Depends(
        bearer_scheme
    ),
) -> str:
    """
    Verify a Cognito access token and return its immutable
    Cognito subject identifier.

    Security checks:
    - JWT signature using RS256.
    - Expected issuer.
    - Expiration and issued-at claims.
    - Required claims.
    - Access token only.
    - Expected app client ID.

    Never trusts an X-User-Id request header.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Bearer authentication is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unsupported authentication scheme",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not all([
        settings.cognito_user_pool_id,
        settings.cognito_app_client_id,
        settings.cognito_issuer,
        settings.cognito_jwks_url,
    ]):
        logger.error(
            "Cognito authentication configuration is incomplete"
        )

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication provider is not configured",
        )

    token = credentials.credentials

    try:
        jwks_client = get_jwks_client()

        signing_key = (
            jwks_client.get_signing_key_from_jwt(token)
        )

    except PyJWKClientConnectionError as exc:
        logger.error("Unable to retrieve Cognito signing keys")

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Identity provider signing keys unavailable",
        ) from exc

    except PyJWKClientError as exc:
        logger.warning("Unable to identify JWT signing key")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    try:
        claims = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            issuer=settings.cognito_issuer,
            options={
                "verify_aud": False,
                "require": [
                    "exp",
                    "iat",
                    "iss",
                    "sub",
                    "token_use",
                    "client_id",
                ],
            },
        )

    except InvalidTokenError as exc:
        logger.warning("Cognito JWT validation failed")

        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        ) from exc

    # Only Cognito access tokens are accepted by this API.
    if claims.get("token_use") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="An access token is required",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Access tokens use client_id rather than the ID token's aud.
    if claims.get("client_id") != settings.cognito_app_client_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token was issued to an untrusted application",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = claims.get("sub")

    if not isinstance(user_id, str) or not user_id.strip():
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid user identity in token",
        )

    logger.debug(
        "Authenticated Cognito user: %s",
        user_id,
    )

    return user_id
