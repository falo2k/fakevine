# ruff: noqa: F403, F405, D102
"""Abstract base class for ComicVine data sources."""

from abc import ABC, abstractmethod

from fakevine.models.cvapimodels import *


class RateLimitError(Exception):
    """Thrown for a trunk rate limiting requests."""

class RequestLimitError(Exception):
    """Thrown for a trunk breaching request limits."""

class AuthenticationError(Exception):
    """Thrown for API key problems."""

class UnsupportedResponseError(Exception):
    """Catch all for anything new and not yet covered (cloudflare?)."""

class GatewayError(UnsupportedResponseError):
    """Gateway timeouts.  TBD how best to handle these or just pass them on."""

class ComicTrunk(ABC):
    """Abstract base class representing different types of ComicVine data sources.

    This class provides an interface for interacting with various ComicVine
    data sources and defines the required methods for fetching volume, issue,
    and related information.
    """

    @abstractmethod
    def search(self, params: SearchParams) -> SearchResponse:
        ...

    @abstractmethod
    def volume(self, item_id: str, params: CommonParams) -> VolumeResponse:
        ...

    @abstractmethod
    def volumes(self, params: FilterParams) -> CVResponse:
        ...

    @abstractmethod
    def character(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def characters(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def chat(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def chats(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def concept(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def concepts(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def episode(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def episodes(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def issue(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def issues(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def location(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def locations(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def movie(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def movies(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def object(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def objects(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def origin(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def origins(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def person(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def people(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def power(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def powers(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def promo(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def promos(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def publisher(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def publishers(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def series(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def series_list(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def story_arc(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def story_arcs(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def team(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def teams(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def video(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def videos(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def video_type(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def video_types(self, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def video_category(self, item_id: str, params: CommonParams) -> CVResponse:
        ...

    @abstractmethod
    def video_categories(self, params: CommonParams) -> CVResponse:
        ...

    def types(self, params: CommonParams) -> CVResponse:  # noqa: ARG002
        return CVResponse.model_validate_json(
            json_data= '''
            {
                "error": "OK",
                "limit": 20,
                "offset": 0,
                "number_of_page_results": 20,
                "number_of_total_results": 20,
                "status_code": 1,
                "results": [
                    {
                    "detail_resource_name": "character",
                    "list_resource_name": "characters",
                    "id": 4005
                    },
                    {
                    "detail_resource_name": "chat",
                    "list_resource_name": "chats",
                    "id": 2450
                    },
                    {
                    "detail_resource_name": "concept",
                    "list_resource_name": "concepts",
                    "id": 4015
                    },
                    {
                    "detail_resource_name": "episode",
                    "list_resource_name": "episodes",
                    "id": 4070
                    },
                    {
                    "detail_resource_name": "issue",
                    "list_resource_name": "issues",
                    "id": 4000
                    },
                    {
                    "detail_resource_name": "location",
                    "list_resource_name": "locations",
                    "id": 4020
                    },
                    {
                    "detail_resource_name": "movie",
                    "list_resource_name": "movies",
                    "id": 4025
                    },
                    {
                    "detail_resource_name": "object",
                    "list_resource_name": "objects",
                    "id": 4055
                    },
                    {
                    "detail_resource_name": "origin",
                    "list_resource_name": "origins",
                    "id": 4030
                    },
                    {
                    "detail_resource_name": "person",
                    "list_resource_name": "people",
                    "id": 4040
                    },
                    {
                    "detail_resource_name": "power",
                    "list_resource_name": "powers",
                    "id": 4035
                    },
                    {
                    "detail_resource_name": "promo",
                    "list_resource_name": "promos",
                    "id": 1700
                    },
                    {
                    "detail_resource_name": "publisher",
                    "list_resource_name": "publishers",
                    "id": 4010
                    },
                    {
                    "detail_resource_name": "series",
                    "list_resource_name": "series",
                    "id": 4075
                    },
                    {
                    "detail_resource_name": "story_arc",
                    "list_resource_name": "story_arcs",
                    "id": 4045
                    },
                    {
                    "detail_resource_name": "team",
                    "list_resource_name": "teams",
                    "id": 4060
                    },
                    {
                    "detail_resource_name": "video",
                    "list_resource_name": "videos",
                    "id": 2300
                    },
                    {
                    "detail_resource_name": "video_type",
                    "list_resource_name": "video_types",
                    "id": 2320
                    },
                    {
                    "detail_resource_name": "video_category",
                    "list_resource_name": "video_categories",
                    "id": 2320
                    },
                    {
                    "detail_resource_name": "volume",
                    "list_resource_name": "volumes",
                    "id": 4050
                    }
                ],
                "version": "1.0"
            }
            ''', # noqa: Q001
        )
