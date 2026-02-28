import logging
import os

import uvicorn
from fastapi import FastAPI

from fakevine.cvrouter import CVRouter
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk

logger = logging.getLogger(__name__)

def main() -> None:
    """Initialize and run the Fakevine FastAPI application.

    Sets up the FastAPI app with the FakeVine router, and the configured ComicTrunk backend.
    """
    app = FastAPI()

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
        )
