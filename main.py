"""
Squadron status-sync server.

| ``Path``: main.py
| ``Project``: Squadron
| ``Created``: 21.11.2026
| ``Authors``: Nilusink
"""

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from fastapi import FastAPI, Depends, HTTPException
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm

app = FastAPI()

SECRET_KEY = "REPLACE_WITH_A_RANDOM_SECRET"
ALGORITHM = "HS256"
TOKEN_EXPIRE_MINUTES = 60 * 24

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")

ph = PasswordHasher()

# Example user database
users = {
    "nilusink": ph.hash("1234")
}


@app.post("/login")
def login(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
    hashed = users.get(form.username)

    if not hashed or not ph.verify(hashed, form.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")

    token = jwt.encode(
        {
            "sub": form.username,
            "exp": datetime.now(timezone.utc)
                   + timedelta(minutes=TOKEN_EXPIRE_MINUTES)
        },
        SECRET_KEY,
        algorithm=ALGORITHM
    )

    return {
        "access_token": token,
        "token_type": "bearer"
    }


def get_current_user(token: Annotated[str, Depends(oauth2_scheme)]):
    try:
        payload = jwt.decode(
            token,
            SECRET_KEY,
            algorithms=[ALGORITHM]
        )
        username = payload["sub"]

        if username not in users:
            raise ValueError()

        return username

    except (jwt.InvalidTokenError, KeyError, ValueError):
        raise HTTPException(status_code=401, detail="Invalid token")


@app.get("/me")
def me(user: Annotated[str, Depends(get_current_user)]):
    return {"username": user}
