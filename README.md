# FakeVine
This is a ComicVine compatible API package that can serve comic metadata using the same endpoints provided by the [ComicVine API](https://comicvine.gamespot.com/api/documentation).  With an appropriate backend, it can act as a cache for ComicVine API calls, a mock instance for testing comics applications, or a host for serving from static data dumps.

It is built on FastAPI and anger.

Some responses are not exact copies - CV returns a webpage for some HTTP error codes that are not replicated as you should be using the status code.  There are also some documented CV endpoints that are intentionally not implemented for the backends as they are either not properly implemented on CV's end or just have junk data.  They should really be avoided by consumers and will return bad responses.  These are `/chat`, `/chats`, `/promo`, & `/promos`.  Another error scenario that I have handled differently is how CV responds to junk in `field_list`, `sort`, and `filter`.  Their behaviour is as close as possible to default CV behaviour, but if they get proper junk then CV sends just as bad back, and I avoid this by doing some pre-cleaning of these params in the router.

The models are based on the [CV API documentation](https://comicvine.gamespot.com/api/documentation), and analysing actual CV data.  If it deviates from the documentation, that is likely because the documentation is wrong - e.g. no, [`/teams`](https://comicvine.gamespot.com/api/documentation#toc-0-34) is not filterable on `aliases`.  You may notice that there are a lot of nullable fields in the CV response models.  These reflect the real state of CV data rather than an ideal view of what could be (e.g. the API will serve empty volumes).  At the time of writing, I've only done models for the comic elements in the API as that's where I believe most use comes from.  It's possible that some validation will fail because of some unforseen futzery in ComicVine's data (if using as a cache) - please do report any such issues you find!  I have used these models to parse responses across all detail (single response) endpoints from CV without failures.

## Features
Current:
- A single backend offering a simple sqlite backed cache for ComicVine
- JSON responses only

Planned:
- Support for response types other than JSON
- A backend to serve data from a SQLite database
- A backend to serve data from a JSON file (mostly to support smaller test scenarios)
- Configurable failure scenarios to force failures from certain API calls
- Support remapping API URLs in responses to the FakeVine route 
- Host a static folder for cover caching
- Docker image
- Healthcheck for the router and trunks, primarily for Docker to monitor

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

## Contributing
Contributions will be welcome once I've got the core finished, but I'd suggest reaching out before starting anything large.  Contributions that are entirely or majority AI generated (both code and documentation) will likely be rejected.   You can find me on the [CBL-ReadingLists discord](https://discord.gg/DQmHfzFdGG). 

Any commits should be done using [commitizen](https://commitizen-tools.github.io/commitizen/) by running `uv run cz c`.  Consider squashing before submitting a PR if you have a scrappy commit history.
