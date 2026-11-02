import os

import boto3
from botocore.exceptions import BotoCoreError, ClientError
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

router = APIRouter(prefix="/api/v1/auth", tags=["authentication"])


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=256)
    password: str = Field(min_length=1, max_length=256)


def get_setting(name: str, default=None):
    environment_value = os.getenv(name.upper())

    if environment_value is not None:
        return environment_value

    try:
        from app.core.config import settings
        return getattr(settings, name, default)
    except (ImportError, AttributeError):
        return default


def cognito_client():
    app_env = str(get_setting("app_env", "local")).lower()

    client_options = {
        "region_name": get_setting("aws_region", "us-east-1"),
    }

    if app_env in {"local", "development"}:
        endpoint = get_setting("floci_endpoint")

        if endpoint:
            client_options["endpoint_url"] = endpoint

        access_key = get_setting("aws_access_key_id")
        secret_key = get_setting("aws_secret_access_key")

        if access_key and secret_key:
            client_options["aws_access_key_id"] = access_key
            client_options["aws_secret_access_key"] = secret_key

    return boto3.client("cognito-idp", **client_options)


@router.post("/login")
def login(payload: LoginRequest):
    client_id = get_setting("cognito_app_client_id")

    if not client_id:
        raise HTTPException(
            status_code=503,
            detail="Cognito authentication is not configured.",
        )

    try:
        response = cognito_client().initiate_auth(
            AuthFlow="USER_PASSWORD_AUTH",
            ClientId=client_id,
            AuthParameters={
                "USERNAME": payload.username,
                "PASSWORD": payload.password,
            },
        )

        authentication = response.get("AuthenticationResult")

        if not authentication:
            challenge = response.get("ChallengeName", "unknown")
            raise HTTPException(
                status_code=401,
                detail=f"Additional sign-in step required: {challenge}",
            )

        return {
            "access_token": authentication["AccessToken"],
            "expires_in": authentication.get("ExpiresIn", 3600),
            "token_type": authentication.get("TokenType", "Bearer"),
        }

    except HTTPException:
        raise

    except ClientError as exc:
        code = exc.response.get("Error", {}).get("Code", "")

        if code in {
            "NotAuthorizedException",
            "UserNotFoundException",
            "PasswordResetRequiredException",
        }:
            raise HTTPException(
                status_code=401,
                detail="Invalid username or password.",
            ) from exc

        if code == "UserNotConfirmedException":
            raise HTTPException(
                status_code=403,
                detail="This account has not been confirmed.",
            ) from exc

        raise HTTPException(
            status_code=400,
            detail="Cognito could not complete authentication.",
        ) from exc

    except BotoCoreError as exc:
        raise HTTPException(
            status_code=503,
            detail="Unable to reach the Cognito service.",
        ) from exc
