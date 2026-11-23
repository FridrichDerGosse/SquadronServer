"""
Edits and reads all user data.

| ``Path``: _user_data.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from dataclasses import dataclass


@dataclass(frozen=True)
class UserData:
    name: str
    password: str
    status: int = 0
    info: str = ""


class UserManager:
    """
    Edits and reads all user data.

    :cvar __instance: singular manager instance

    :ivar _users: user data
    """
    __instance: UserManager = None

    def __new__(cls, *args, **kwargs):
        if not cls.__instance:
            cls.__instance = super(UserManager, cls).__new__(cls)

        return cls.__instance

    def __init__(self) -> None:
        self._users: dict[str, UserData] = {}

        self.add_user(UserData(
            name="Nilusink",
            password="$argon2id$v=19$m=65536,t=3,p=4$uVlioYd2Eow0yBQw9NzqmQ$sUEKKi+yuqOaLCINjaV+0jZzvo65Ie6RIZF/uzCtST8",
        ))

    def check_username(self, username: str) -> bool:
        """
        Check if a username exists.

        :param username: username to check
        :return: true if exists, false if not
        """
        return username in self._users

    async def get_user(self, username: str) -> dict:
        """
        Try to find a user by username.

        :param username: user to get
        :return: userdata
        :raises KeyError: if invalid username
        """
        if username not in self._users:
            raise KeyError(f"User \"{username}\" not found")

        user = self._users[username]
        return {
            "username": user.name,
            "status": user.status,
            "info": user.info
        }

    async def get_password_hash(self, username: str) -> str:
        """
        get password hash of a user.

        :param username: user to get password hash from
        :return: password hash if found
        :raises KeyError: if invalid username
        """
        if username not in self._users:
            raise KeyError(f"User \"{username}\" not found")

        return self._users[username].password

    async def get_all_users(self) -> list[dict[str, str | int]]:
        """
        Get info about all users.

        :return: list of username, status, info
        """
        out = []
        for user in self._users.keys():
            out.append(await self.get_user(user))

        return out

    def add_user(self, user: UserData) -> None:
        """
        Add a new user if it does not already exist.

        :param user: userdata to add
        :raises KeyError: if user already exists
        """
        if user.name in self._users:
            raise KeyError

        self._users[user.name] = user

    async def set_status(self, username: str, status: int) -> None:
        """
        Set status of a user

        :param username: user to change
        :param status: status to set
        :raises KeyError: if invalid username
        """
        if username not in self._users:
            raise KeyError(f"User \"{username}\" not found")

        # create new instance because frozen dataclass
        user = self._users[username]
        self._users[username] = UserData(
            user.name,
            user.password,
            status,
            user.info
        )
        del user

    async def set_info(self, username: str, info: str) -> None:
        """
        Set info of a user

        :param username: user to change
        :param info: info to set
        :raises KeyError: if invalid username
        """
        if username not in self._users:
            raise KeyError(f"User \"{username}\" not found")

        # create new instance because frozen dataclass
        user = self._users[username]
        self._users[username] = UserData(
            user.name,
            user.password,
            user.status,
            info
        )
        del user

    async def get_status(self, username: str) -> dict[str, str | int]:
        """
        get status and info of a user.

        :param username: user to check
        :return: status, info
        :raises KeyError: if invalid username
        """
        if username not in self._users:
            raise KeyError(f"User \"{username}\" not found")

        user = self._users[username]
        return {
            "status": user.status,
            "info": user.info
        }

    async def get_user_states(self) -> list[dict[str, str | int]]:
        """
        Get status and info of all users.

        :return: list of status, info
        """
        out = []
        for user in self._users.keys():
            out.append(await self.get_status(user))

        return out


# create singular instance
user_manager = UserManager()
