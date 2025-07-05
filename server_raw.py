from typing import Final
from asyncio import run
from os import environ
from dotenv import load_dotenv
from requests import Response, get, post
import websockets

GATWAY_URL: Final[str] = "wss://gateway.discord.gg/"

from utils import (
    write_json,
    read_json,
    req,
    LOGGER,
    TOKEN,
    CLIENT_ID,
    CLIENT_SECRET
)

AUTHTOKEN = None

async def authorize() -> None:
    """
    Authorizes the bot by loading the token from environment variables and setting the authorization header.
    Raises:
        ValueError: If the TOKEN is not set in the environment variables.
    """
    global AUTHTOKEN
    try:
        res = await req(
            post,
            "/oauth2/token",
            headers = {
            'Content-Type': 'application/x-www-form-urlencoded'
            },
            data = {
            'grant_type': 'client_credentials',
            'scope': 'bot'
            },
            auth=(CLIENT_ID, CLIENT_SECRET),
        )

        tkoen = res.json().get('access_token')
        if not tkoen:
            raise ValueError("Failed to retrieve access token from response.")
        
        AUTHTOKEN = tkoen
        LOGGER.info(f"Authorization successful. Access Token: {AUTHTOKEN}")
        
        print(res.status_code, res.text)
    except ValueError as e:
        LOGGER.error(f"Authorization error: {e}")
        raise ValueError(f"Authorization error: {e}")


async def connect() -> None:
    """
    Connects to the Discord gateway using websockets.
    Raises:
        Exception: If the connection fails.
    """
    wsuri = f"{GATWAY_URL}?v=10&encoding=json"
    async with websockets.connect(wsuri) as ws:
        LOGGER.info(f"Connected to Discord Gateway at {wsuri}")
        async for msg in ws:
            print(msg)

async def main() -> None:
    """
    Main function to run the authorization and connection process.
    """
    try:
        await authorize()
        await connect()
    except Exception as e:
        LOGGER.error(f"An error occurred: {e}")
        raise

if __name__ == "__main__":
    run(main())