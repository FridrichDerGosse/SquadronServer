"""
FastAPI server.

| ``Path``: _server.py
| ``Project``: SquadronServer
| ``Created``: 21/11/2026
| ``Authors``: Nilusink
"""
from fastapi.security import OAuth2PasswordRequestForm
from fastapi import FastAPI, Depends, HTTPException
from pydantic import BaseModel, model_validator
from typing import Annotated

from ._auth import login, get_current_user
from ._constants import Status, HOST, PORT
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
        async def get_own_user(user: Annotated[str, Depends(get_current_user)]):
            """
            Get all information about the current user.
            :return:
            """
            return await user_manager.get_user(user)

        @self._app.get("/user/all")
        async def get_all_users(_: Annotated[str, Depends(get_current_user)]):
            return await user_manager.get_all_users()

        @self._app.get("/user")
        async def get_user(
                _: Annotated[str, Depends(get_current_user)],
                username: str
        ):
            return await user_manager.get_user(username)

        @self._app.get("/status/me")  # own user
        async def get_own_state(user: Annotated[str, Depends(get_current_user)]):
            return await user_manager.get_status(user)

        @self._app.get("/status/all")  # own user
        async def get_all_states(_: Annotated[str, Depends(get_current_user)]):
            return await user_manager.get_user_states()

        @self._app.get("/status")
        async def get_state(
                _: Annotated[str, Depends(get_current_user)],
                username: str
        ):
            return await user_manager.get_state(username)

        # endregion

        # region post requests
        @self._app.post("/login")
        async def login_endpoint(form: Annotated[OAuth2PasswordRequestForm, Depends()]):
            # try to log in
            token = await login(form.username, form.password)

            if not token:
                raise HTTPException(status_code=401, detail="Invalid username or password")

            return {
                "access_token": token,
                "token_type": "bearer",
            }

        @self._app.post("/status")
        async def set_state(
                user: Annotated[str, Depends(get_current_user)],
                state: UserStatus
        ):
            try:
                if state.status:
                    await user_manager.set_status(user, state.status)

                if state.info:
                    await user_manager.set_info(user, state.info)

            except KeyError:
                raise HTTPException(status_code=404, detail="User not found")

            return {
                "success": True
            }

        # endregion

    async def serve(self):
        """Run this buffer as its own FastAPI server."""
        config = uvicorn.Config(
            self._app,
            host=HOST,
            port=PORT,
            log_level="warning",
            # ssl_certfile="./localhost+1.pem",
            # ssl_keyfile="./localhost+1-key.pem",
        )
        server = uvicorn.Server(config)
        await server.serve()
