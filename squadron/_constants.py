"""
Defines global constants.

| ``Path``: _constants.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from enum import Enum
import secrets

from ._alerts import Alert, PriorityLevel


# enums
class Status(Enum):
    standby = 1  # available within a few minutes
    ready = 2  # at pc, ready to join call
    coming = 3  # coming to call
    online = 4  # in call
    request = 5  # needs attention / look at WhatsApp chat
    offline = 6  # not available
    leaving = 7  # leaving shortly
    away = 8  # temporarily away
    pause = 9  # taking a break (german because break is a keyword)


# auth config
TOKEN_EXPIRE_MINUTES = 60
JWT_ALGORITHM = "HS256"
SECRET_KEY = secrets.token_hex(32)


# server config
HOST: str = "0.0.0.0"
PORT: int = 42069


# database
DB_FILE: str = "squadron.db"
