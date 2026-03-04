import logging
import os

import uvicorn
from fastapi import FastAPI
from loguru import logger

from fakevine.cvrouter import CVRouter
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk


def main() -> None:
    """Initialize and run the Fakevine FastAPI application.

    Sets up the FastAPI app with the FakeVine router, and the configured ComicTrunk backend.
    Intercepts uvicorn logging to loguru.
    """
    app = FastAPI()

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

    try:
        cache_expiry = int(os.environ.get("CACHE_EXPIRY_SECONDS"))  # ty:ignore[invalid-argument-type]
    except (ValueError, TypeError):
        cache_expiry = 24*60*60

    cv_router = CVRouter(trunk=SimpleCacheTrunk(
        cv_api_key=os.environ["CACHE_CV_API_KEY"],
        cache_filename=os.environ.get("CACHE_DB_PATH"),
        cache_expiry_seconds=cache_expiry,
        cv_api_url=os.environ.get("CACHE_CV_API_URL")),
        api_key=os.environ.get("API_KEY"))

    app.include_router(cv_router.router)

    try:
        listen_port = int(os.environ.get("LISTEN_PORT"))  # ty:ignore[invalid-argument-type]
    except (ValueError, TypeError):
        listen_port = 8463

    uvicorn.run(
        app,
        host=os.environ.get("LISTEN_INTERFACE", '0.0.0.0'),  # noqa: S104
        port=listen_port,
        log_config=None,
        log_level=None,
        )

class InterceptHandler(logging.Handler):  # noqa: D101
    def emit(self, record) -> None:  # noqa: D102
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
            level, record.getMessage()
        )

