# ruff: noqa: D101, FIX002
import datetime
from enum import Enum
from typing import Annotated, Any, Literal

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    computed_field,
)

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

class FieldType(Enum):
    """An enum to mark fields in the model metadata for validation functions."""

    Sortable = 1
    Filterable = 2
    DateTime = 3

## Utility functions for request parameter validation
def split_and_validate_field_list(value: str | None, model: type[BaseModel]) -> list[str] | None:
    """Transform field_list in request params using CV's logic."""
    if value is None or value == "":
        return None

    fields = [field for field in value.split(',') if field in model.model_fields]

    return None if len(fields) == 0 else fields

def validate_field_list(value: str | None, model: type[BaseModel]) -> str | None:
    """Validate field_list in request params using CV's logic."""
    split = split_and_validate_field_list(value, model)

    return None if split is None else ','.join(split)

def split_and_validate_filter_list(value: str | None, model: type[BaseModel]) -> list[str] | None:
    """Transform field_list in request params using CV's logic."""
    if value is None or value == "":
        return None

    items = []
    filterable: list[str] = [field for field in model.model_fields if FieldType.Filterable in model.model_fields[field].metadata]
    datetime_fields: list[str] = [field for field in model.model_fields if FieldType.DateTime in model.model_fields[field].metadata]
    for filter_string in value.split(','):
        split_sort = filter_string.split(':',1)
        if len(split_sort) < 2 or split_sort[1] == '':  # noqa: PLR2004
            continue

        split_sort[1] = split_sort[1].lower()

        # At some point could test behaviour for what happens if only one half is invalid.
        try:
            if split_sort[0] in datetime_fields:
                dates = split_sort[1].split('|',maxsplit=1)
                dates[0] = check_and_fix_date_fields(dates[0])
                if len(dates) > 1:
                    dates[1] = check_and_fix_date_fields(dates[1])

                split_sort[1] = '|'.join(dates)
        except ValueError:
            continue

        if split_sort[0] in filterable:
            items.append(':'.join(split_sort))

    return None if len(items) == 0 else items

def check_and_fix_date_fields(date_string: str) -> str:
    """Validate and normlalise date/datetime strings from requests."""
    # ruff: disable[DTZ007]
    format_strings = {
        '%Y-%m-%d %H:%M:%S': '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M:': '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:%M': '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H:': '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d %H': '%Y-%m-%d %H:%M:%S',
        '%Y-%m-%d': '%Y-%m-%d',
    }

    date_string = date_string.strip()
    for test_format, output_format in format_strings.items():
        try:
            parsed_date = datetime.datetime.strptime(date_string, test_format)
            return parsed_date.strftime(output_format)
        except ValueError:
            continue

    # ruff: enable[DTZ007]
    raise ValueError

def validate_filter_list(value: str | None, model: type[BaseModel]) -> str | None:
    """Validate field_list in request params using CV's logic."""
    split = split_and_validate_filter_list(value, model)

    return None if split is None else ','.join(split)

def split_and_validate_sort_order(value: str | None, model: type[BaseModel]) -> tuple[str, str] | None:
    """Transform sort in request params using CV's logic.

    From observation, CV does consider comma delimited lists, but then ignores all
    but the last valid sort element.  There is no multisort.  ASC is default.
    """
    if value is None or value == "":
        return None

    items = []
    sortable = [field for field in model.model_fields if FieldType.Sortable in model.model_fields[field].metadata]
    for sorter in value.split(','):
        split_sort = sorter.split(':',1)
        if len(split_sort) < 2 or split_sort[1] == '':  # noqa: PLR2004
            split_sort.append('asc')

        split_sort[1] = split_sort[1].lower()

        if split_sort[1] not in ['asc', 'desc']:
            split_sort[1] = 'asc'

        if split_sort[0] in sortable:
            items.append(tuple(split_sort))

    return None if len(items) == 0 else items[-1]

