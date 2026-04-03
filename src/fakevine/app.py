import logging
import os
import sys
from pathlib import Path

import uvicorn
from loguru import logger

from fakevine.cvapp import CVApp
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk
from fakevine.trunks.static_db_trunk import StaticDBTrunk


def main() -> None:
    """Initialize and run the Fakevine FastAPI application.

    Sets up the FastAPI app with the FakeVine router, and the configured ComicTrunk backend.
    Intercepts uvicorn logging to loguru.
    """
    log_interception()

    comic_trunk = os.environ.get("COMIC_TRUNK", "Cache").lower()
    if comic_trunk not in ["cache", "staticdb", "json"]:
        logger.warning("COMIC_TRUNK setting not recognised, defaulting to Cache")
        comic_trunk = "cache"

    match comic_trunk:
        case "cache":
            try:
                cache_expiry = int(os.environ.get("CACHE_EXPIRY_MINUTES"))  # ty:ignore[invalid-argument-type]
            except (ValueError, TypeError):
                cache_expiry = 24*60

            override_list: list[list] = [entry.split(':') for entry in os.environ.get("CACHE_EXPIRY_OVERRIDE", "").split(',')]
            for entry in override_list:
                if len(entry) == 1:
                    entry.append(-1)
                if entry[1] == "":
                    entry[1] = -1
                else:
                    entry[1] = int(entry[1])

            cv_app = CVApp(trunk=SimpleCacheTrunk(
                cv_api_key=os.environ["CACHE_CV_API_KEY"],
                cache_filename=os.environ.get("CACHE_DB_PATH"),
                cache_expiry_minutes=cache_expiry,
                cv_api_url=os.environ.get("CACHE_CV_API_URL"),
                user_agent=os.environ.get("CACHE_CV_UA", "fauxvigne"),
                overrides=override_list),
                api_key=os.environ.get("API_KEY"))

        case "staticdb":
            db_path = Path(os.environ.get("STATICDB_PATH", "fakevine.db"))

            if not db_path.exists() and not db_path.is_file():
                logger.error(f'{db_path} does not exist / is not a file')
                sys.exit(1)

            cv_app = CVApp(trunk=StaticDBTrunk(
                database_path=Path(db_path)),
                api_key=os.environ.get("API_KEY"))

        case "json":
            logger.error("JSON Trunk not yet implemented")
            sys.exit(1)

    try:
        listen_port = int(os.environ.get("LISTEN_PORT"))  # ty:ignore[invalid-argument-type]
    except (ValueError, TypeError):
        listen_port = 8463

    uvicorn.run(
        cv_app.app,
        host=os.environ.get("LISTEN_INTERFACE", '0.0.0.0'),  # noqa: S104
        port=listen_port,
        log_config=None,
        log_level=None,
        )

def log_interception() -> None:  # noqa: D103
    for handler in logging.root.handlers[:]:
        logging.root.removeHandler(handler)

    # Intercept standard logging
    logging.basicConfig(handlers=[InterceptHandler()], level=logging.INFO)

    loggers = (
        "uvicorn",
        "uvicorn.access",
        "uvicorn.error",
        "fastapi",
        "asyncio",
        "starlette",
    )

    for logger_name in loggers:
        logging_logger = logging.getLogger(logger_name)
        logging_logger.handlers = []
        logging_logger.propagate = True

class InterceptHandler(logging.Handler):  # noqa: D101
    def emit(self, record) -> None:  # noqa: ANN001, D102
        # Get corresponding Loguru level
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = record.levelno

        # Find caller to get correct stack depth
        frame, depth = logging.currentframe(), 2
        while frame.f_back and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage(),
        )

