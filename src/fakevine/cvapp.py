import json
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import FastAPI, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from lxml import etree
from pydantic_core import ValidationError

from fakevine.models import cvapimodels
from fakevine.models.cvapimodels import (
    BaseModelExtra,
    CommonParams,
    CVResponse,
    FilterParams,
    SearchParams,
    validate_field_list,
    validate_filter_list,
    validate_resource_list,
    validate_sort_order,
)
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    GatewayError,
    ObjectNotFoundError,
    RateLimitError,
    RequestLimitError,
    UnsupportedResponseError,
    URLFormatError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from lxml.etree._element import _Element


class CVApp:
    """FastAPI App for ComicVine API compatible endpoints.

    Handles routing and processing of requests to backend ComicTrunk.

    Attributes
    ----------
    OBJECT_NOT_FOUND, INVALID_API_KEY, RATE_LIMITED, REQUEST_LIMIT_BREACH, URL_FORMAT_ERROR : Response
        Responses to match CV's HTTP status codes and content.
    app : FastAPI
        FastAPI app instance.
    api_keys : list[str]
        Optional API key for basic authentication.
    trunk : ComicTrunk
        ComicTrunk instance for data operations.

    """

    app: FastAPI
    api_key: str | None = None
    trunk: ComicTrunk

    def __init__(self, trunk: ComicTrunk, api_keys: list[str]) -> None:
        """Initialize the CVRouter with a ComicTrunk and optional API key.

        Args:
            trunk (ComicTrunk): The comic trunk instance for data operations.
            api_keys (list[str]): The API keys for authentication.  If none provided then will not perform checks.

        """
        self.api_keys = api_keys
        self.trunk = trunk
        self.app = FastAPI(exception_handlers={
            RequestValidationError : self._validation_exception_handler})
        self._attach_routes()

        self._exception_responses:dict[type[Exception], tuple[int, CVResponse | str]] = {
            RateLimitError : (status.HTTP_429_TOO_MANY_REQUESTS, r"<title>429</title>429 Too Many Requests"),
            AuthenticationError : (status.HTTP_401_UNAUTHORIZED, CVResponse(limit=0, status_code=100)),
            RequestLimitError : (420, CVResponse(limit=0, status_code=107)),
            ObjectNotFoundError : (status.HTTP_200_OK, CVResponse(limit=0, status_code=101)),
            UnsupportedResponseError : (status.HTTP_501_NOT_IMPLEMENTED, "Response not handled"),
            NotImplementedError : (status.HTTP_501_NOT_IMPLEMENTED, "Not supported by trunk"),
            URLFormatError : (status.HTTP_404_NOT_FOUND, CVResponse(limit=0, status_code=102)),
            GatewayError: (status.HTTP_502_BAD_GATEWAY, "<html><title>502 Bad Gateway</title><body>502 Bad Gateway</body></html>"),
        }

    async def _validation_exception_handler(self, request: Request, exc: RequestValidationError) -> Response:
        if request.query_params.get('api_key') is None or request.query_params.get('api_key') == '':
            status_code, data = self._exception_responses[AuthenticationError]
            if request.query_params.get('format', 'json') in ['json', 'jsonp']:
                return JSONResponse(content=jsonable_encoder(data), status_code=status_code)

            return Response(content=cvresponse_to_xml(data), status_code=status_code, media_type=r"application/xml")  # ty:ignore[invalid-argument-type]

        message = """
            <html>
                <title>Random CV Webpage</title>
                <body>
                    <b>Validation errors:</b>
        """
        for error in exc.errors():
            message += f"<br />Field: {error['loc']}, Error: {error['msg']}"
        return HTMLResponse(status_code=status.HTTP_200_OK, content=f"{message}</body></html>")

    def _attach_routes(self) -> None:
        routes =[
            ('/character/4005-{character_id}', self._get_character, "Character Detail", True),
            ('/characters', self._get_characters, "Character Search", True),
            ('/chat/2450-{item_id}', self._get_object_not_found, "Chat Detail", False),
            ('/chats', self._get_object_not_found, "Chat Search", False),
            ('/concept/4015-{concept_id}', self._get_concept, "Concept Detail", True),
            ('/concepts', self._get_concepts, "Concept Search", True),
            ('/episode/4070-{episode_id}', self._get_episode, "Episode Detail", True),
            ('/episodes', self._get_episodes, "Episode Search", True),
            ('/issue/4000-{issue_id}', self._get_issue, "Issue Detail", True),
            ('/issues', self._get_issues, "Issue Search", True),
            ('/location/4020-{location_id}', self._get_location, "Location Detail", True),
            ('/locations', self._get_locations, "Location Search", True),
            ('/movie/4025-{movie_id}', self._get_movie, "Movie Detail", True),
            ('/movies', self._get_movies, "Movie Search", True),
            ('/object/4055-{object_id}', self._get_object, "Object Detail", True),
            ('/objects', self._get_objects, "Object Search", True),
            ('/origin/4030-{origin_id}', self._get_origin, "Origin Detail", True),
            ('/origins', self._get_origins, "Origin Search", True),
            ('/person/4040-{person_id}', self._get_person, "Person Detail", True),
            ('/people', self._get_people, "People Detail", True),
            ('/power/4035-{power_id}', self._get_power, "Power Detail", True),
            ('/powers', self._get_powers, "Power Search", True),
            ('/promo/1700-{promo_id}', self._get_object_not_found, "Promo Detail", False),
            ('/promos', self._get_object_not_found, "Promo Search", False),
            ('/publisher/4010-{publisher_id}', self._get_publisher, "Publisher Detail", True),
            ('/publishers', self._get_publishers, "Publisher Search", True),
            ('/search', self._get_search, "General Search", True),
            ('/series/4075-{series_id}', self._get_series, "Series Detail", True),
            ('/series_list', self._get_series_list, "Series Search", True),
            ('/story_arc/4045-{story_arc_id}', self._get_story_arc, "Story Arc Detail", True),
            ('/story_arcs', self._get_story_arcs, "Story Arc Search", True),
            ('/team/4060-{team_id}', self._get_team, "Team Detail", True),
            ('/teams', self._get_teams, "Team Search", True),
            ('/types', self._get_types, "Resource Type Data", True),
            ('/video/2300-{video_id}', self._get_video, "Video Detail", True),
            ('/videos', self._get_videos, "Video Search", True),
            ('/video_type/2320-{video_type_id}', self._get_video_type, "Video Type Detail", True),
            ('/video_types', self._get_video_types, "Video Type Search", True),
            ('/video_category/2320-{video_category_id}', self._get_video_category, "Video Category Detail", True),
            ('/video_categories', self._get_video_categories, "Video Category Search", True),
            ('/volumes', self._get_volumes, "Volume Search", True),
            ('/volume/4050-{volume_id}', self._get_volume, "Volume Detail", True),
            ('/{any_id}/{other_id}', self._get_url_format_error, "URL Format Error", False),
            ('/{any_id}/{other_id}-{id_other}', self._get_url_format_error, "URL Format Error", False),
            ('/{any_id}', self._get_url_format_error, "URL Format Error", False),
        ]

        for route in routes:
            self.app.add_api_route(
                methods=['GET'],
                path=route[0],
                endpoint=route[1],
                name=route[2],
                include_in_schema=route[3])

    async def _fetch_response(self, params: CommonParams, trunk_method: Callable, item_id: int | None = None) -> Response:
        """Handle passing parameters to the ComicTrunk and processing the response into the correct format.

        Args:
            params (CommonParams): The parameters passed from the route.
            trunk_method (Callable): The ComicTrunk method for this route.
            item_id (str | None, optional): For routes that take an id parameter (e.g. /volume). Defaults to None.

        Returns:
            Response: The appropriate CV API compatible response.

        """
        if self.api_keys != [] and params.api_key not in self.api_keys:
            status_code, data = self._exception_responses[AuthenticationError]
        elif params.format == "jsonp" and (params.json_callback is None or params.json_callback == ""):
            status_code = status.HTTP_200_OK
            data = CVResponse(limit=0, status_code=103)
            params.format = 'json'
        else:
            try:
                data = await trunk_method(params=params) if item_id is None else await trunk_method(item_id=item_id, params=params)
                status_code=status.HTTP_200_OK

            except (RateLimitError, AuthenticationError, RequestLimitError, GatewayError, URLFormatError, ObjectNotFoundError,
                    UnsupportedResponseError, NotImplementedError) as ex:
                status_code, data= self._exception_responses[type(ex)]
            except ValidationError as ex:
                full_errors = ""
                for ex_error in ex.errors():
                    error_loc = '->'.join(map(str,list(ex_error["loc"])))
                    input_summary = f"{str(ex_error["input"])[:100]}{' ...' if len(str(ex_error["input"])) > 100 else ''}"  # noqa: PLR2004
                    error_msg = f"{ex_error["msg"]}: {error_loc}: {input_summary}"
                    full_errors = f"/n{error_msg}" if full_errors == "" else error_msg
                    logger.error(error_msg)
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT
                data=error_msg

        if not isinstance(data, CVResponse):
            return HTMLResponse(content=data, status_code=status_code)

        if params.format == "json":
            return JSONResponse(content=jsonable_encoder(data), status_code=status_code)

        if params.format == 'jsonp':
            return Response(content=jsonp_encoder(data, params.json_callback),  # ty:ignore[invalid-argument-type]
                status_code=status_code,
                media_type=r"text/javascript; charset=UTF-8")

        return Response(content=cvresponse_to_xml(data), status_code=status_code, media_type=r"application/xml")

    async def _get_volumes(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseVolume)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseVolume)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseVolume)

        return await self._fetch_response(params=params, trunk_method=self.trunk.volumes)

    async def _get_volume(self, volume_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.volume, item_id=volume_id)

    async def _get_search(self, params: Annotated[SearchParams, Query()]) -> Response:
        search_models: list[type[cvapimodels.BaseModelExtra]]= [
            cvapimodels.BaseCharacter,
            cvapimodels.BaseConcept,
            cvapimodels.BaseIssue,
            cvapimodels.BaseObject,
            cvapimodels.BaseOrigin,
            cvapimodels.BasePerson,
            cvapimodels.BasePublisher,
            cvapimodels.BaseStoryArc,
            cvapimodels.BaseTeam,
            cvapimodels.BaseVolume,
            cvapimodels.BaseEntity]

        params.sort = validate_sort_order(params.sort,
            model=search_models)
        params.field_list = validate_field_list(params.field_list,
            model=search_models)
        params.resources = validate_resource_list(params.resources)

        if params.field_list not in [None, '']:
            params.field_list = ','.join([*params.field_list.split(','), 'resource_type'])

        return await self._fetch_response(params=params, trunk_method=self.trunk.search)

    async def _get_types(self,
                        format: Literal['json', 'xml', 'jsonp'] = 'json',  # noqa: A002
                        api_key: str | None = None) -> Response:
        return await self._fetch_response(
            params=CommonParams.model_validate({'format':format, 'api_key': api_key}),
            trunk_method= self.trunk.types)

    async def _get_character(self, character_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailCharacter)

        return await self._fetch_response(params=params, trunk_method=self.trunk.character, item_id=character_id)

    async def _get_characters(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseVolume)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseVolume)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseVolume)

        return await self._fetch_response(params=params, trunk_method=self.trunk.characters)

    async def _get_concept(self, concept_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailConcept)

        return await self._fetch_response(params=params, trunk_method=self.trunk.concept, item_id=concept_id)

    async def _get_concepts(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseConcept)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseConcept)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseConcept)

        return await self._fetch_response(params=params, trunk_method=self.trunk.concepts)

    async def _get_episode(self, episode_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.episode, item_id=episode_id)

    async def _get_episodes(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.episodes)

    async def _get_issue(self, issue_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailIssue)

        return await self._fetch_response(params=params, trunk_method=self.trunk.issue, item_id=issue_id)

    async def _get_issues(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseIssue)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseIssue)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseIssue)

        return await self._fetch_response(params=params, trunk_method=self.trunk.issues)

    async def _get_location(self, location_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailLocation)

        return await self._fetch_response(params=params, trunk_method=self.trunk.location, item_id=location_id)

    async def _get_locations(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseLocation)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseLocation)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseLocation)

        return await self._fetch_response(params=params, trunk_method=self.trunk.locations)

    async def _get_movie(self, movie_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.movie, item_id=movie_id)

    async def _get_movies(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.movies)

    async def _get_object(self, object_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailObject)

        return await self._fetch_response(params=params, trunk_method=self.trunk.object, item_id=object_id)

    async def _get_objects(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseObject)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseObject)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseObject)

        return await self._fetch_response(params=params, trunk_method=self.trunk.objects)

    async def _get_origin(self, origin_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailOrigin)

        return await self._fetch_response(params=params, trunk_method=self.trunk.origin, item_id=origin_id)

    async def _get_origins(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseOrigin)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseOrigin)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseOrigin)

        return await self._fetch_response(params=params, trunk_method=self.trunk.origins)

    async def _get_person(self, person_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPerson)

        return await self._fetch_response(params=params, trunk_method=self.trunk.person, item_id=person_id)

    async def _get_people(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePerson)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePerson)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePerson)

        return await self._fetch_response(params=params, trunk_method=self.trunk.people)

    async def _get_power(self, power_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPower)

        return await self._fetch_response(params=params, trunk_method=self.trunk.power, item_id=power_id)

    async def _get_powers(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePower)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePower)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePower)

        return await self._fetch_response(params=params, trunk_method=self.trunk.powers)

    async def _get_publisher(self, publisher_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPublisher)

        return await self._fetch_response(params=params, trunk_method=self.trunk.publisher, item_id=publisher_id)

    async def _get_publishers(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePublisher)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePublisher)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePublisher)

        return await self._fetch_response(params=params, trunk_method=self.trunk.publishers)

    async def _get_series(self, series_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.series, item_id=series_id)

    async def _get_series_list(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return await self._fetch_response(params=params, trunk_method=self.trunk.series_list)

    async def _get_story_arc(self, story_arc_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailStoryArc)

        return await self._fetch_response(params=params, trunk_method=self.trunk.story_arc, item_id=story_arc_id)

    async def _get_story_arcs(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseStoryArc)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseStoryArc)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseStoryArc)

        return await self._fetch_response(params=params, trunk_method=self.trunk.story_arcs)

    async def _get_team(self, team_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailTeam)

        return await self._fetch_response(params=params, trunk_method=self.trunk.team, item_id=team_id)

    async def _get_teams(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseTeam)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseTeam)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseTeam)

        return await self._fetch_response(params=params, trunk_method=self.trunk.teams)

    async def _get_video(self, video_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.video, item_id=video_id)

    async def _get_videos(self, params: Annotated[FilterParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.videos)

    async def _get_video_type(self, video_type_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.video_type, item_id=video_type_id)

    async def _get_video_types(self, params: Annotated[FilterParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.video_types)

    async def _get_video_category(self, video_category_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.video_category, item_id=video_category_id)

    async def _get_video_categories(self, params: Annotated[FilterParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=self.trunk.video_categories)

    async def _get_object_not_found(self, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=lambda *_, **__: (_ for _ in ()).throw(ObjectNotFoundError), item_id=None)  # noqa: E501

    async def _get_url_format_error(self, params: Annotated[CommonParams, Query()]) -> Response:
        return await self._fetch_response(params=params, trunk_method=lambda *_, **__: (_ for _ in ()).throw(URLFormatError), item_id=None)

xml_resource_naming: dict[str, str] = {
    'character_credits' : 'character',
    'character_died_in' : 'character',
    'character_enemies' : 'character',
    'character_friends' : 'character',
    'characters' : 'character',
    'concept_credits' : 'concept',
    'created_characters' : 'character',
    'creators' : 'creator',
    'disbanded_in_issues' : 'issue',
    'episodes' : 'episode',
    'issue_credits' : 'issue',
    'issues_died_in' : 'issue',
    'isssues_disbanded_in' : 'issue',
    'isssue_credits' : 'issue',
    'location_credits' : 'location',
    'locations' : 'location',
    'movies' : 'movie',
    'object_credits' : 'object',
    'objects' : 'object',
    'people' : 'person',
    'person_credits' : 'person',
    'powers' : 'power',
    'story_arc_credits' : 'story_arc',
    'story_arcs' : 'story_arc',
    'team_credits' : 'team',
    'team_disbanded_in' : 'team',
    'team_enemies' : 'team',
    'team_friends' : 'team',
    'teams' : 'team',
    'volume_credits' : 'volume',
    'volumes' : 'volume',
}

def cvresponse_to_xml(response: CVResponse) -> str:
    """Encode the CVResponse object as XML."""
    root: _Element = etree.Element('response')
    etree.SubElement(root, 'error').text= etree.CDATA(response.error)  # ty:ignore[invalid-argument-type]
    etree.SubElement(root, 'limit').text = str(response.limit)
    etree.SubElement(root, 'offset').text = str(response.offset)
    etree.SubElement(root, 'number_of_page_results').text = str(response.number_of_page_results)
    etree.SubElement(root, 'number_of_total_results').text = str(response.number_of_total_results)
    etree.SubElement(root, 'status_code').text = str(response.status_code)
    results = etree.SubElement(root, 'results')

    if response.results is not None and response.results != []:
        if isinstance(response.results, BaseModelExtra):
            entity_to_xml(response.results, results)
        elif isinstance(response.results, list):
            for entity in response.results:
                container = etree.SubElement(results, entity._entity_name)  # noqa: SLF001
                entity_to_xml(entity, container)
        elif isinstance(response.results, dict):
            # Should only be used for the currently unmodelled endpoints
            for entry, value in response.results.items():
                etree.SubElement(results, entry).text = etree.CDATA(value) if isinstance(value, str) else str(value)
        else:
            logger.warning(f'Unrecognised attribute type for response results: {type(response.results)}')

    etree.SubElement(root, 'version').text = response.version

    return etree.tostring(root, encoding='utf8').decode()

def entity_to_xml(entity: cvapimodels.BaseModelExtra, parent: _Element) -> None:  # noqa: C901
    """Encode a response entity as XML."""
    for field_name, field_info in type(entity).model_fields.items():
        if getattr(entity, field_name) is None:
            etree.SubElement(parent, field_name)
            continue

        field = getattr(entity, field_name)

        if isinstance(field, int) or cvapimodels.FieldType.DateTime in field_info.metadata \
            or 'FieldType.DateTime' in str(field_info.annotation):
            etree.SubElement(parent, field_name).text = str(field)
        elif isinstance(field, str):
            etree.SubElement(parent, field_name).text = etree.CDATA(field)
        elif isinstance(field, dict):
            container = etree.SubElement(parent, field_name)
            for k, v in field.items():
                etree.SubElement(container, k).text = etree.CDATA(v) if isinstance(v, str) else str(v)
        elif isinstance(field, cvapimodels.BasicLinkedEntity):
            container = etree.SubElement(parent, field_name)
            linkedentity_to_xml(field, container)
        elif isinstance(field, cvapimodels.CVDate):
            container = etree.SubElement(parent, field_name)
            etree.SubElement(container, 'date').text = field.date
            etree.SubElement(container, 'timezone').text = etree.CDATA(field.timezone)
            etree.SubElement(container, 'timezone_type').text = str(field.timezone_type)
        elif isinstance(field, list):
            container = etree.SubElement(parent, field_name)
            child_element_name = xml_resource_naming.get(field_name, field_name.split('_')[0] if '_' in field_name else field_name[:-1])
            for child in field:
                child_element = etree.SubElement(container, child_element_name)
                if isinstance(child, cvapimodels.BasicLinkedEntity):
                    linkedentity_to_xml(child, child_element)
                else:
                    child_element.text = etree.CDATA(str(child))

def linkedentity_to_xml(entity: cvapimodels.BasicLinkedEntity, parent: _Element) -> None:
    """Encode BasicLinkedEntity and subclasses to XML."""
    etree.SubElement(parent, 'id').text = str(entity.id)
    etree.SubElement(parent, 'api_detail_url').text = etree.CDATA(entity.api_detail_url)
    etree.SubElement(parent, 'name').text = None if entity.name is None else etree.CDATA(entity.name)

    if isinstance(entity, cvapimodels.SiteLinkedEntity):
        etree.SubElement(parent, 'site_detail_url').text = etree.CDATA(entity.site_detail_url)

    if isinstance(entity, cvapimodels.LinkedIssue):
        etree.SubElement(parent, 'issue_number').text = None if entity.issue_number is None else str(entity.issue_number)

    if isinstance(entity, cvapimodels.CountedSiteLinkedEntity):
        etree.SubElement(parent, 'count').text = None if entity.count is None else str(entity.count)

    if isinstance(entity, cvapimodels.PersonCredits):
        etree.SubElement(parent, 'role').text = etree.CDATA(entity.role)

def jsonp_encoder(model: CVResponse, callback: str) -> str:
    """Nobody should really be using this but whatever."""
    return f'{callback}({json.dumps(jsonable_encoder(model))})'