def validate_sort_order(value: str | None, model: type[BaseModel]) -> str | None:
    """Validate sort_order in request params using CV's logic."""
    validated = split_and_validate_sort_order(value, model)

    return None if validated is None else f'{validated[0]}:{validated[1]}'

## Request Models
class CommonParams(BaseModel):
    api_key: str | None = None
    format: Literal['json', 'xml', 'jsonp'] = 'json'
    field_list: Annotated[str | None, "Comma delimited list of fields"] = None

class FilterParams(CommonParams):
    limit: int = Field(100, gt=0, le=100)
    offset: int = Field(0, ge=0)
    sort: Annotated[str | None, "Sort by field and direction (asc/desc) in the format field:asc"] = "id:asc"
    filter: Annotated[str | None, "Filters to apply.  Comma delimited of the form field:value, or field:valA|valB for date ranges"] = None

class SearchParams(CommonParams):
    limit: int = Field(10, gt=0, le=10)
    offset: int = Field(0, ge=0)
    sort: Annotated[str | None, "Sort by field and direction (asc/desc) in the format field:asc"] = "id:asc"
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
    model_config = ConfigDict(frozen = True)

    api_detail_url: str
    id: int
    name: str | None

    # Equality and Hash functions defined for quick deduplication of references
    def __eq__(self, other: object) -> bool:
        """Equality check assumes ID uniqueness for data deduplication."""
        if not isinstance(other, BasicLinkedEntity):
            return NotImplemented

        return self.id == other.id

    def __hash__(self) -> int:
        """Hash check assumes ID uniqueness for data deduplication."""
        return self.id

class LinkedIssue(BasicLinkedEntity):
    issue_number: str | None

class SiteLinkedEntity(BasicLinkedEntity):
    site_detail_url: str

class BaseEntity(BaseModel):
    aliases: str | None = None
    api_detail_url: str
    date_added: Annotated[str,
        "Date format is %Y-%m-%d %H:%M:%S - Data is UTC-7/8 (PDT/PST depending on time of year)",
        FieldType.Sortable, FieldType.Filterable, FieldType.DateTime]
    date_last_updated: Annotated[str,
        "Date format is %Y-%m-%d %H:%M:%S - Data is UTC-7/8 (PDT/PST depending on time of year)",
        FieldType.Sortable, FieldType.Filterable, FieldType.DateTime]
    deck: str | None = None
    description: str | None = None
    id: Annotated[int, FieldType.Sortable, FieldType.Filterable]
    image: dict[str, str | None] | None = None
    name: Annotated[str | None, FieldType.Sortable, FieldType.Filterable] = None
    site_detail_url: str

class BaseCharacter(BaseEntity):
    birth: Annotated[str, "Date string in the form %Y-%m-%d %H:%M:%S"] | None
    count_of_issue_apperances: int = 0
    first_appeared_in_issue: LinkedIssue | None
    gender: Annotated[int | None, FieldType.Filterable]
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
    cover_date: Annotated[str | None, 'Response format is %Y-%m-%d but the filter format can be anything up to %Y-%m-%d %H:%M:%S',
    FieldType.Sortable, FieldType.Filterable, FieldType.DateTime]
    has_staff_review: Literal[False] | SiteLinkedEntity
    issue_number: Annotated[str | None, FieldType.Filterable, FieldType.Sortable] # Unbelievable this can be empty. "Mature data source"
    store_date: Annotated[str | None, 'Response format is %Y-%m-%d but the filter format can be anything up to %Y-%m-%d %H:%M:%S',
        FieldType.Sortable, FieldType.Filterable, FieldType.DateTime]
    volume: Annotated[SiteLinkedEntity | None, FieldType.Filterable]

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
    count_of_issue_appearances: int | None
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
    count_of_issue_appearances: int | None
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
    id: Annotated[int, FieldType.Sortable, FieldType.Filterable]
    name: Annotated[str | None, FieldType.Sortable, FieldType.Filterable] = None
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
