from logging import getLogger, FileHandler, Formatter
from pathlib import Path
from json import dump, load, JSONDecodeError
from typing import Any, Final, Callable, LiteralString
import asyncio
from requests import Response
from os import environ
from dotenv import load_dotenv


CLIENT_ID: Final[str | None] = None
CLIENT_SECRET: Final[str | None] = None
CODE: Final[str | None] = None
REDIRECT: Final[str | None] = None
TOKEN: Final[str | None] = None

try:
    LOGFILE:Path = Path(__file__).parent.resolve() / "discord.log"
    LOGFILE.parent.mkdir(parents=True, exist_ok=True)
    HANDLER = FileHandler(filename=LOGFILE, encoding='utf-8', mode='w')
    HANDLER.setFormatter(Formatter("%(asctime)s [%(threadName)-12.12s] [%(levelname)-5.5s]  %(message)s"))
    LOGGER = getLogger("orca")
    LOGGER.addHandler(HANDLER)
    LOGGER.setLevel("DEBUG")
except (IOError, OSError) as err:
    raise ValueError(f"Failed to set up logging: {err}")

try:
    assert load_dotenv(verbose=True), "Failed to load .env file"

    TOKEN = environ.get("TOKEN", None)
    assert TOKEN is not None, "TOKEN is not set in the environment variables"

    CLIENT_ID = environ.get("CLIENT_ID", None)
    assert CLIENT_ID is not None, "CLIENT_ID is not set in the environment variables"

    CLIENT_SECRET = environ.get("CLIENT_SECRET", None)
    assert CLIENT_SECRET is not None, "CLIENT_SECRET is not set in the environment variables"

    CODE = environ.get("CODE", None)
    assert CODE is not None, "CODE is not set in the environment variables"

    REDIRECT = environ.get("REDIRECT", None)
    assert REDIRECT is not None, "REDIRECT is not set in the environment variables"

except AssertionError as e:
    LOGGER.error(f"Error loading Environment variables: {e}")
    raise ValueError(f"Environment variable error: {e}")



def write_json(fp: Path, data: dict[str, Any] | None) -> bool:
    """
    Writes a dictionary to a JSON file at the specified path.
    Args:
        fp (Path): The file path where the JSON data should be written.
        data (dict[str, Any] | None): The data to write to the JSON file. If None, no action is taken.
    Returns:
        bool: True if the data was written successfully, False otherwise.
    """
    if not data:
        LOGGER.warning(f"write_json:::No data to write to {fp}")
        return False
    
    try:
        with open(fp, 'w', encoding='utf-8') as f:
            dump(data, f, indent=4, ensure_ascii=False)
            LOGGER.info(f"write_json:::{fp} written to successfully")
            return True
    except (IOError, OSError) as err:
        LOGGER.error(f"write_json:::Failed to write data {err} to file {fp}")
        return False
    


def read_json(fp: Path) -> dict[str, Any] | None:
    """
    Reads a JSON file from the specified path and returns its content as a dictionary.
    Args:
        fp (Path): The file path from which to read the JSON data.
    Returns:
        dict[str, Any] | None: The data read from the JSON file as a dictionary, or None if the file does not exist or an error occurs.
    """
    if not fp.exists():
        LOGGER.warning(f"read_json:::File {fp} does not exist.")
        return None
    
    try:
        with open(fp, 'r', encoding='utf-8') as f:
            data = load(f)
            LOGGER.info(f"read_json:::{fp} read successfully")
            return data
    except (IOError, OSError, JSONDecodeError) as err:
        LOGGER.error(f"read_json:::Failed to read data from {fp} with error: {err}")
        return None
    

async def req(fn: Callable, url: str, **kwargs) -> Response:
    kwargs['timeout'] = 30
    kwargs.setdefault('headers', {})
    r = await asyncio.to_thread(fn, url, **kwargs)
    await asyncio.sleep(0.10)
    return r