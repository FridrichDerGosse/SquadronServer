"""
Describes join alerts.

| ``Path``: _alerts.py
| ``Project``: SquadronServer
| ``Created``: 23/11/2026
| ``Authors``: Nilusink
"""
from dataclasses import dataclass
from enum import Enum


class PriorityLevel(Enum):
    a1 = 0  # absolutely critical, something broke / help needed
    a2 = 1  # urgent
    b1 = 10  # game request, hurry (game, discord, ...)
    b2 = 11  # game request, take your time
