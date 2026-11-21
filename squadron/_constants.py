"""
Defines global constants.

| ``Path``: _constants.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from enum import Enum
import secrets


# enums
class Status(Enum):
    ready = 2
    coming = 3
    online = 4
    offline = 6
    leaving = 7


# auth config
TOKEN_EXPIRE_MINUTES = 60
JWT_ALGORITHM = "HS256"
SECRET_KEY = secrets.token_hex(32)


# server config
HOST: str = "0.0.0.0"
PORT: int = 42069
