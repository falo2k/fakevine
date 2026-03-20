# ruff: noqa: F403, F405, D102
import requests_cache
from requests.adapters import HTTPAdapter
from requests_cache.backends.sqlite import SQLiteCache
from urllib3.util import Retry

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

    def __init__(self, cv_api_key: str, cache_expiry_minutes : int = 24*60, cache_filename: str | None = None,
        cv_api_url: str | None = None, user_agent: str = "fauxvigne") -> None:
        """Initialize SimpleCacheTrunk with ComicVine API credentials and cache settings.

        Args:
            cv_api_key: ComicVine API key for authentication.
            cache_expiry_minutes: Cache expiration time in minutes (default: 24 hours).
            cache_filename: SQLite cache filename (default: 'requests-cache.sqlite').
            cv_api_url: ComicVine API base URL (default: Official CV API URL).
            user_agent: User-Agent for requests to CV.

        """
        self.cv_api_key = cv_api_key

        self.response_map: dict[int,type[Exception]] = {
            401: AuthenticationError,
            420: RequestLimitError,
            429: RateLimitError,
            502: GatewayError,
        }

        self.headers = {
            'User-Agent' : user_agent,
            'Content-Type' : 'application/json',
        }

        if cache_filename is None:
            cache_filename = 'requests-cache.sqlite'

        if cv_api_url is not None:
            self.cv_api_url = cv_api_url.strip('/')
        else:
            self.cv_api_url = "https://comicvine.gamespot.com/api"

        retries = Retry(
            total=3,
            backoff_factor=0.1,
            status_forcelist=[502, 503, 504],
        )

        sqlite_cache = SQLiteCache(cache_filename, wal= True)
        self._session = requests_cache.CachedSession(backend=sqlite_cache, expire_after=cache_expiry_minutes*60)
        self._session.mount('https://', HTTPAdapter(max_retries=retries))
        self._session.mount('http://', HTTPAdapter(max_retries=retries))

    def _process_response(self, endpoint: str, params: CommonParams, response_collection: type[SingleResponse | MultiResponse], \
                result_model: type[BaseModelExtra]) -> SingleResponse[type[BaseModelExtra]] | MultiResponse[type[BaseModelExtra]]:
            params.api_key = self.cv_api_key
            if params.field_list is None or params.field_list == []:
                return_class = result_model
            else:
                field_list = params.field_list.split(',')
                return_class = filtered_model(result_model, field_list)

            response = self._session.get(f'{self.cv_api_url}{endpoint}', params=params, headers=self.headers)

            if response.status_code != 200:  # noqa: PLR2004
                if response.status_code in self.response_map:
                    raise self.response_map[response.status_code]
                error_string = f'Unsupported response from ComicVine: {response.status_code}'
                raise UnsupportedResponseError(error_string)

            return response_collection[return_class].model_validate(response.json())  # ty:ignore[invalid-return-type, unresolved-attribute]

    def search(self, params: SearchParams) -> SearchResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/search', params=params, headers=self.headers)

        if response.status_code != 200:  # noqa: PLR2004
            if response.status_code in self.response_map:
                raise self.response_map[response.status_code]
            error_string = f'Unsupported response from ComicVine: {response.status_code}'
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
        return return_class.model_validate(response.json())

    def volume(self, item_id: int, params: CommonParams) -> SingleResponse[DetailVolume]:
        return self._process_response(f'/volume/4050-{item_id}', params, SingleResponse, DetailVolume)  # ty:ignore[invalid-return-type]

    def volumes(self, params: FilterParams) -> MultiResponse[BaseVolume]:
        return self._process_response('/volumes', params, MultiResponse, BaseVolume)  # ty:ignore[invalid-return-type]

    def character(self, item_id: int, params: CommonParams) -> SingleResponse[DetailCharacter]:
        return self._process_response(f'/character/4005-{item_id}', params, SingleResponse, DetailCharacter)  # ty:ignore[invalid-return-type]

    def characters(self, params: CommonParams) -> MultiResponse[BaseCharacter]:
        return self._process_response('/characters', params, MultiResponse, BaseCharacter)  # ty:ignore[invalid-return-type]

    def concept(self, item_id: int, params: CommonParams) -> SingleResponse[DetailConcept]:
        return self._process_response(f'/concept/4015-{item_id}', params, SingleResponse, DetailConcept)  # ty:ignore[invalid-return-type]

    def concepts(self, params: CommonParams) -> MultiResponse[BaseConcept]:
        return self._process_response('/concepts', params, MultiResponse, BaseConcept)  # ty:ignore[invalid-return-type]

    def episode(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/episode/4070-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def episodes(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/episodes', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def issue(self, item_id: int, params: CommonParams) -> SingleResponse[DetailIssue]:
        return self._process_response(f'/issue/4000-{item_id}', params, SingleResponse, DetailIssue)  # ty:ignore[invalid-return-type]

    def issues(self, params: CommonParams) -> MultiResponse[BaseIssue]:
        return self._process_response('/issues', params, MultiResponse, BaseIssue)  # ty:ignore[invalid-return-type]

    def location(self, item_id: int, params: CommonParams) -> SingleResponse[DetailLocation]:
        return self._process_response(f'/location/4020-{item_id}', params, SingleResponse, DetailLocation)  # ty:ignore[invalid-return-type]

    def locations(self, params: CommonParams) -> MultiResponse[BaseLocation]:
        return self._process_response('/locations', params, MultiResponse, BaseLocation)  # ty:ignore[invalid-return-type]

    def movie(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/movie/4025-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def movies(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/movies', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def object(self, item_id: int, params: CommonParams) -> SingleResponse[DetailObject]:
        return self._process_response(f'/object/4055-{item_id}', params, SingleResponse, DetailObject)  # ty:ignore[invalid-return-type]

    def objects(self, params: CommonParams) -> MultiResponse[BaseObject]:
        return self._process_response('/objects', params, MultiResponse, BaseObject)  # ty:ignore[invalid-return-type]

    def origin(self, item_id: int, params: CommonParams) -> SingleResponse[DetailOrigin]:
        return self._process_response(f'/origin/4030-{item_id}', params, SingleResponse, DetailOrigin)  # ty:ignore[invalid-return-type]

    def origins(self, params: CommonParams) -> MultiResponse[BaseOrigin]:
        return self._process_response('/origins', params, MultiResponse, BaseOrigin)  # ty:ignore[invalid-return-type]

    def person(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPerson]:
        return self._process_response(f'/person/4040-{item_id}', params, SingleResponse, DetailPerson)  # ty:ignore[invalid-return-type]

    def people(self, params: CommonParams) -> MultiResponse[BasePerson]:
        return self._process_response('/people', params, MultiResponse, BasePerson)  # ty:ignore[invalid-return-type]

    def power(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPower]:
        return self._process_response(f'/power/4035-{item_id}', params, SingleResponse, DetailPower)  # ty:ignore[invalid-return-type]

    def powers(self, params: CommonParams) -> MultiResponse[BasePower]:
        return self._process_response('/powers', params, MultiResponse, BasePower)  # ty:ignore[invalid-return-type]

    def publisher(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPublisher]:
        return self._process_response(f'/publisher/4010-{item_id}', params, SingleResponse, DetailPublisher)  # ty:ignore[invalid-return-type]

    def publishers(self, params: CommonParams) -> MultiResponse[BasePublisher]:
        return self._process_response('/publishers', params, MultiResponse, BasePublisher)  # ty:ignore[invalid-return-type]

    def series(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/series/4075-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def series_list(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/series_list', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def story_arc(self, item_id: int, params: CommonParams) -> SingleResponse[DetailStoryArc]:
        return self._process_response(f'/story_arc/4045-{item_id}', params, SingleResponse, DetailStoryArc)  # ty:ignore[invalid-return-type]

    def story_arcs(self, params: CommonParams) -> MultiResponse[BaseStoryArc]:
        return self._process_response('/story_arcs', params, MultiResponse, BaseStoryArc)  # ty:ignore[invalid-return-type]

    def team(self, item_id: int, params: CommonParams) -> SingleResponse[DetailTeam]:
        return self._process_response(f'/team/4060-{item_id}', params, SingleResponse, DetailTeam)  # ty:ignore[invalid-return-type]

    def teams(self, params: CommonParams) -> MultiResponse[BaseTeam]:
        return self._process_response('/teams', params, MultiResponse, BaseTeam)  # ty:ignore[invalid-return-type]

    def types(self, params: CommonParams) -> MultiResponse[BaseTypes]:
        return self._process_response('/types', params, MultiResponse, BaseTypes)  # ty:ignore[invalid-return-type]

    def video(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/video/2300-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def videos(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/videos', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def video_type(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/video_type/2320-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def video_types(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/video_types', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def video_category(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        return self._process_response(f'/video_category/2320-{item_id}', params, SingleResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]

    def video_categories(self, params: CommonParams) -> MultiResponse[BaseModelExtra]:
        return self._process_response('/video_categories', params, MultiResponse, BaseModelExtra)  # ty:ignore[invalid-return-type]
