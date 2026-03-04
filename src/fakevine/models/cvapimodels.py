# ruff: noqa: D101
from typing import Any, Literal

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

## Request Models
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


## Response Models
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

class BasicLinkedEntity(BaseModel):
    api_detail_url: str
    id: int
    name: str | None

class LinkedIssue(BasicLinkedEntity):
    issue_number: str

class SiteLinkedEntity(BasicLinkedEntity):
    site_detail_url: str

class CoreEntityModel(BaseModel):
    id: int
    name: str
    api_detail_url: str
    site_detail_url: str

class BaseCharacter(CoreEntityModel):
    aliases: str | None = None
    birth: str | None
    count_of_issue_apperances: int = 0
    date_added: str
    date_last_updated: str
    deck: str | None
    description: str | None
    first_appeared_in_issue: LinkedIssue | None
    gender: int | None
    image: dict[str,str] | None
    origin: BasicLinkedEntity | None
    publisher: BasicLinkedEntity | None
    real_name: str | None

class DetailCharacter(BaseCharacter):
    character_enemies: list[SiteLinkedEntity] = []
    character_friends: list[SiteLinkedEntity] = []
    creators: list[SiteLinkedEntity] = []
    issue_credits: list[SiteLinkedEntity] = []
    issues_died_in: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    powers: list[BasicLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    team_enemies: list[SiteLinkedEntity] = []
    team_friends: list[SiteLinkedEntity] = []
    teams: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

class SearchCharacter(BaseCharacter):
    resource_type: Literal["character"] = "character"

class BaseConcept(CoreEntityModel):
    count_of_issue_apperances: int = 0
    date_added: str
    date_last_updated: str
    deck: str | None
    description: str | None
    first_appeared_in_issue: LinkedIssue | None
    image: dict[str,str] | None
    start_year: str | None

class DetailConcept(BaseConcept):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

class SearchConcept(BaseConcept):
    resource_type: Literal["concept"] = "concept"

# TODO: episode model

class AssociatedImages(BaseModel):
    original_url: str | None
    id: int
    caption: str | None
    image_tags: str | None

class BaseIssue(CoreEntityModel):
    aliases: str | None = None
    name: str | None
    cover_date: str | None
    date_added: str
    date_last_updated: str
    deck: str | None
    description: str | None
    has_staff_review: Literal[False] | SiteLinkedEntity
    image: dict[str,str] | None
    associated_images: list[AssociatedImages] = []
    issue_number: str | None # Unbelievable that this can be empty. "Mature data source."
    store_date: str | None
    volume: SiteLinkedEntity | None

class PersonCredits(SiteLinkedEntity):
    role: str

class DetailIssue(BaseIssue):
    character_credits: list[SiteLinkedEntity] = []
    character_died_in: list[SiteLinkedEntity] = []
    concept_credits: list[SiteLinkedEntity] = []
    first_appearance_characters: None = None
    first_appearance_concepts: None = None
    first_appearance_locations: None = None
    first_appearance_objects: None = None
    first_appearance_storyarcs: None = None
    first_appearance_teams: None = None
    location_credits: list[SiteLinkedEntity] = []
    object_credits: list[SiteLinkedEntity] = []
    person_credits: list[PersonCredits] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    team_credits: list[SiteLinkedEntity] = []
    team_disbanded_in: list[SiteLinkedEntity] = []

class SearchIssue(BaseIssue):
    resource_type: Literal["issue"] = "issue"

class BaseLocation(CoreEntityModel):
    aliases: str | None = None
    count_of_issue_appearances: int
    date_added: str
    date_last_updated: str
    deck: str | None
    description: str | None
    first_appeared_in_issue: LinkedIssue | None
    image: dict[str,str] | None
    start_year: str | None

class DetailLocation(BaseLocation):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

class SearchLocation(BaseLocation):
    resource_type: Literal["location"] = "location"

# TODO: movies model

class BaseObject(CoreEntityModel):
    aliases: str | None = None
    count_of_issue_appearances: int
    date_added: str
    date_last_updated: str
    deck: str | None
    description: str | None
    first_appeared_in_issue: LinkedIssue | None
    image: dict[str,str] | None
    start_year: str | None

class DetailObject(BaseObject):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

class SearchObject(BaseObject):
    resource_type: Literal["object"] = "object"

class BaseOrigin(SiteLinkedEntity):
    ...

class DetailOrigin(BaseOrigin):
    profiles: list = []  # Poorly documented rubbish
    character_set: Any | None # More Poorly documented rubbish
    characters: list[BasicLinkedEntity] = []

class SearchOrigin(BaseOrigin):
    resource_type: Literal["origin"] = "origin"




## Can potentially consolidate more.  Maybe a StoryElement base class, and a BookEntity base class?

class BaseVolume(CoreEntityModel):
    aliases: str | None = None
    count_of_issues: int
    date_added: str
    date_last_updated: str
    deck: str | None = None
    description: str | None
    first_issue: LinkedIssue | None
    image: dict[str,str] | None
    last_issue: LinkedIssue | None
    publisher: BasicLinkedEntity | None
    start_year: str | None

class DetailVolume(BaseVolume):
    characters : list[dict] | None = None
    issues : list[dict] | None = None
    locations : list[dict] | None = None
    objects : list[dict] | None = None

class SingleResponse[T](CVResponse):
    results: T | list = []

class MultiResponse[T](CVResponse):
    results: list[T] = []

class SearchVolume(BaseVolume):
    resource_type: Literal["volume"] = "volume"

# TODO: Refactor this to be created programatically?
class SearchResponse(CVResponse):
    results: list[
        SearchVolume |
        SearchCharacter |
        SearchConcept |
        SearchIssue |
        SearchObject |
        SearchOrigin |
        CVResponse] = []
