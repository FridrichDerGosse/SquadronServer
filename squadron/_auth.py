"""
Handles everything involved in authentication.

| ``Path``: _auth.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from datetime import datetime, timezone, timedelta
from fastapi.security import OAuth2PasswordBearer
from fastapi import HTTPException
from argon2 import PasswordHasher
from typing import Annotated
from fastapi import Depends
import asyncio
import jwt

from ._constants import TOKEN_EXPIRE_MINUTES, SECRET_KEY
from ._constants import JWT_ALGORITHM
from ._user_data import user_manager


# single global instance
AUTH_PW_HASHER = PasswordHasher()
OAUTH2_SCHEME = OAuth2PasswordBearer(tokenUrl="login")


def create_token(
        username: str,
        expires_in: int = TOKEN_EXPIRE_MINUTES
) -> str:
    """
    Generate acces token for user

    :param username: username to generate token for
    :param expires_in: time until expiration
    :return: valid token
    """
    return jwt.encode(
        {
            "sub": username,
            "exp": datetime.now(timezone.utc)
                + timedelta(minutes=expires_in)
        },
        SECRET_KEY,
        algorithm=JWT_ALGORITHM
    )

async def login(username: str, password: str) -> str | None:
    """
    Authenticate user. Returns token on success, None on fail.

    :param username: user to log in
    :param password: password for user
    :return: token if valid, None otherwise
    """
    # try to find user
    try:
        password_hash = await user_manager.get_password_hash(username)

    except KeyError:
        return None

    # check credentials
    if not await asyncio.to_thread(
        AUTH_PW_HASHER.verify,
        password_hash,
        password
    ):
        return None

    # create token
    return create_token(username)


async def get_current_user(token: Annotated[str, Depends(OAUTH2_SCHEME)]) -> str:
    """
    check token validity and return user.

    :param token: token to check
    :return: username
    :raises HTTPException: if invalid token or name
    """
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[JWT_ALGORITHM]
        )
        username = payload["sub"]

    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Signature expired. Please log in again.")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token. Please log in again.")

    # check if user is valid
    try:
        await user_manager.get_user(username)

    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    # return username if all checks have passed
    return username
