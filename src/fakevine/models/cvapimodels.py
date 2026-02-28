# ruff: noqa: D101
from typing import Literal

from pydantic import BaseModel, Field, computed_field

CV_STATUS_CODES: dict[int, str] = {
    1:      "OK",
    100:    "Invalid API Key", # 404
    101:    "Object Not Found",
    102:    "Error in URL Format",
    103:    "'jsonp' format requires a 'json_callback' argument",
    104:    "Filter Error",
    105:    "Subscriber only video is for subscribers only",
    107:    "Rate limit exceeded.  Slow down cowboy.",#107
}


class CommonParams(BaseModel):
    api_key: str | None = None
    format: Literal['json', 'xml', 'jsonp'] = 'json'
    field_list: list[str] | None = None


class FilterParams(CommonParams):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort: str | None = "id:asc"
    filter: str | None = None


class SearchParams(CommonParams):
    limit: int = Field(10, gt=0, le=10)
    offset: int = Field(0, ge=0)
    sort: str | None = "id:asc"
    query: str | None = None


class CVResponse(BaseModel):
    @computed_field
    def error(self) -> str:  # noqa: D102
        return CV_STATUS_CODES.get(self.status_code, "Unrecognised status_code")
    limit: int = Field(100, ge=0, le=100)
    offset: int = Field(0, ge=0)
    number_of_page_results: int = Field(0, ge=0)
    number_of_total_results: int = Field(0, ge=0)
    status_code: Literal[1, 100, 101, 102, 103, 104, 105, 107] = 1
    results: list[dict] | dict = []
    version: str | None = "1.0"

class BaseVolume(BaseModel):
    aliases: str | None = None
    api_detail_url : str
    count_of_issues: int
    date_added: str
    date_last_updated: str
    deck: str | None = None
    description: str
    first_issue: dict
    id: int
    image: dict[str,str]
    last_issue: dict
    name: str
    publisher: dict
    site_detail_url: str
    start_year: str

class DetailVolume(BaseVolume):
    characters : list[dict] | None = None
    issues : list[dict] | None = None
    locations : list[dict] | None = None
    objects : list[dict] | None = None

class VolumeResponse(CVResponse):
    results: DetailVolume | list = []

class VolumesResponse(CVResponse):
    results: list[BaseVolume] = []


class SearchVolume(BaseVolume):
    resource_type: Literal["volume"] = "volume"

class SearchResponse(CVResponse):
    results: list[SearchVolume | CVResponse] = []
