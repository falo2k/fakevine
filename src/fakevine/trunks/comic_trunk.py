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

class URLFormatError(Exception):
    """Thrown for URL formatting errors."""

class ObjectNotFoundError(Exception):
    """Thrown for missing entity IDs."""

class UnsupportedResponseError(Exception):
    """Catch all for anything new and not yet covered (cloudflare?)."""

class GatewayError(UnsupportedResponseError):
    """Gateway timeouts.  TBD how best to handle these or just pass them on."""

class ComicTrunk(ABC):
    """Abstract base class representing different types of ComicVine data sources.

    This class provides an interface for interacting with various ComicVine
    data sources and defines the required methods for fetching volume, issue,
    and related information.

    While all methods should return a particular model, if a field_list is defined
    in request params, you may need to use the utility methods filtered_model or
    optional_model provided in cvapimodels to avoid parsing errors.

    """

    @abstractmethod
    async def search(self, params: SearchParams) -> SearchResponse:
        ...

    @abstractmethod
    async def volume(self, item_id: int, params: CommonParams) -> SingleResponse[DetailVolume]:
        ...

    @abstractmethod
    async def volumes(self, params: FilterParams) -> MultiResponse[BaseVolume]:
        ...

    @abstractmethod
    async def character(self, item_id: int, params: CommonParams) -> SingleResponse[DetailCharacter]:
        ...

    @abstractmethod
    async def characters(self, params: FilterParams) -> MultiResponse[BaseCharacter]:
        ...

    @abstractmethod
    async def concept(self, item_id: int, params: CommonParams) -> SingleResponse[DetailConcept]:
        ...

    @abstractmethod
    async def concepts(self, params: FilterParams) -> MultiResponse[BaseConcept]:
        ...

    @abstractmethod
    async def episode(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def episodes(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def issue(self, item_id: int, params: CommonParams) -> SingleResponse[DetailIssue]:
        ...

    @abstractmethod
    async def issues(self, params: FilterParams) -> MultiResponse[BaseIssue]:
        ...

    @abstractmethod
    async def location(self, item_id: int, params: CommonParams) -> SingleResponse[DetailLocation]:
        ...

    @abstractmethod
    async def locations(self, params: FilterParams) -> MultiResponse[BaseLocation]:
        ...

    @abstractmethod
    async def movie(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def movies(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def object(self, item_id: int, params: CommonParams) -> SingleResponse[DetailObject]:
        ...

    @abstractmethod
    async def objects(self, params: FilterParams) -> MultiResponse[BaseObject]:
        ...

    @abstractmethod
    async def origin(self, item_id: int, params: CommonParams) -> SingleResponse[DetailOrigin]:
        ...

    @abstractmethod
    async def origins(self, params: FilterParams) -> MultiResponse[BaseOrigin]:
        ...

    @abstractmethod
    async def person(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPerson]:
        ...

    @abstractmethod
    async def people(self, params: FilterParams) -> MultiResponse[BasePerson]:
        ...

    @abstractmethod
    async def power(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPower]:
        ...

    @abstractmethod
    async def powers(self, params: FilterParams) -> MultiResponse[BasePower]:
        ...

    @abstractmethod
    async def publisher(self, item_id: int, params: CommonParams) -> SingleResponse[DetailPublisher]:
        ...

    @abstractmethod
    async def publishers(self, params: FilterParams) -> MultiResponse[BasePublisher]:
        ...

    @abstractmethod
    async def series(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def series_list(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def story_arc(self, item_id: int, params: CommonParams) -> SingleResponse[DetailStoryArc]:
        ...

    @abstractmethod
    async def story_arcs(self, params: FilterParams) -> MultiResponse[BaseStoryArc]:
        ...

    @abstractmethod
    async def team(self, item_id: int, params: CommonParams) -> SingleResponse[DetailTeam]:
        ...

    @abstractmethod
    async def teams(self, params: FilterParams) -> MultiResponse[BaseTeam]:
        ...

    @abstractmethod
    async def video(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def videos(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def video_type(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def video_types(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def video_category(self, item_id: int, params: CommonParams) -> SingleResponse[BaseModelExtra]:
        ...

    @abstractmethod
    async def video_categories(self, params: FilterParams) -> MultiResponse[BaseModelExtra]:
        ...

    async def types(self, params: CommonParams) -> MultiResponse[BaseTypes]:  # noqa: ARG002
        return MultiResponse[BaseTypes].model_validate_json(
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
