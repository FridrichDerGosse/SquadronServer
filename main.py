"""
Squadron status-sync server.

| ``Path``: main.py
| ``Project``: Squadron
| ``Created``: 21.11.2026
| ``Authors``: Nilusink
"""
from squadron import SquadronServer, user_manager
import asyncio


async def main():
    # setup database
    await user_manager.init()

    # setup and start server
    server = SquadronServer()
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
