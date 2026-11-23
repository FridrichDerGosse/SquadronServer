"""
FastAPI server.

| ``Path``: _server.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from fastapi.sse import ServerSentEvent, EventSourceResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel, model_validator
from collections.abc import AsyncIterator
from typing import Annotated
import asyncio

from ._constants import Status, HOST, PORT, EventType, PriorityLevel
from ._auth import login, get_current_user, hash_password
from ._db_definitions import get_session
from ._user_data import user_manager
import uvicorn


class UserStatus(BaseModel):
    status: Status | None = None
    info: str | None = None

    @model_validator(mode="after")
    def check_fields(self):
        if self.status is None and self.info is None:
            raise ValueError("At least one of 'status' or 'info' must be provided")

        return self


class AlertInfo(BaseModel):
    priority: PriorityLevel
    title: str
    targets: list[str]
    info: str = ""


class SquadronServer:
    """
    Squadron Server.
    """

    def __init__(self) -> None:
        self._app = FastAPI()

        self._register_endpoints()

    def _register_endpoints(self) -> None:
        """
        register available endpoints.
        """
        @self._app.get("/")
        def root():
            return {"status": Status.online}

        # region get requests
        @self._app.get("/user/me")
        async def get_own_user(
                user: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session)
        ):
            """
            Get all information about the current user.
            :return:
            """
            return await user_manager.get_user(session, user)

        @self._app.get("/user/all")
        async def get_all_users(
                _: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session)
        ):
            return await user_manager.get_all_users(session)

        @self._app.get("/user")
        async def get_user(
                _: Annotated[str, Depends(get_current_user)],
                username: str,
                session: AsyncSession = Depends(get_session),
        ):
            return await user_manager.get_user(session, username)

        @self._app.get("/status/me")  # own user
        async def get_own_state(
                user: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session),
        ):
            return await user_manager.get_status(session, user)

        @self._app.get("/status/all")  # own user
        async def get_all_states(
                _: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session),
        ):
            return await user_manager.get_user_states(session)

        @self._app.get("/status")
        async def get_state(
                _: Annotated[str, Depends(get_current_user)],
                username: str,
                session: AsyncSession = Depends(get_session),
        ):
            return await user_manager.get_status(session, username)

        @self._app.get("/alerts")
        async def get_alerts(
                username: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session),
        ):
            user = await user_manager.get_user(session, username)
            alerts = await user_manager.check_alerts(session, user["id"])

            return alerts

        # endregion

        # region post requests
        @self._app.post("/login")
        async def login_endpoint(
                form: Annotated[OAuth2PasswordRequestForm, Depends()],
                session: AsyncSession = Depends(get_session),
        ):
            # try to log in
            token = await login(session, form.username, form.password)

            if not token:
                raise HTTPException(status_code=401, detail="Invalid username or password")

            return {
                "access_token": token,
                "token_type": "bearer",
            }

        @self._app.post("/register")
        async def register(
                form: Annotated[OAuth2PasswordRequestForm, Depends()],
                session: AsyncSession = Depends(get_session),
        ):
            # try to register user
            try:
                user = await user_manager.add_user(
                    session,
                    form.username,
                    await hash_password(form.password),
                )

            except KeyError:
                raise HTTPException(status_code=409, detail="User already exists.")

            return {
                "success": True,
                "user": user
            }


        @self._app.post("/status")
        async def set_state(
                user: Annotated[str, Depends(get_current_user)],
                state: UserStatus,
                session: AsyncSession = Depends(get_session),
        ):
            try:
                if state.status is not None:
                    await user_manager.set_status(session, user, state.status)

                if state.info is not None:
                    await user_manager.set_info(session, user, state.info)

            except KeyError:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True
            }

        @self._app.post("/alert")
        async def alert(
                username: Annotated[str, Depends(get_current_user)],
                data: AlertInfo,
                session: AsyncSession = Depends(get_session),
        ):
            # get own user ID
            user = await user_manager.get_user(session, username)

            # alert users
            n_alerted = await user_manager.alert_users(
                user["id"],
                data.priority,
                data.title,
                session,
                data.targets,
                info=data.info
            )

            return {
                "success": True,
                "n_alerted": n_alerted
            }

        # endregion

        # region subscriptions
        @self._app.get("/events")
        async def get_events_stream(
                username: Annotated[str, Depends(get_current_user)],
                session: AsyncSession = Depends(get_session),
        ) -> AsyncIterator[ServerSentEvent]:
            # subscribe user to updates
            user = await user_manager.get_user(session, username)
            sid, queue = user_manager.subscribe(user["id"])

            yield ServerSentEvent(comment="stream started")

            # look for any outstanding alerts
            for alert in await user_manager.check_alerts(session, user["id"]):
                yield ServerSentEvent(
                    data=alert,
                    event=EventType.alert.value
                )

            try:
                while True:
                    title, data = await queue.get()

                    yield ServerSentEvent(
                        data=data,
                        event=title.value,
                    )

            except asyncio.CancelledError:
                raise

            finally:
                user_manager.unsubscribe(user["id"], sid)
        # endregion

    async def serve(self):
        """Run this buffer as its own FastAPI server."""
        config = uvicorn.Config(
            self._app,
            host=HOST,
            port=PORT,
            log_level="debug",
            # ssl_certfile="./localhost+1.pem",
            # ssl_keyfile="./localhost+1-key.pem",
        )
        server = uvicorn.Server(config)
        await server.serve()
