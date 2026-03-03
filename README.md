# FakeVine
This is a ComicVine compatible API package that can serve comic metadata using the same endpoints provided by the [ComicVine API](https://comicvine.gamespot.com/api/documentation).  With an appropriate backend, it can act as a cache for ComicVine calls, a mock instance for testing comics applications, or a host for static data dumps.

It is built on FastAPI, and the router can be added to an existing app.

Some responses are not exact copies - CV returns a webpage with some HTTP error codes that are not replicated as you should be using the status code.  There are also some documented CV endpoints that are intentionally not implemented for the backends as they are either not properly implemented on CV's end or just have junk data.  They should really be avoided by consumers, but if you must use them they are: /chat, /chats, /promo, /promos.

## Features
Current:
- A single backend offering a simple sqlite backed cache for ComicVine

Planned:
- A backend to serve data from a SQLite database
- A backend to serve data from a JSON file (mostly to support smaller test scenarios)
- Configurable failure scenarios to force failures from certain API calls
- Support remapping API URLs in responses to the FakeVine route 
- Host a static folder for cover caching
- Docker image

## Running The App
Launch the app using [uv](https://docs.astral.sh/uv/) with `uv run fakevine`.  If you have not set any environment variables, you can pass a dotEnv file by running `uv run --env-file .env`.  See `.env.example` for details of available options.  At minimum you should define a CV API key for the cache to use.  The cache defaults to a 1 day expiry.

## Running in Docker
TBD

## Using in your own projects
While I don't currently plan to distribute this repo through pip, you can add the package using uv directly from GitHub using one of the commands below.

```bash
uv add "fakevine @ git+https://github.com/falo2k/fakevine.git"
```

```bash
uv add "fakevine @ git+ssh://git@github.com/falo2k/fakevine.git"
```

To create a custom backend, extend the ComicTrunk class and pass an instance to your FakeVine instance.  As an example, you can reproduce the default cached CV setup with the following code.

```python
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk
from fakevine.cvrouter import CVRouter
from fastapi import FastAPI


def main():
    app = FastAPI()

    cv_router = CVRouter(trunk=SimpleCacheTrunk(cv_api_key="YOURSECRETAPIKEY"))

    app.include_router(cv_router.router)

    uvicorn.run(
        app,
        host='0.0.0.0',
        port=8463,
    )


if __name__ == "__main__":
    main()
```