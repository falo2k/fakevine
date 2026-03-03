# ruff: noqa: F403, F405, D102
from typing import TypeVar

import requests_cache
from requests.adapters import HTTPAdapter
from requests_cache import Response
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

    def __init__(self, cv_api_key: str, cache_expiry_seconds : int = 24*60*60, cache_filename: str | None = None,
        cv_api_url: str | None = None) -> None:
        """Initialize SimpleCacheTrunk with ComicVine API credentials and cache settings.

        Args:
            cv_api_key: ComicVine API key for authentication.
            cache_expiry_seconds: Cache expiration time in seconds (default: 24 hours).
            cache_filename: SQLite cache filename (default: 'requests-cache.sqlite').
            cv_api_url: ComicVine API base URL (default: Official CV API URL).

        """
        self.cv_api_key = cv_api_key

        self.response_map: dict[int,type[Exception]] = {
            401: AuthenticationError,
            420: RequestLimitError,
            429: RateLimitError,
            502: GatewayError,
        }

        self.headers = {
            'User-Agent' : 'vineyard',
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
        self._session = requests_cache.CachedSession(backend=sqlite_cache, expire_after=cache_expiry_seconds)
        self._session.mount('https://', HTTPAdapter(max_retries=retries))
        self._session.mount('http://', HTTPAdapter(max_retries=retries))

    T = TypeVar('T', bound=CVResponse)

    def process_response(self, response: Response, model: type[T]) -> T:
        if response.status_code != 200:  # noqa: PLR2004
            if response.status_code in self.response_map:
                raise self.response_map[response.status_code]
            error_string = f'Unsupported response from ComicVine: {response.status_code}'
            raise UnsupportedResponseError(error_string)
        return model.model_validate(response.json())

    def volume(self, item_id: str, params: CommonParams) -> VolumeResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/volume/{item_id}', params=params, headers=self.headers)
        return self.process_response(response, model=VolumeResponse)

    def volumes(self, params: FilterParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/volumes', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def search(self, params: SearchParams) -> SearchResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/search', params=params, headers=self.headers)
        return self.process_response(response, model=SearchResponse)

    def character(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/character', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def characters(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/characters', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def chat(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/chat', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def chats(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/chats', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def concept(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/concept', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def concepts(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/concepts', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def episode(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/episode', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def episodes(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/episodes', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def issue(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/issue', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def issues(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/issues', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def location(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/location', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def locations(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/locations', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def movie(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/movie', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def movies(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/movies', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def object(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/object', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def objects(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/objects', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def origin(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/origin', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def origins(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/origins', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def person(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/person', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def people(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/people', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def power(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/power', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def powers(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/powers', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def promo(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/promo', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def promos(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/promos', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def publisher(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/publisher', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def publishers(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/publishers', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def series(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/series', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def series_list(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/series_list', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def story_arc(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/story_arc', params=params,headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def story_arcs(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/story_arcs', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def team(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/team', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def teams(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/teams', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def types(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/types', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def video(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/video', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def videos(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/videos', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def video_type(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/video_type', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def video_types(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/video_types', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def video_category(self, item_id: str, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/video_category', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)

    def video_categories(self, params: CommonParams) -> CVResponse:
        params.api_key = self.cv_api_key
        response = self._session.get(f'{self.cv_api_url}/video_categories', params=params, headers=self.headers)
        return self.process_response(response, model=CVResponse)
