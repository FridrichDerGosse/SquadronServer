"""
Edits and reads all user data.

| ``Path``: _user_data.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from sqlalchemy.ext.asyncio import AsyncSession
from dataclasses import dataclass
from pydantic import BaseModel
from sqlmodel import select
import asyncio

from ._db_definitions import init_db, AlertTarget, \
    Alert, User
from ._constants import PriorityLevel, Status, EventType


@dataclass(frozen=True)
class UserData:
    name: str
    password: str
    status: int = 0
    info: str = ""


class StatusEvent(BaseModel):
    username: str
    status: Status
    info: str


class AlertEvent(BaseModel):
    id: int
    priority_level: PriorityLevel
    title: str


class UserManager:
    """
    Edits and reads all user data.

    :cvar __instance: singular manager instance
    """
    __instance: UserManager | None = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(UserManager, cls).__new__(cls)

        return cls.__instance

    def __init__(self):
        self._sse_queues: dict[int, tuple[int, asyncio.Queue]] = {}
        self._sse_id = 0

    # region subscriptions
    def subscribe(self, user_id: int) -> tuple[int, asyncio.Queue]:
        """
        Subscribe user to updates.

        :param user_id: id of user to subscribe as.
        :return: subscription id
        """
        sid = self._sse_id
        self._sse_id += 1

        queue = asyncio.Queue()

        self._sse_queues[sid] = (
            user_id,
            queue
        )

        return sid, queue

    def unsubscribe(self, sid: int) -> None:
        """
        remove active subscription.
        :param sid: subscription id
        """
        if sid in self._sse_queues:
            self._sse_queues.pop(sid)

    def _user_update(self, user: User) -> None:
        for _, queue in self._sse_queues.values():
            queue.put_nowait((
                EventType.user_update,
                {
                    "username": user.username,
                    "status": user.status,
                    "info": user.info
                }
            ))

    # endregion

    @staticmethod
    async def init() -> None:
        await init_db()

    @staticmethod
    async def check_username(
            session: AsyncSession,
            username: str
    ) -> bool:
        """
        Check if a username exists.

        :param session: database session
        :param username: username to check
        :return: true if exists, false if not
        """
        query = select(User).where(User.username == username)
        return bool(await session.scalar(query))

    @staticmethod
    async def get_user(
            session: AsyncSession,
            username: str
    ) -> dict:
        """
        Try to find a user by username.

        :param session: database session
        :param username: user to get
        :return: userdata
        :raises KeyError: if invalid username
        """
        user = await session.scalar(
            select(User).where(User.username == username)
        )

        if not user:
            raise KeyError(f"User \"{username}\" not found")

        return {
            "id": user.id,
            "username": user.username,
            "status": user.status,
            "info": user.info
        }

    @staticmethod
    async def get_password_hash(
            session: AsyncSession,
            username: str
    ) -> str:
        """
        get password hash of a user.

        :param session: database session
        :param username: user to get password hash from
        :return: password hash if found
        :raises KeyError: if invalid username
        """
        user = await session.scalar(
            select(User).where(User.username == username)
        )

        if not user:
            raise KeyError(f"User \"{username}\" not found")

        return user.password_hash

    @staticmethod
    async def get_all_users(
            session: AsyncSession,
    ) -> list[dict[str, str | int]]:
        """
        Get info about all users.

        :return: list of username, status, info
        """
        result = await session.execute(select(  # type: ignore
            User.username,
            User.status,
            User.info
        ))
        users = [
            {
                "id": row.id,
                "username": row.username,
                "status": row.status,
                "info": row.info
            }
            for row in result
        ]

        return users

    async def add_user(
            self,
            session: AsyncSession,
            user: UserData
    ) -> None:
        """
        Add a new user if it does not already exist.

        :param session: database session
        :param user: userdata to add
        :raises KeyError: if user already exists
        """
        if await self.check_username(session, user.name):
            raise KeyError("User already exists")

        user = User(
            username=user.name,
            password_hash=user.password,
        )
        session.add(user)
        await session.commit()

    async def set_status(
            self,
            session: AsyncSession,
            username: str,
            status: Status
    ) -> None:
        """
        Set status of a user

        :param session: database session
        :param username: user to change
        :param status: status to set
        :raises KeyError: if invalid username
        """
        # get user
        user = await session.scalar(
            select(User).where(User.username == username)
        )

        if user is None:
            raise KeyError(f"User \"{username}\" not found")

        # adjust status
        user.status = Status(status)
        await session.commit()

        # update user
        await session.refresh(user)
        self._user_update(user)

    async def set_info(
            self,
            session: AsyncSession,
            username: str,
            info: str
    ) -> None:
        """
        Set info of a user

        :param session: database session
        :param username: user to change
        :param info: info to set
        :raises KeyError: if invalid username
        """
        # get user
        user = await session.scalar(
            select(User).where(User.username == username)
        )

        if user is None:
            raise KeyError(f"User \"{username}\" not found")

        # adjust status
        user.info = info
        await session.commit()

        # update user
        await session.refresh(user)
        self._user_update(user)

    @staticmethod
    async def get_status(
            session: AsyncSession,
            username: str
    ) -> dict[str, Status | str]:
        """
        get status and info of a user.

        :param session: database session
        :param username: user to check
        :return: status, info
        :raises KeyError: if invalid username
        """
        user = await session.scalar(
            select(User).where(User.username == username)
        )

        if not user:
            raise KeyError(f"User \"{username}\" not found")

        return {
            "status": user.status,
            "info": user.info
        }

    @staticmethod
    async def get_user_states(
            session: AsyncSession,
    ) -> list[dict[str, str | int]]:
        """
        Get status and info of all users.

        :param session: database session
        :return: list of status, info
        """
        result = await session.execute(select(  # type: ignore
            User.username,
            User.status,
            User.info
        ))
        users = [
            {
                "status": row.status,
                "info": row.info
            }
            for row in result
        ]

        return users


# create singular instance
user_manager: UserManager = UserManager()
