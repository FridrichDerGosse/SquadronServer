"""
Squadron status-sync server.

| ``Path``: main.py
| ``Project``: Squadron
| ``Created``: 21.11.2026
| ``Authors``: Nilusink
"""
from squadron import SquadronServer
import asyncio


async def main():
    server = SquadronServer()
    await server.serve()


if __name__ == "__main__":
    asyncio.run(main())
