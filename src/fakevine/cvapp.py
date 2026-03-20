from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import FastAPI, Query, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import HTMLResponse, JSONResponse, Response
from loguru import logger
from pydantic_core import ValidationError

from fakevine.models import cvapimodels
from fakevine.models.cvapimodels import (
    CommonParams,
    CVResponse,
    FilterParams,
    SearchParams,
    validate_field_list,
    validate_filter_list,
    validate_sort_order,
)
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    GatewayError,
    RateLimitError,
    RequestLimitError,
    UnsupportedResponseError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic import BaseModel


class CVApp:
    """FastAPI App for ComicVine API compatible endpoints.

    Handles routing and processing of requests to backend ComicTrunk.

    Attributes
    ----------
    OBJECT_NOT_FOUND, INVALID_API_KEY, RATE_LIMITED, REQUEST_LIMIT_BREACH, URL_FORMAT_ERROR : Response
        Responses to match CV's HTTP status codes and content.
    app : FastAPI
        FastAPI app instance.
    api_key : str | None
        Optional API key for basic authentication.
    trunk : ComicTrunk
        ComicTrunk instance for data operations.

    """

    OBJECT_NOT_FOUND: JSONResponse = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={key:value for key, value in
            jsonable_encoder(CVResponse(limit=0, status_code=101)).items() if key != 'version'})
    INVALID_API_KEY: JSONResponse = JSONResponse(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content={key:value for key, value in
            jsonable_encoder(CVResponse(limit=0, status_code=100)).items() if key != 'version'})
    RATE_LIMITED: HTMLResponse = HTMLResponse(
        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
        content=r"<title>429</title>429 Too Many Requests")
    REQUEST_LIMIT_BREACH: JSONResponse = JSONResponse(
        status_code=420,
        content={key:value for key, value in
            jsonable_encoder(CVResponse(limit=0, status_code=107)).items() if key != 'version'})
    DEADEND_RESPONSE: JSONResponse = JSONResponse(
        status_code=status.HTTP_200_OK,
        content={"error": "OK", "limit": None, "offset": None, "number_of_page_results": 0,
                "number_of_total_results": 0, "status_code": 1, "results": [], "version": "1.0" })
    URL_FORMAT_ERROR: JSONResponse = JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={key:value for key, value in
            jsonable_encoder(CVResponse(limit=0, status_code=102)).items() if key != 'version'})

    app: FastAPI
    api_key: str | None = None
    trunk: ComicTrunk

    def __init__(self, trunk: ComicTrunk, api_key: str | None = None) -> None:
        """Initialize the CVRouter with a ComicTrunk and optional API key.

        Args:
            trunk (ComicTrunk): The comic trunk instance for data operations.
            api_key (str | None, optional): The API key for authentication. Defaults to None.

        """
        self.api_key = api_key
        self.trunk = trunk
        self.app = FastAPI(exception_handlers={RequestValidationError : self._validation_exception_handler})
        self._attach_routes()

        self._exception_responses = {
            RateLimitError : CVApp.RATE_LIMITED,
            AuthenticationError : CVApp.INVALID_API_KEY,
            RequestLimitError : CVApp.REQUEST_LIMIT_BREACH,
            GatewayError: HTMLResponse(status_code=status.HTTP_502_BAD_GATEWAY,
                content="<html><title>502 Bad Gateway</title><body>502 Bad Gateway</body></html>"),
        }

    async def _validation_exception_handler(self, request: Request, exc: RequestValidationError) -> Response:  # noqa: ARG002
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
            ('/chats', self._get_cv_deadend, "Chat Search", False),
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
            ('/promos', self._get_cv_deadend, "Promo Search", False),
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
            ('/*', self._get_undefined, "Catch All", False),
        ]

        for route in routes:
            self.app.add_api_route(
                methods=['GET'],
                path=route[0],
                endpoint=route[1],
                name=route[2],
                include_in_schema=route[3])

    def _fetch_response(self, params: CommonParams, trunk_method: Callable | None, item_id: int | None = None) -> Response:
        """Handle passing parameters to the ComicTrunk and processing the response into the correct format.

        Args:
            params (CommonParams): The parameters passed from the route.
            trunk_method (Callable | None): The ComicTrunk method for this route.  If None, is an unused CV endpoint.
            item_id (str | None, optional): For routes that take an id parameter (e.g. /volume). Defaults to None.

        Returns:
            Response: The appropriate CV API compatible response.

        """
        if self.api_key is not None and params.api_key is None:
            return CVApp.INVALID_API_KEY

        # TODO@falo2k:  Process conversion of responses into other formats
        # https://github.com/falo2k/fakevine/issues/2
        if params.format != "json":
            return CVApp.OBJECT_NOT_FOUND

        if trunk_method is None:
            data = self.DEADEND_RESPONSE
        else:
            try:
                data = trunk_method(params=params) if item_id is None else trunk_method(item_id=item_id, params=params)

            except (RateLimitError, AuthenticationError, RequestLimitError, GatewayError) as ex:
                return self._exception_responses[type(ex)]  # ty:ignore[invalid-argument-type]
            except (UnsupportedResponseError, NotImplementedError) as ex:
                error_msg = f"Response not handled ({trunk_method.__name__}): {ex}"  # ty:ignore[unresolved-attribute]
                logger.error(error_msg)
                return JSONResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content={'error':error_msg})
            except ValidationError as ex:
                for ex_error in ex.errors():
                    error_loc = '->'.join(list(ex_error["loc"]))  # ty:ignore[no-matching-overload]
                    input_summary = f"{str(ex_error["input"])[:100]}{' ...' if len(str(ex_error["input"])) > 100 else ''}"  # noqa: PLR2004
                    error_msg = f"{ex_error["msg"]}: {error_loc}: {input_summary}"
                    logger.error(error_msg)
                return JSONResponse(
                    status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                    content=jsonable_encoder({"errors": ex.errors()}),
                )

            # TODO@falo2k:  Process conversion of responses into other formats
            # https://github.com/falo2k/fakevine/issues/2

        return data

    async def _get_volumes(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseVolume)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseVolume)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseVolume)

        return self._fetch_response(params=params, trunk_method=self.trunk.volumes)

    async def _get_volume(self, volume_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.volume, item_id=volume_id)

    async def _get_search(self, params: Annotated[SearchParams, Query()]) -> Response:
        if params.query is None:
            return CVApp.OBJECT_NOT_FOUND

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

        if params.field_list not in [None, '']:
            params.field_list = ','.join([*params.field_list.split(','), 'resource_type'])

        return self._fetch_response(params=params, trunk_method=self.trunk.search)

    async def _get_types(self,
                        format: Literal['json', 'xml', 'jsonp'] = 'json',  # noqa: A002
                        api_key: str | None = None) -> Response:
        return self._fetch_response(
            params=CommonParams.model_validate({'format':format, 'api_key': api_key}),
            trunk_method= self.trunk.types)

    async def _get_character(self, character_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailCharacter)

        return self._fetch_response(params=params, trunk_method=self.trunk.character, item_id=character_id)

    async def _get_characters(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseVolume)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseVolume)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseVolume)

        return self._fetch_response(params=params, trunk_method=self.trunk.characters)

    async def _get_concept(self, concept_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailConcept)

        return self._fetch_response(params=params, trunk_method=self.trunk.concept, item_id=concept_id)

    async def _get_concepts(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseConcept)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseConcept)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseConcept)

        return self._fetch_response(params=params, trunk_method=self.trunk.concepts)

    async def _get_episode(self, episode_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.episode, item_id=episode_id)

    async def _get_episodes(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.episodes)

    async def _get_issue(self, issue_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailIssue)

        return self._fetch_response(params=params, trunk_method=self.trunk.issue, item_id=issue_id)

    async def _get_issues(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseIssue)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseIssue)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseIssue)

        return self._fetch_response(params=params, trunk_method=self.trunk.issues)

    async def _get_location(self, location_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailLocation)

        return self._fetch_response(params=params, trunk_method=self.trunk.location, item_id=location_id)

    async def _get_locations(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseLocation)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseLocation)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseLocation)

        return self._fetch_response(params=params, trunk_method=self.trunk.locations)

    async def _get_movie(self, movie_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.movie, item_id=movie_id)

    async def _get_movies(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.movies)

    async def _get_object(self, object_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailObject)

        return self._fetch_response(params=params, trunk_method=self.trunk.object, item_id=object_id)

    async def _get_objects(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseObject)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseObject)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseObject)

        return self._fetch_response(params=params, trunk_method=self.trunk.objects)

    async def _get_origin(self, origin_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailOrigin)

        return self._fetch_response(params=params, trunk_method=self.trunk.origin, item_id=origin_id)

    async def _get_origins(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseOrigin)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseOrigin)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseOrigin)

        return self._fetch_response(params=params, trunk_method=self.trunk.origins)

    async def _get_person(self, person_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPerson)

        return self._fetch_response(params=params, trunk_method=self.trunk.person, item_id=person_id)

    async def _get_people(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePerson)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePerson)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePerson)

        return self._fetch_response(params=params, trunk_method=self.trunk.people)

    async def _get_power(self, power_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPower)

        return self._fetch_response(params=params, trunk_method=self.trunk.power, item_id=power_id)

    async def _get_powers(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePower)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePower)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePower)

        return self._fetch_response(params=params, trunk_method=self.trunk.powers)

    async def _get_publisher(self, publisher_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailPublisher)

        return self._fetch_response(params=params, trunk_method=self.trunk.publisher, item_id=publisher_id)

    async def _get_publishers(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BasePublisher)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BasePublisher)
        params.filter = validate_filter_list(params.filter, cvapimodels.BasePublisher)

        return self._fetch_response(params=params, trunk_method=self.trunk.publishers)

    async def _get_series(self, series_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.series, item_id=series_id)

    async def _get_series_list(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseEntity)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseEntity)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseEntity)

        return self._fetch_response(params=params, trunk_method=self.trunk.series_list)

    async def _get_story_arc(self, story_arc_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailStoryArc)

        return self._fetch_response(params=params, trunk_method=self.trunk.story_arc, item_id=story_arc_id)

    async def _get_story_arcs(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseStoryArc)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseStoryArc)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseStoryArc)

        return self._fetch_response(params=params, trunk_method=self.trunk.story_arcs)

    async def _get_team(self, team_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        params.field_list = validate_field_list(params.field_list, cvapimodels.DetailTeam)

        return self._fetch_response(params=params, trunk_method=self.trunk.team, item_id=team_id)

    async def _get_teams(self, params: Annotated[FilterParams, Query()]) -> Response:
        params.sort = validate_sort_order(params.sort, cvapimodels.BaseTeam)
        params.field_list = validate_field_list(params.field_list, cvapimodels.BaseTeam)
        params.filter = validate_filter_list(params.filter, cvapimodels.BaseTeam)

        return self._fetch_response(params=params, trunk_method=self.trunk.teams)

    async def _get_video(self, video_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video, item_id=video_id)

    async def _get_videos(self, params: Annotated[FilterParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.videos)

    async def _get_video_type(self, video_type_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_type, item_id=video_type_id)

    async def _get_video_types(self, params: Annotated[FilterParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_types)

    async def _get_video_category(self, video_category_id: int, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_category, item_id=video_category_id)

    async def _get_video_categories(self, params: Annotated[FilterParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_categories)

    async def _get_cv_deadend(self, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=None)

    async def _get_object_not_found(self, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=lambda *_, **__: self.OBJECT_NOT_FOUND, item_id=None)

    async def _get_url_format_error(self, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=lambda *_, **__: self.URL_FORMAT_ERROR, item_id=None)

    async def _get_undefined(self) -> HTMLResponse:
        return HTMLResponse(content="Unknown route", status_code=status.HTTP_404_NOT_FOUND)
