"""
Edits and reads all user data.

| ``Path``: _user_data.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import select, update
from dataclasses import dataclass
from pydantic import BaseModel
import typing as tp
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
        self._sse_queues: dict[
            int, dict[int, tuple[int, asyncio.Queue]]
        ] = {}
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

        if user_id not in self._sse_queues:
            self._sse_queues[user_id] = {}

        self._sse_queues[user_id][sid] = (
            user_id,
            queue
        )

        return sid, queue

    def unsubscribe(self, user_id: int, sid: int) -> None:
        """
        remove active subscription.

        :param user_id: user id
        :param sid: subscription id
        """
        if user_id in self._sse_queues:
            if sid in self._sse_queues[user_id]:
                self._sse_queues[user_id].pop(sid)

    def _user_update(self, user: User) -> None:
        for u in self._sse_queues:
            for _, queue in self._sse_queues[u].values():
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

    # region auth
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
    # endregion

    # region user
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
            username: str,
            password: str
    ) -> dict:
        """
        Add a new user if it does not already exist.

        :param session: database session
        :param username: name of user to add
        :param password: password, hashed
        :raises KeyError: if user already exists
        """
        if await self.check_username(session, username):
            raise KeyError("User already exists")

        user = User(
            username=username,
            password_hash=password,
        )
        session.add(user)
        await session.commit()

        await session.refresh(user)
        return {
            "id": user.id,
            "username": user.username,
            "status": user.status,
            "info": user.info
        }
    # endregion

    # region status
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
    # endregion

    # region alerts
    async def alert_users(
            self,
            alerted_by: int,
            priority_level: PriorityLevel,
            title: str,
            session: AsyncSession,
            usernames: list[str],
            info: str = ""
    ) -> int:
        """
        try to alert users

        :param alerted_by: user that instigated the alert
        :param priority_level: priority level of alert
        :param title: short title of alert
        :param session: database session
        :param usernames: usernames of users to alert
        :param info: optional, additional info
        :raises RuntimeError: if no valid users were found
        """
        # check if all users are alertable
        users = []
        for username in usernames:
            user = await session.scalar(
                select(User).where(User.username == username)
            )
            if not user:
                continue

            users.append(user)

        if not users:
            raise RuntimeError("No valid users found.")

        # create alert
        alert = Alert(
            alerted_by=alerted_by,
            priority_level=priority_level,
            title=title,
            info=info
        )
        session.add(alert)
        await session.commit()
        await session.refresh(alert)

        # create alert targets
        alerted = 0
        for user in users:
            executed = False
            # check if the user is listening for events
            if user.id in self._sse_queues:
                for _, queue in self._sse_queues[user.id].values():
                    queue.put_nowait((EventType.alert, alert))
                    executed = True

            alerted += executed

            alert_target = AlertTarget(
                alert_id=alert.id,
                user_id=user.id,
                executed=executed
            )
            session.add(alert_target)
            await session.commit()

        return alerted

    @staticmethod
    async def check_alerts(
            session: AsyncSession,
            user_id: int
    ) -> tp.Sequence[Alert]:
        """
        Check if the user has any outstanding alerts,
        executes any which aren't yet.

        :param session: database session
        :param user_id: user to check alerts for.
        :return: list of outstanding alerts
        """
        # get alerts
        alerts = await session.scalars(
            select(Alert)
            .join(AlertTarget, Alert.id == AlertTarget.alert_id)
            .where(AlertTarget.user_id == user_id, AlertTarget.executed == False)
        )

        # mark alerts as executed
        await session.execute(
            update(AlertTarget)
            .where(AlertTarget.user_id == user_id)
            .values(executed=True)

        )
        await session.commit()

        # return alerts
        return alerts.all()

    # endregion


# create singular instance
user_manager: UserManager = UserManager()
