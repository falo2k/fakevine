import traceback
from typing import TYPE_CHECKING, Annotated, Literal

from fastapi import APIRouter, Query, status
from fastapi.encoders import jsonable_encoder
from fastapi.responses import HTMLResponse, JSONResponse, Response

from fakevine.models.cvapimodels import CommonParams, CVResponse, FilterParams, SearchParams
from fakevine.trunks.comic_trunk import (
    AuthenticationError,
    ComicTrunk,
    RateLimitError,
    RequestLimitError,
    UnsupportedResponseError, GatewayError,
)

if TYPE_CHECKING:
    from collections.abc import Callable

class CVRouter:
    """Router for ComicVine API compatible endpoints.

    Handles routing and processing of requests to backend ComicTrunk.

    Attributes
    ----------
    OBJECT_NOT_FOUND, INVALID_API_KEY, RATE_LIMITED, REQUEST_LIMIT_BREACH : Response
        Eesponses to match CV's HTTP status codes and content.
    router : APIRouter
        FastAPI router instance.
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

    router: APIRouter
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
        self.router = APIRouter()
        self._attach_routes()

    def _attach_routes(self) -> None:
        routes =[
            ('/volumes', self._get_volumes, "Volume Search"),
            ('/volume/{volume_id}', self._get_volume, "Volume Detail"),
            ('/search', self._get_search, "General Search"),
            ('/types', self._get_types, "Type Data"),
            ('/character/{character_id}', self._get_character, "Character Detail"),
            ('/characters', self._get_characters, "Character Search"),
            ('/chat/{chat_id}', self._get_chat, "Chat Detail"),
            ('/chats', self._get_chats, "Chat Search"),
            ('/concept/{concept_id}', self._get_concept, "Concept Detail"),
            ('/concepts', self._get_concepts, "Concept Search"),
            ('/episode/{episode_id}', self._get_episode, "Episode Detail"),
            ('/episodes', self._get_episodes, "Episode Search"),
            ('/issue/{issue_id}', self._get_issue, "Issue Detail"),
            ('/issues', self._get_issues, "Issue Search"),
            ('/location/{location_id}', self._get_location, "Location Detail"),
            ('/locations', self._get_locations, "Location Search"),
            ('/movie/{movie_id}', self._get_movie, "Movie Detail"),
            ('/movies', self._get_movies, "Movie Search"),
            ('/object/{object_id}', self._get_object, "Object Detail"),
            ('/objects', self._get_objects, "Object Search"),
            ('/origin/{origin_id}', self._get_origin, "Origin Detail"),
            ('/origins', self._get_origins, "Origin Search"),
            ('/person/{person_id}', self._get_person, "Person Detail"),
            ('/people/{people_id}', self._get_people, "People Detail"),
            ('/power/{power_id}', self._get_power, "Power Detail"),
            ('/powers', self._get_powers, "Power Search"),
            ('/promo/{promo_id}', self._get_promo, "Promo Detail"),
            ('/promos', self._get_promos, "Promo Search"),
            ('/publisher/{publisher_id}', self._get_publisher, "Publisher Detail"),
            ('/publishers', self._get_publishers, "Publisher Search"),
            ('/series', self._get_series, "Serie Search"),
            ('/series_list/{series_list_id}', self._get_series_list, "Series_list Detail"),
            ('/search/{search_id}', self._get_search, "Search Detail"),
            ('/story_arc/{story_arc_id}', self._get_story_arc, "Story_arc Detail"),
            ('/story_arcs', self._get_story_arcs, "Story_arc Search"),
            ('/team/{team_id}', self._get_team, "Team Detail"),
            ('/teams', self._get_teams, "Team Search"),
            ('/video/{video_id}', self._get_video, "Video Detail"),
            ('/videos', self._get_videos, "Video Search"),
            ('/video_type/{video_type_id}', self._get_video_type, "Video_type Detail"),
            ('/video_types', self._get_video_types, "Video_type Search"),
            ('/video_category/{video_category_id}', self._get_video_category, "Video_category Detail"),
            ('/video_categories', self._get_video_categories, "Video_categorie Search"),
        ]

        for route in routes:
            self.router.add_api_route(methods=['GET'], path=route[0], endpoint=route[1], name=route[2])

        self.router.add_api_route(methods=['GET'], path='/*',
            endpoint=self._get_undefined, name="Catch All", include_in_schema=False)

    def _fetch_response(self, params: CommonParams, trunk_method: Callable, item_id: str | None = None) -> Response:
        """Handle passing parameters to the ComicTrunk and processing the response into the correct format.

        Args:
            params (CommonParams): The parameters passed from the route.
            trunk_method (Callable): The ComicTrunk method for this route.
            item_id (str | None, optional): For routes that take an id parameter (e.g. /volume). Defaults to None.

        Returns:
            Response: The appropriate CV API compatible response.

        """
        if self.api_key is not None and params.api_key is None:
            return CVRouter.INVALID_API_KEY

        # TODO Process conversion of responses into other formats
        if params.format != "json":
            return CVRouter.OBJECT_NOT_FOUND

        exception_responses = {
            RateLimitError : CVRouter.RATE_LIMITED,
            AuthenticationError : CVRouter.INVALID_API_KEY,
            RequestLimitError : CVRouter.REQUEST_LIMIT_BREACH,
            GatewayError: HTMLResponse(status_code=status.HTTP_502_BAD_GATEWAY, 
                content="<html><title>502 Bad Gateway</title><body>502 Bad Gateway</body></html>"),
        }

        try:
            data = trunk_method(params=params) if item_id is None else trunk_method(item_id=item_id, params=params)
        except (RateLimitError, AuthenticationError, RequestLimitError, GatewayError) as ex:
            return exception_responses[type(ex)]
        except UnsupportedResponseError:
            exception_html = f'<html><title>Unsupported Feature</title><body>{traceback.format_exc()}</body></html>'
            return HTMLResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=exception_html)

        return data

    async def _get_volumes(self, params: Annotated[FilterParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.volumes)

    async def _get_volume(self, volume_id: str, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.volume, item_id=volume_id)

    async def _get_search(self, params: Annotated[SearchParams, Query()]) -> Response:
        if params.query is None:
            return CVRouter.OBJECT_NOT_FOUND

        return self._fetch_response(params=params, trunk_method=self.trunk.search)

    async def _get_types(self, format: Literal['json', 'xml', 'jsonp'] = 'json', api_key: str | None = None) -> Response:
        return self._fetch_response(
            params=CommonParams.model_validate({'format':format, 'api_key': api_key}),
            trunk_method= self.trunk.types)

    async def _get_character(self, character_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.character, item_id=character_id)

    async def _get_characters(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.characters)

    async def _get_chat(self, chat_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.chat, item_id=chat_id)

    async def _get_chats(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.chats)

    async def _get_concept(self, concept_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.concept, item_id=concept_id)

    async def _get_concepts(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.concepts)

    async def _get_episode(self, episode_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.episode, item_id=episode_id)

    async def _get_episodes(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.episodes)

    async def _get_issue(self, issue_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.issue, item_id=issue_id)

    async def _get_issues(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.issues)

    async def _get_location(self, location_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.location, item_id=location_id)

    async def _get_locations(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.locations)

    async def _get_movie(self, movie_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.movie, item_id=movie_id)

    async def _get_movies(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.movies)

    async def _get_object(self, object_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.object, item_id=object_id)

    async def _get_objects(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.objects)

    async def _get_origin(self, origin_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.origin, item_id=origin_id)

    async def _get_origins(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.origins)

    async def _get_person(self, person_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.person, item_id=person_id)

    async def _get_people(self, people_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.people, item_id=people_id)

    async def _get_power(self, power_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.power, item_id=power_id)

    async def _get_powers(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.powers)

    async def _get_promo(self, promo_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.promo, item_id=promo_id)

    async def _get_promos(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.promos)

    async def _get_publisher(self, publisher_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.publisher, item_id=publisher_id)

    async def _get_publishers(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.publishers)

    async def _get_series(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.series)

    async def _get_series_list(self, series_list_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.series_list, item_id=series_list_id)

    async def _get_search(self, search_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.search, item_id=search_id)

    async def _get_story_arc(self, story_arc_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.story_arc, item_id=story_arc_id)

    async def _get_story_arcs(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.story_arcs)

    async def _get_team(self, team_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.team, item_id=team_id)

    async def _get_teams(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.teams)

    async def _get_video(self, video_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video, item_id=video_id)

    async def _get_videos(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.videos)

    async def _get_video_type(self, video_type_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_type, item_id=video_type_id)

    async def _get_video_types(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_types)

    async def _get_video_category(self, video_category_id: str, params: Annotated[CommonParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_category, item_id=video_category_id)

    async def _get_video_categories(self, params: Annotated[FilterParams, Query()]) ->Response:
        return self._fetch_response(params=params, trunk_method=self.trunk.video_categories)


    async def _get_undefined(self) -> HTMLResponse:
        return HTMLResponse(content="Unknown route", status_code=status.HTTP_404_NOT_FOUND)
