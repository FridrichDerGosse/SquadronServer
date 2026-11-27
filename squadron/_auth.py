"""
Handles everything involved in authentication.

| ``Path``: _auth.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from datetime import datetime, timezone, timedelta
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.ext.asyncio import AsyncSession
from argon2 import PasswordHasher, exceptions
from fastapi import HTTPException
from typing import Annotated
from fastapi import Depends
import asyncio
import jwt

from ._constants import TOKEN_EXPIRE_MINUTES, SECRET_KEY
from ._db_definitions import get_session
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
    Generate access token for user

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


async def login(session: AsyncSession, username: str, password: str) -> str | None:
    """
    Authenticate user. Returns token on success, None on fail.

    :param session: database session
    :param username: user to log in
    :param password: password for user
    :return: token if valid, None otherwise
    """
    # try to find user
    try:
        password_hash = await user_manager.get_password_hash(session, username)

    except KeyError:
        return None

    # check credentials
    try:
        await asyncio.to_thread(
            AUTH_PW_HASHER.verify,
            password_hash,
            password
        )

    except (
            exceptions.VerifyMismatchError,
            exceptions.VerificationError,
            exceptions.InvalidHashError
    ):
        raise HTTPException(status_code=401, detail="Incorrect credentials.")

    # create token
    return create_token(username)


async def get_current_user(
        token: Annotated[str, Depends(OAUTH2_SCHEME)],
        session: AsyncSession = Depends(get_session)
) -> str:
    """
    check token validity and return user.

    :param token: token to check
    :param session: database session
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
        raise HTTPException(status_code=401, detail="Token expired. Please log in again.")

    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token.")
    # check if user is valid
    try:
        await user_manager.get_user(session, username)

    except KeyError:
        raise HTTPException(status_code=404, detail="User not found")

    # return username if all checks have passed
    return username


async def hash_password(password: str) -> str:
    """
    hash a password with argon2

    :param password: password to hash
    :return: hashed password
    """
    try:
        return await asyncio.to_thread(
            AUTH_PW_HASHER.hash,
            password,
        )

    except exceptions.HashingError:
        raise HTTPException(status_code=400, detail="Unhashable password supplied")
