# ruff: noqa: D101, FIX002
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, computed_field

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
    field_list: Annotated[list[str], "Comma delimited list of fields"] | None = None

class FilterParams(CommonParams):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort: Annotated[str, "Sort by field and direction (asc/desc) in the format field:asc"] | None = "id:asc"
    filter: str | None = None

class SearchParams(CommonParams):
    limit: int = Field(10, gt=0, le=10)
    offset: int = Field(0, ge=0)
    sort: str | None = "id:asc"
    query: str | None = None


## Response Models
class CVResponse(BaseModel):
    model_config = ConfigDict(extra='allow')

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

class SingleResponse[T](CVResponse):
    results: T | list = []

class MultiResponse[T](CVResponse):
    results: list[T] = []

class BasicLinkedEntity(BaseModel):
    api_detail_url: str
    id: int
    name: str | None

class LinkedIssue(BasicLinkedEntity):
    issue_number: str

class SiteLinkedEntity(BasicLinkedEntity):
    site_detail_url: str

class BaseEntity(BaseModel):
    aliases: str | None = None
    api_detail_url: str
    date_added: Annotated[str, "Date format is %Y-%m-%d %H:%M:%S - Data is UTC-7/8 (PDT/PST depending on time of year)"]  # noqa: E501
    date_last_updated: Annotated[str, "Date format is %Y-%m-%d %H:%M:%S - Data is UTC-7/8 (PDT/PST depending on time of year)"]  # noqa: E501
    deck: str | None = None
    description: str | None = None
    id: int
    image: dict[str, str | None] | None = None
    name: str | None = None
    site_detail_url: str

class BaseCharacter(BaseEntity):
    birth: Annotated[str, "Date string in the form %Y-%m-%d %H:%M:%S"] | None
    count_of_issue_apperances: int = 0
    first_appeared_in_issue: LinkedIssue | None
    gender: int | None
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

class BaseConcept(BaseEntity):
    count_of_issue_apperances: int = 0
    first_appeared_in_issue: LinkedIssue | None
    start_year: str | None

class DetailConcept(BaseConcept):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

# TODO@falo2k: episode model
# https://github.com/falo2k/fakevine/issues/1

class AssociatedImages(BaseModel):
    original_url: str | None
    id: int
    caption: str | None
    image_tags: str | None

class BaseIssue(BaseEntity):
    associated_images: list[AssociatedImages] = []
    cover_date: str | None
    has_staff_review: Literal[False] | SiteLinkedEntity
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

class BaseLocation(BaseEntity):
    count_of_issue_appearances: int
    first_appeared_in_issue: LinkedIssue | None
    start_year: str | None

class DetailLocation(BaseLocation):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

# TODO@falo2k: movies model
# https://github.com/falo2k/fakevine/issues/1

class BaseObject(BaseEntity):
    count_of_issue_appearances: int
    first_appeared_in_issue: LinkedIssue | None
    start_year: str | None

class DetailObject(BaseObject):
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

# Note that BaseOrigin does not use the common entity base of other models
class BaseOrigin(BaseModel):
    api_detail_url: str
    id: int
    name: str | None
    site_detail_url: str

class DetailOrigin(BaseOrigin):
    profiles: list = []  # Poorly documented rubbish
    character_set: Any | None # More Poorly documented rubbish
    characters: list[BasicLinkedEntity] = []

class CVDate(BaseModel):
    date: Annotated[str, "Date string in the form %Y-%m-%d %H:%M:%S.%f"]
    timezone: Annotated[str, "e.g. America/Los_Angeles"]
    timezone_type: Annotated[Literal[3], "Can't find evidence of any other value than 3 here"] = 3

class BasePerson(BaseEntity):
    birth: Annotated[str, "Date string in the form %Y-%m-%d %H:%M:%S"] | None
    country: str | None
    count_of_isssue_appearances: Annotated[int, "Yes, isssue.  You want to fight about it?"] | None
    death: Annotated[CVDate, "Of course this is an entirely different format to birth.  Of course it is."] | None
    email: str | None = None
    gender: Annotated[int, "0: Unknown, 1: Male, 2 or 3: Female"] | None
    hometown: str | None
    website: str | None

