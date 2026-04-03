# ruff: noqa: F403, F405, D102
from aiohttp_client_cache import CachedSession, SQLiteBackend
from sqlalchemy import over

from fakevine.models.cvapimodels import *
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    GatewayError,
    RateLimitError,
    RequestLimitError,
    UnsupportedResponseError,
)


class SimpleCacheTrunk(ComicTrunk):
    """A SQLite backed cache for requests to ComicVine."""

    _cache = None

    def __init__(self, cv_api_key: str, cache_expiry_minutes : int = 24*60, cache_filename: str | None = None,
        cv_api_url: str | None = None, user_agent: str = "fauxvigne", overrides: list[list] = []) -> None:
        """Initialize SimpleCacheTrunk with ComicVine API credentials and cache settings.

        Args:
            cv_api_key: ComicVine API key for authentication.
            cache_expiry_minutes: Cache expiration time in minutes (default: 24 hours).
            cache_filename: SQLite cache filename (default: 'requests-cache.sqlite').
            cv_api_url: ComicVine API base URL (default: Official CV API URL).
            user_agent: User-Agent for requests to CV.
            overrides: List of override expiries for endpoints (each a list[endpoint,minutes])

        """
        self._cv_api_key = cv_api_key

        self._response_map: dict[int,type[Exception]] = {
            401: AuthenticationError,
            420: RequestLimitError,
            429: RateLimitError,
            502: GatewayError,
        }

        self._headers = {
            'User-Agent' : user_agent,
            'Content-Type' : 'application/json',
        }

        if cache_filename is None:
            self._cache_filename = 'cache-trunk.sqlite'
        else:
            self._cache_filename = cache_filename

        if cv_api_url is not None:
            if cv_api_url[-1] != '/':
                self._cv_api_url += '/'
        else:
            self._cv_api_url = "https://comicvine.gamespot.com/api/"

        self._overrides = {f'{endpoint}/*' : expiry*60 if expiry >= 0 else expiry for endpoint, expiry in overrides}

        self._cache_expiry = cache_expiry_minutes*60

        self._cache = SQLiteBackend(cache_name=self._cache_filename, expire_after=self._cache_expiry,
                autoclose=False, urls_expire_after=self._overrides)
        self._session = None

    def __del__(self) -> None:  # noqa: D105
        if self._cache is not None:
            self._cache.close()

        if self._session is not None:
            self._session.close()

    def _setup_session(self) -> None:
        """Set up the async ClientSession instance and any bypasses."""
        if self._session is None:
            self._session = CachedSession(base_url=self._cv_api_url, cache=self._cache)

    async def _process_response(self, endpoint: str, params: CommonParams, response_collection: type[SingleResponse | MultiResponse], \
                result_model: type[BaseModelExtra]) -> SingleResponse[type[BaseModelExtra]] | MultiResponse[type[BaseModelExtra]]:
            modified_params = params.model_copy(update={'api_key' : self._cv_api_key, 'format' : 'json'})

            self._setup_session()

            response = await self._session.get(endpoint,  # ty:ignore[unresolved-attribute]
                params=modified_params.model_dump(exclude_none=True),
                headers=self._headers)

            if params.field_list is None or params.field_list == []:
                return_class = result_model
            else:
                field_list = params.field_list.split(',')
                return_class = filtered_model(result_model, field_list)

            if response.status != 200:  # noqa: PLR2004
                if response.status in self._response_map:
                    raise self._response_map[response.status]
                error_string = f'Unsupported response from ComicVine: {response.status}'
                raise UnsupportedResponseError(error_string)

            return response_collection[return_class].model_validate(await response.json())  # ty:ignore[invalid-return-type, unresolved-attribute]

    async def search(self, params: SearchParams) -> SearchResponse:
        modified_params = params.model_copy(update={'api_key' : self._cv_api_key, 'format' : 'json'})

        self._setup_session()

        response = await self._session.get('search',  # ty:ignore[unresolved-attribute]
            params=modified_params.model_dump(exclude_none=True),
            headers=self._headers)

        if response.status != 200:  # noqa: PLR2004
            if response.status in self._response_map:
                raise self._response_map[response.status]
            error_string = f'Unsupported response from ComicVine: {response.status}'
            raise UnsupportedResponseError(error_string)

        if params.field_list is None or params.field_list == []:
            return_class = SearchResponse
        else:
            field_list = params.field_list.split(',')
            filtered_classes = \
                filtered_model(DetailCharacter, field_list) | \
                filtered_model(DetailConcept, field_list) | \
                filtered_model(SearchIssue, field_list) | \
                filtered_model(SearchObject, field_list) | \
                filtered_model(SearchOrigin, field_list) | \
                filtered_model(SearchPerson, field_list) | \
                filtered_model(SearchPublisher, field_list) | \
                filtered_model(SearchStoryArc, field_list) | \
                filtered_model(SearchTeam, field_list) | \
                filtered_model(SearchVolume, field_list) | \
                filtered_model(BaseEntity, field_list)
            return_class = MultiResponse[filtered_classes]  # ty:ignore[invalid-type-form]
        return return_class.model_validate(await response.json())

    async def volume(self, item_id: int, params: CommonParams) -> SingleResponse[DetailVolume]:
        return await self._process_response(f'volume/4050-{item_id}', params, SingleResponse, DetailVolume)  # ty:ignore[invalid-return-type]

    async def volumes(self, params: FilterParams) -> MultiResponse[BaseVolume]:
        return await self._process_response('volumes', params, MultiResponse, BaseVolume)  # ty:ignore[invalid-return-type]

    async def character(self, item_id: int, params: CommonParams) -> SingleResponse[DetailCharacter]:
        return await self._process_response(f'character/4005-{item_id}', params, SingleResponse, DetailCharacter)  # ty:ignore[invalid-return-type]

    async def characters(self, params: FilterParams) -> MultiResponse[BaseCharacter]:
        return await self._process_response('characters', params, MultiResponse, BaseCharacter)  # ty:ignore[invalid-return-type]

    async def concept(self, item_id: int, params: CommonParams) -> SingleResponse[DetailConcept]:
        return await self._process_response(f'concept/4015-{item_id}', params, SingleResponse, DetailConcept)  # ty:ignore[invalid-return-type]

    async def concepts(self, params: FilterParams) -> MultiResponse[BaseConcept]:
        return await self._process_response('concepts', params, MultiResponse, BaseConcept)  # ty:ignore[invalid-return-type]

    async def episode(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'episode/4070-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def episodes(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('episodes', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def issue(self, item_id: int, params: CommonParams) -> SingleResponse[DetailIssue]:
        return await self._process_response(f'issue/4000-{item_id}', params, SingleResponse, DetailIssue)  # ty:ignore[invalid-return-type]

    async def issues(self, params: FilterParams) -> MultiResponse[BaseIssue]:
        return await self._process_response('issues', params, MultiResponse, BaseIssue)  # ty:ignore[invalid-return-type]

    async def location(self, item_id: int, params: CommonParams) -> SingleResponse[DetailLocation]:
        return await self._process_response(f'location/4020-{item_id}', params, SingleResponse, DetailLocation)  # ty:ignore[invalid-return-type]

    async def locations(self, params: FilterParams) -> MultiResponse[BaseLocation]:
        return await self._process_response('locations', params, MultiResponse, BaseLocation)  # ty:ignore[invalid-return-type]

    async def movie(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'movie/4025-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def movies(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('movies', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def object(self, item_id: int, params: CommonParams) -> SingleResponse[DetailObject]:
        return await self._process_response(f'object/4055-{item_id}', params, SingleResponse, DetailObject)  # ty:ignore[invalid-return-type]

    async def objects(self, params: FilterParams) -> MultiResponse[BaseObject]:
        return await self._process_response('objects', params, MultiResponse, BaseObject)  # ty:ignore[invalid-return-type]

    async def origin(self, item_id: int, params: CommonParams) -> SingleResponse[DetailOrigin]:
        return await self._process_response(f'origin/4030-{item_id}', params, SingleResponse, DetailOrigin)  # ty:ignore[invalid-return-type]

    async def origins(self, params: FilterParams) -> MultiResponse[BaseOrigin]:
        return await self._process_response('origins', params, MultiResponse, BaseOrigin)  # ty:ignore[invalid-return-type]

    async def person(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPerson]:
        return await self._process_response(f'person/4040-{item_id}', params, SingleResponse, DetailPerson)  # ty:ignore[invalid-return-type]

    async def people(self, params: FilterParams) -> MultiResponse[BasePerson]:
        return await self._process_response('people', params, MultiResponse, BasePerson)  # ty:ignore[invalid-return-type]

    async def power(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPower]:
        return await self._process_response(f'power/4035-{item_id}', params, SingleResponse, DetailPower)  # ty:ignore[invalid-return-type]

    async def powers(self, params: FilterParams) -> MultiResponse[BasePower]:
        return await self._process_response('powers', params, MultiResponse, BasePower)  # ty:ignore[invalid-return-type]

    async def publisher(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPublisher]:
        return await self._process_response(f'publisher/4010-{item_id}', params, SingleResponse, DetailPublisher)  # ty:ignore[invalid-return-type]

    async def publishers(self, params: FilterParams) -> MultiResponse[BasePublisher]:
        return await self._process_response('publishers', params, MultiResponse, BasePublisher)  # ty:ignore[invalid-return-type]

    async def series(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'series/4075-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def series_list(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('series_list', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def story_arc(self, item_id: int, params: CommonParams) -> SingleResponse[DetailStoryArc]:
        return await self._process_response(f'story_arc/4045-{item_id}', params, SingleResponse, DetailStoryArc)  # ty:ignore[invalid-return-type]

    async def story_arcs(self, params: FilterParams) -> MultiResponse[BaseStoryArc]:
        return await self._process_response('story_arcs', params, MultiResponse, BaseStoryArc)  # ty:ignore[invalid-return-type]

    async def team(self, item_id: int, params: CommonParams) -> SingleResponse[DetailTeam]:
        return await self._process_response(f'team/4060-{item_id}', params, SingleResponse, DetailTeam)  # ty:ignore[invalid-return-type]

    async def teams(self, params: FilterParams) -> MultiResponse[BaseTeam]:
        return await self._process_response('teams', params, MultiResponse, BaseTeam)  # ty:ignore[invalid-return-type]

    async def types(self, params: CommonParams) -> MultiResponse[BaseTypes]:
        return await self._process_response('types', params, MultiResponse, BaseTypes)  # ty:ignore[invalid-return-type]

    async def video(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'video/2300-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def videos(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('videos', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def video_type(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'video_type/2320-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def video_types(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('video_types', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def video_category(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return await self._process_response(f'video_category/2320-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    async def video_categories(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        return await self._process_response('video_categories', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]
