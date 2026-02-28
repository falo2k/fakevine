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
    UnsupportedResponseError,
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

        error_html = f'<html><title>Unsupported Feature</title><body>{traceback.format_exc()}</body></html>'
        exception_responses = {
            RateLimitError : CVRouter.RATE_LIMITED,
            AuthenticationError : CVRouter.INVALID_API_KEY,
            RequestLimitError : CVRouter.REQUEST_LIMIT_BREACH,
            UnsupportedResponseError : HTMLResponse(status_code=status.HTTP_501_NOT_IMPLEMENTED, content=error_html),
        }

        try:
            data = trunk_method(params=params) if item_id is None else trunk_method(item_id=item_id, params=params)
        except (RateLimitError, AuthenticationError, RequestLimitError, UnsupportedResponseError) as ex:
            return exception_responses[type(ex)]

        return data

    async def _get_volumes(self, params: Annotated[FilterParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method= self.trunk.volumes)

    async def _get_volume(self, volume_id: str, params: Annotated[CommonParams, Query()]) -> Response:
        return self._fetch_response(params=params, trunk_method= self.trunk.volume, item_id=volume_id)

    async def _get_search(self, params: Annotated[SearchParams, Query()]) -> Response:
        if params.query is None:
            return CVRouter.OBJECT_NOT_FOUND

        return self._fetch_response(params=params, trunk_method= self.trunk.search)

    async def _get_types(self, format: Literal['json', 'xml', 'jsonp'] = 'json', api_key: str | None = None) -> Response:
        return self._fetch_response(
            params=CommonParams.model_validate({'format':format, 'api_key': api_key}),
            trunk_method= self.trunk.types)

    async def _get_undefined(self) -> HTMLResponse:
        return HTMLResponse(content="Unknown route", status_code=status.HTTP_404_NOT_FOUND)