class DetailPerson(BasePerson):
    created_characters: list[SiteLinkedEntity] = []
    issues: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

# /powers doesn't use deck or image from the common entity model
class BasePower(BaseEntity):
    deck: None = None
    image: None = None

class DetailPower(BasePower):
    characters: list[SiteLinkedEntity] = []

class BasePublisher(BaseEntity):
    location_address: str | None
    location_city:  str | None
    location_state:  str | None

class DetailPublisher(BasePublisher):
    characters: list[SiteLinkedEntity] = []
    story_arcs: list[SiteLinkedEntity] = []
    teams: list[SiteLinkedEntity] = []
    volumes: list[SiteLinkedEntity] = []

# TODO@falo2k: series model
# https://github.com/falo2k/fakevine/issues/1

class BaseStoryArc(BaseEntity):
    count_of_isssue_appearances: Annotated[int, "Yes, isssue.  You want to fight about it?"] | None
    first_appeared_in_episode: dict[str,Any] | None
    first_appeared_in_issue: LinkedIssue | None
    publisher: SiteLinkedEntity | None

class DetailStoryArc(BaseStoryArc):
    episodes: list[SiteLinkedEntity] = []
    issues: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []

class BaseTeam(BaseEntity):
    count_of_isssue_appearances: Annotated[int, "Yes, isssue.  You want to fight about it?"] | None
    count_of_team_members: int
    first_appeared_in_issue: LinkedIssue | None
    publisher: BasicLinkedEntity | None

class DetailTeam(BaseTeam):
    character_enemies: list[SiteLinkedEntity] = []
    character_friends: list[SiteLinkedEntity] = []
    characters: list[SiteLinkedEntity] = []
    disbanded_in_issues: list[SiteLinkedEntity] = []
    isssues_disbanded_in: Annotated[list[SiteLinkedEntity], "Yes, isssues again."] = []
    issue_credits: list[SiteLinkedEntity] = []
    movies: list[SiteLinkedEntity] = []
    story_arc_credits: list[SiteLinkedEntity] = []
    volume_credits: list[SiteLinkedEntity] = []

class BaseTypes(BaseModel):
    detail_resource_name: str
    id: int
    list_resource_name: str

# TODO@falo2k: video* models
# https://github.com/falo2k/fakevine/issues/1

class BaseVolume(BaseEntity):
    count_of_issues: int
    first_issue: LinkedIssue | None
    last_issue: LinkedIssue | None
    publisher: BasicLinkedEntity | None
    start_year: str | None

class DetailVolume(BaseVolume):
    characters : list[dict] | None = None
    issues : list[dict] | None = None
    locations : list[dict] | None = None
    objects : list[dict] | None = None

class SearchCharacter(BaseCharacter):
    resource_type: Literal["character"] = "character"

class SearchConcept(BaseConcept):
    resource_type: Literal["concept"] = "concept"

class SearchIssue(BaseIssue):
    resource_type: Literal["issue"] = "issue"

class SearchLocation(BaseLocation):
    resource_type: Literal["location"] = "location"

class SearchObject(BaseObject):
    resource_type: Literal["object"] = "object"

class SearchOrigin(BaseOrigin):
    resource_type: Literal["origin"] = "origin"

class SearchPerson(BasePerson):
    resource_type: Literal["person"] = "person"

class SearchVolume(BaseVolume):
    resource_type: Literal["volume"] = "volume"

class SearchPublisher(BasePublisher):
    resource_type: Literal["publisher"] = "publisher"

class SearchStoryArc(BaseStoryArc):
    resource_type: Literal["story_arc"] = "story_arc"

class SearchTeam(BaseTeam):
    resource_type: Literal["team"] = "team"

class SearchResponse(CVResponse):
    results: list[
        SearchCharacter |
        SearchConcept |
        SearchIssue |
        SearchObject |
        SearchOrigin |
        SearchPerson |
        SearchPublisher |
        SearchStoryArc |
        SearchTeam |
        SearchVolume |
        BaseEntity] = []
