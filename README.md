## WARNING
Project is still in core development, so may have some refactoring in the short term until 0.1.0 release.

# FakeVine
This is a ComicVine compatible API package that can serve comic metadata using the same endpoints provided by the [ComicVine API](https://comicvine.gamespot.com/api/documentation).  With an appropriate backend, it can act as a cache for ComicVine API calls, a mock instance for testing comics applications, or a host for serving from static data dumps.

It is built on FastAPI and anger. :rage1:

Some error scenario responses are not exact copies - CV returns a webpage for some HTTP error codes that are not replicated as you should be using the status code.  There are also some documented CV endpoints that are intentionally not implemented for the backends as they are either not properly implemented on CV's end or just have junk data.  They should really be avoided by consumers and will return bad responses.  These are `/chat`, `/chats`, `/promo`, & `/promos`.  Another error scenario that I have handled differently is how CV responds to junk in `field_list`, `sort`, and `filter`.  Their behaviour is as close as possible to default CV behaviour, but if they get proper junk then CV sends just as bad back, and I avoid this by doing some pre-cleaning of these params in the app.  Sort orders of list elements will depend on the trunk used and trial and error on CV.  This should only really matter for `/story_arc` issues as they are not returned with an ordering attribute, but then that data is generally trash quality anyway :man_shrugging:.

The models are based on the [CV API documentation](https://comicvine.gamespot.com/api/documentation), and analysing actual CV data.  If it deviates from the documentation, that is likely because the documentation is wrong - e.g. no, [`/teams`](https://comicvine.gamespot.com/api/documentation#toc-0-34) is not filterable on `aliases`.  You may notice that there are a lot of nullable fields in the CV response models.  These reflect the real state of CV data rather than an ideal view of what could be (e.g. the API will serve empty volumes).  At the time of writing, I've only done models for the comic elements in the API as that's where I believe most use comes from.  It's possible that some validation will fail because of some unforseen futzery in ComicVine's data (if using as a cache) - please do report any such issues you find!  I have used these models to parse responses across all detail (single response) endpoints from CV without failures.

There are some differences in the XML and json responses.  CV is completely inconsistent in the structure and attributes returned in each for the same entity.  It's frankly infuriating, but as I don't want to maintain a whole XML supporting model in addition to the main API model, responses from FakeVine may have **additional** data returned (depending on the source).  As always, if you're building apps off the CV API, make sure you test them against the actual API first.

## Running The App
Launch the app using [uv](https://docs.astral.sh/uv/) with `uv run fakevine`.

Configuration is loaded in the order `defaults.toml` -> `settings.toml` -> ENV VARs (or a dotEnv file).  See `defaults.toml` for details of available options.  At minimum you should define a CV API key for the cache to use.

## Backends
### Simple Request Cache (Cache)
Will cache requests to ComicVine for the defined duration, storing responses in a local SQLite database.  Requires a ComicVine API key to function.  Caching is done on a complete request basis (i.e. the unique combination of all parameters passed to the endpoint).  Some endpoints are better suited to shorter expiries using the `CACHE_EXPIRY_OVERRIDE` setting.  e.g. You may want `/volume` to expire weekly to allow new issue releases to be recognised, `/search` or `/volumes` to never expire as they are primarily used for discovery, but `/issue` could have a longer expiry as a mostly one and done request.

More complex logic could be introduced in the future to drive record expiry settings based on the data returned.

### Static Databases (StaticDB and LocalCVDB)
Uses a static SQLite database to serve response data.  There are two database schemas supported:
- LocalCVDB uses the schema from the early 2026 reddit dump.  It does not support all routes, or all fields on those routes, due to the limited content within that schema.
- StaticDB uses a full schema to cover comic based data, and an instance can be generated using `fakevine-utils` and a database of historic `json` responses.

As a full search engine, and unpicking how CV search **currently** works is out of scope for this projects, the `/search` endpoint uses SQLite FTS5.  It's not the best.

**Note that all the above backends use an in-memory cache of any requests for 5 minutes in case you want to heavily load the API.**

### JSON Database (json)
Not yet implemented.  Originally the purpose of this project to create a testing tool ...

## Running in Docker
See the example docker-compose files for how to deploy FakeVine.  Settings can be set as environment variables in docker, or added as a file in `/data`.  At minimum you will want to set a `CACHE_CV_API_KEY` for the cache setup, likely also paths for log storage.  As rate limiting and complex caching is out of scope for the app, an example compose is provided for deploying [Caddy](https://caddyserver.com/) to perform these services in front of FakeVine.

**Available image tags:**
- `latest` - Latest stable release
- `v{version}` - Specific release version (e.g., `v0.1.0`)
- `nightly` - Latest nightly build
- `nightly-{sha}` - Specific nightly build with commit SHA
- Any of the above with `-dev` suffix for development images with debugpy support (on port 5678).

## Using in your own projects
While I don't currently plan to distribute this repo through pip, you can add the package using uv directly from GitHub using one of the commands below.

```bash
uv add "fakevine @ git+https://github.com/comictools/fakevine.git"
```

```bash
uv add "fakevine @ git+ssh://git@github.com/comictools/fakevine.git"
```

To create a custom backend, extend the ComicTrunk class and pass an instance to your FakeVine instance.  As an example, you can reproduce the default cached CV setup with the following code.  You can use it in an existing application as a [sub-application](https://fastapi.tiangolo.com/advanced/sub-applications/).

```python
import uvicorn
from fakevine.trunks.simple_cache_trunk import SimpleCacheTrunk
from fakevine.cvapp import CVApp

def main():
    print("Hello from test-fakevine-router!")
    cv_app = CVApp(trunk=SimpleCacheTrunk(
        cv_api_key="ff203453c76560ef4f7a4aba7c9be9336081007d"))

    uvicorn.run(
        cv_app.app,
        host='0.0.0.0',
        port=8463,
    )

if __name__ == "__main__":
    main()
```

## Contributing
Contributions will be welcome once I've got the core finished, but I'd suggest reaching out before starting anything large.  Contributions that are entirely or majority AI generated (both code and documentation) will likely be rejected.   You can find me on the [Mylar](https://discord.gg/6qpyCZRZRB) or [CBL-ReadingLists](https://discord.gg/DQmHfzFdGG) discords.

Any commits should be done using [commitizen](https://commitizen-tools.github.io/commitizen/) by running `uv run cz c`.  Consider squashing before submitting a PR if you have a scrappy commit history.

## Feature Log
:thumbsup: **Current:**
- Backends offering a SQLite backed cache for ComicVine or static SQLite database sources
- JSON and XML response types

:writing_hand: **Planned:**
- A backend to serve data from a JSON file (mostly to support smaller test scenarios)
- Configurable failure scenarios to force failures from certain API calls
- Support remapping API URLs in responses to the FakeVine route 
- Host a static folder for cover caching

:thumbsdown: **Unplanned:**
- Request caching.  You can add a service like Caddy's [cache-handler](https://github.com/caddyserver/cache-handler) in front.
- Rate limiting.  It might come later, but any implementation to achieve any control at the scale it's necessary would likely need external services anyway, so it makes more sense to suggest utilising a Caddy rate limiting plugin for this as well.
- More complex authentication.  I'm sure it could do better than simple string checks on a list of api keys, but that'll do for the scope of this while remaining CV compatible.