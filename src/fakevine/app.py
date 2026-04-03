import logging
import sys
from pathlib import Path

import uvicorn
from dynaconf import ValidationError
from dynaconf.vendor.tomllib import TOMLDecodeError
from loguru import logger

from fakevine.config import settings
from fakevine.cvapp import CVApp
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk
from fakevine.trunks.static_db_trunk import StaticDBTrunk


def main() -> None:
    """Initialize and run the Fakevine FastAPI application.

    Sets up the FastAPI app with the FakeVine router, and the configured ComicTrunk backend.
    Intercepts uvicorn logging to loguru.
    """
    log_interception()

    # Test basic validation on settings stack
    try:
        _ = settings.get('COMIC_TRUNK')
    except (TOMLDecodeError, ValueError, ValidationError) as ex:
        message = f"Error Validating Configuration Variable.  {ex}"
        logger.error(message)
        sys.exit(1)

    if settings.get("LOG_FILE_ENABLE"):
        rotation = settings.get("LOG_ROTATION")
        retention = settings.get("LOG_RETENTION")
        try:
            logger.add('fakevine.log', rotation=rotation, retention=retention)
        except ValueError as ex:
            message = f"Error setting up file logging.  {ex}"
            logger.error(message)
            sys.exit(1)

    comic_trunk = settings.get("COMIC_TRUNK", "Cache").lower()
    if comic_trunk not in ["cache", "staticdb", "json"]:
        logger.warning("COMIC_TRUNK setting not recognised, defaulting to Cache")
        comic_trunk = "cache"

    match comic_trunk:
        case "cache":
            cv_app = CVApp(
                trunk=SimpleCacheTrunk(
                    cv_api_key=settings.get("CACHE_CV_API_KEY"),
                    cache_filename=settings.get("CACHE_DB_PATH"),
                    cache_expiry_minutes=settings.get("CACHE_EXPIRY_MINUTES"),
                    cv_api_url=settings.get("CACHE_CV_API_URL"),
                    user_agent=settings.get("CACHE_CV_UA"),
                    overrides=settings.get('CACHE_EXPIRY_OVERRIDE')),
                api_keys=settings.get("API_KEYS"))

        case "staticdb":
            db_path = Path(settings.get("STATICDB_PATH"))

            if not db_path.exists() and not db_path.is_file():
                logger.error(f'{db_path} does not exist / is not a file')
                sys.exit(1)

            cv_app = CVApp(
                trunk=StaticDBTrunk(
                    database_path=Path(db_path)),
                api_keys=settings.get("API_KEYS"))

        case "json":
            logger.error("JSON Trunk not yet implemented")
            sys.exit(1)

    uvicorn.run(
        cv_app.app,
        host=settings.get("LISTEN_INTERFACE"),
        port=settings.get("LISTEN_PORT"),
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

