"""Validation unit tests for CV API models."""
# ruff: noqa: S101, D103, ANN201, PLR2004
import pytest
from pydantic import ValidationError

from fakevine.models.cvapimodels import (
    BaseEntity,
    BaseVolume,
    CVResponse,
    DetailCharacter,
    DetailConcept,
    DetailIssue,
    DetailOrigin,
    DetailPerson,
    DetailPublisher,
    DetailTeam,
    DetailVolume,
    FilterParams,
    MultiResponse,
    SearchParams,
    SearchResponse,
    SearchVolume,
    SingleResponse,
    split_and_validate_field_list,
    split_and_validate_filter_list,
    split_and_validate_sort_order,
    validate_field_list,
    validate_filter_list,
    validate_sort_order,
)

# helpers for model construction

def base_entity_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for BaseEntity-derived models."""
    base = {
        "api_detail_url": "https://example.com/api/test/1/",
        "date_added": "2020-01-01 00:00:00",
        "date_last_updated": "2020-01-01 00:00:00",
        "id": 1,
        "site_detail_url": "https://comicvine.gamespot.com/test/1/",
    }
    base.update(extra)
    return base


def detail_character_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailCharacter with all required fields."""
    base = base_entity_kwargs(
        birth=None,
        count_of_issue_apperances=0,
        first_appeared_in_issue=None,
        gender=None,
        origin=None,
        publisher=None,
        real_name=None,
    )
    base.update(extra)
    return base


def detail_issue_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailIssue with all required fields."""
    base = base_entity_kwargs(
        cover_date=None,
        has_staff_review=False,
        issue_number=None,
        store_date=None,
        volume=None,
    )
    base.update(extra)
    return base


def detail_person_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailPerson with all required fields."""
    base = base_entity_kwargs(
        birth=None,
        country=None,
        count_of_isssue_appearances=None,
        death=None,
        email=None,
        gender=None,
        hometown=None,
        website=None,
    )
    base.update(extra)
    return base


def detail_concept_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailConcept with all required fields."""
    base = base_entity_kwargs(
        count_of_issue_apperances=0,
        first_appeared_in_issue=None,
        start_year=None,
    )
    base.update(extra)
    return base


def detail_volume_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailVolume with all required fields."""
    base = base_entity_kwargs(
        count_of_issues=0,
        first_issue=None,
        last_issue=None,
        publisher=None,
        start_year=None,
    )
    base.update(extra)
    return base


def detail_origin_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailOrigin (doesn't extend BaseEntity)."""
    base = {
        "api_detail_url": "https://example.com/api/origin/1/",
        "id": 1,
        "name": None,
        "site_detail_url": "https://comicvine.gamespot.com/origin/1/",
        "character_set": None,
    }
    base.update(extra)
    return base


def detail_team_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailTeam with all required fields."""
    base = base_entity_kwargs(
        count_of_isssue_appearances=None,
        count_of_team_members=0,
        first_appeared_in_issue=None,
        publisher=None,
    )
    base.update(extra)
    return base


def detail_publisher_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for DetailPublisher with all required fields."""
    base = base_entity_kwargs(
        location_address=None,
        location_city=None,
        location_state=None,
    )
    base.update(extra)
    return base


def search_volume_kwargs(**extra):  # noqa: ANN003
    """Build kwargs for SearchVolume with all required fields."""
    base = base_entity_kwargs(
        count_of_issues=0,
        first_issue=None,
        last_issue=None,
        publisher=None,
        start_year=None,
    )
    base.update(extra)
    return base


# ---------------------------------------------------------------------------
# FilterParams validation tests
# ---------------------------------------------------------------------------


class TestFilterParams:
    """Validation tests for FilterParams request model."""

    def test_filter_params_defaults(self):
        """Test FilterParams has correct default values."""
        fp = FilterParams()
        assert fp.limit == 100
        assert fp.offset == 0
        assert fp.sort == "id:asc"
        assert fp.filter is None
        assert fp.format == "json"

    def test_filter_params_limit_boundary_valid(self):
        """Test FilterParams accepts valid limit values."""
        assert FilterParams(limit=1).limit == 1
        assert FilterParams(limit=50).limit == 50
        assert FilterParams(limit=100).limit == 100

    def test_filter_params_limit_zero_invalid(self):
        """Test FilterParams rejects limit of 0."""
        with pytest.raises(ValidationError) as exc:
            FilterParams(limit=0)
        assert "greater than 0" in str(exc.value)

    def test_filter_params_limit_exceeds_max(self):
        """Test FilterParams rejects limit > 100."""
        with pytest.raises(ValidationError) as exc:
            FilterParams(limit=101)
        assert "less than or equal to 100" in str(exc.value)

    def test_filter_params_negative_offset_invalid(self):
        """Test FilterParams rejects negative offset."""
        with pytest.raises(ValidationError) as exc:
            FilterParams(offset=-1)
        assert "greater than or equal to 0" in str(exc.value)

    def test_filter_params_valid_offset(self):
        """Test FilterParams accepts valid offset values."""
        assert FilterParams(offset=0).offset == 0
        assert FilterParams(offset=100).offset == 100


# ---------------------------------------------------------------------------
# SearchParams validation tests
# ---------------------------------------------------------------------------


class TestSearchParams:
    """Validation tests for SearchParams request model."""

    def test_search_params_defaults(self):
        """Test SearchParams has correct default values."""
        sp = SearchParams()
        assert sp.limit == 10
        assert sp.offset == 0
        assert sp.sort == "id:asc"
        assert sp.query is None
        assert sp.format == "json"

    def test_search_params_limit_boundary_valid(self):
        """Test SearchParams accepts valid limit values."""
        assert SearchParams(limit=1).limit == 1
        assert SearchParams(limit=5).limit == 5
        assert SearchParams(limit=10).limit == 10

    def test_search_params_limit_zero_invalid(self):
        """Test SearchParams rejects limit of 0."""
        with pytest.raises(ValidationError) as exc:
            SearchParams(limit=0)
        assert "greater than 0" in str(exc.value)

    def test_search_params_limit_exceeds_max(self):
        """Test SearchParams rejects limit > 10."""
        with pytest.raises(ValidationError) as exc:
            SearchParams(limit=11)
        assert "less than or equal to 10" in str(exc.value)

    def test_search_params_with_query(self):
        """Test SearchParams with query parameter."""
        sp = SearchParams(query="test")
        assert sp.query == "test"


# ---------------------------------------------------------------------------
# CVResponse validation tests
# ---------------------------------------------------------------------------


class TestCVResponse:
    """Validation tests for CVResponse model."""

    def test_cvresponse_defaults(self):
        """Test CVResponse has correct default values."""
        r = CVResponse()
        assert r.status_code == 1
        assert r.limit == 100
        assert r.offset == 0
        assert r.number_of_page_results == 0
        assert r.number_of_total_results == 0
        assert r.version == "1.0"
        assert r.results == []

    def test_cvresponse_computed_error_field_ok(self):
        """Test CVResponse computed error field for OK status."""
        r = CVResponse(status_code=1)
        assert r.error == "OK"

    def test_cvresponse_computed_error_field_not_found(self):
        """Test CVResponse computed error field for not found."""
        r = CVResponse(status_code=101)
        assert r.error == "Object Not Found"

    def test_cvresponse_computed_error_field_invalid_api_key(self):
        """Test CVResponse computed error field for invalid API key."""
        r = CVResponse(status_code=100)
        assert r.error == "Invalid API Key"

    @pytest.mark.parametrize("status_code", [1, 100, 101, 102, 103, 104, 105, 107])
    def test_cvresponse_valid_status_codes(self, status_code: int):
        """Test CVResponse accepts all valid status codes."""
        r = CVResponse(status_code=status_code)  # ty:ignore[invalid-argument-type]
        assert r.status_code == status_code

    def test_cvresponse_invalid_status_code(self):
        """Test CVResponse rejects invalid status codes."""
        with pytest.raises(ValidationError) as exc:
            CVResponse(status_code=999)  # ty:ignore[invalid-argument-type]
        assert "status_code" in str(exc.value)

    def test_cvresponse_limit_boundary(self):
        """Test CVResponse limit validation."""
        assert CVResponse(limit=0).limit == 0
        assert CVResponse(limit=100).limit == 100
        with pytest.raises(ValidationError):
            CVResponse(limit=101)

    def test_cvresponse_extra_fields_allowed(self):
        """Test CVResponse allows extra fields per ConfigDict."""
        r = CVResponse(extra_field="value")  # ty:ignore[unknown-argument]
        assert r.extra_field == "value"  # ty:ignore[unresolved-attribute]


# ---------------------------------------------------------------------------
# SingleResponse and MultiResponse validation tests
# ---------------------------------------------------------------------------


class TestSingleAndMultiResponse:
    """Validation tests for SingleResponse and MultiResponse."""

    def test_single_response_dict_results(self):
        """Test SingleResponse with dict results."""
        sr = SingleResponse[dict](results={"id": 1})
        assert sr.results == {"id": 1}

    def test_single_response_default_empty(self):
        """Test SingleResponse defaults to empty list."""
        sr = SingleResponse[dict]()
        assert sr.results == []

    def test_multi_response_list_results(self):
        """Test MultiResponse with list results."""
        mr = MultiResponse[dict](results=[{"id": 1}, {"id": 2}])
        assert len(mr.results) == 2

    def test_multi_response_default_empty(self):
        """Test MultiResponse defaults to empty list."""
        mr = MultiResponse[dict]()
        assert mr.results == []

    def test_multi_response_typed_results(self):
        """Test MultiResponse preserves item types."""
        mr = MultiResponse[int](results=[1, 2, 3])
        assert mr.results == [1, 2, 3]


# ---------------------------------------------------------------------------
# BaseEntity validation tests
# ---------------------------------------------------------------------------


class TestBaseEntity:
    """Validation tests for BaseEntity model."""

    def test_base_entity_required_fields(self):
        """Test BaseEntity requires api_detail_url, dates, id, site_detail_url."""
        ent = BaseEntity(**base_entity_kwargs())
        assert ent.id == 1
        assert ent.api_detail_url == "https://example.com/api/test/1/"

    def test_base_entity_missing_api_detail_url(self):
        """Test BaseEntity rejects missing api_detail_url."""
        data = base_entity_kwargs()
        del data["api_detail_url"]
        with pytest.raises(ValidationError) as exc:
            BaseEntity(**data)
        assert "api_detail_url" in str(exc.value)

    def test_base_entity_missing_id(self):
        """Test BaseEntity rejects missing id."""
        data = base_entity_kwargs()
        del data["id"]
        with pytest.raises(ValidationError) as exc:
            BaseEntity(**data)
        assert "id" in str(exc.value)

    def test_base_entity_optional_fields(self):
        """Test BaseEntity accepts optional fields."""
        ent = BaseEntity(**base_entity_kwargs(
            aliases="Alias",
            name="Test",
            deck="Description",
            description="Full description",
        ))
        assert ent.aliases == "Alias"
        assert ent.name == "Test"
        assert ent.deck == "Description"
        assert ent.description == "Full description"

    def test_base_entity_none_optional_values(self):
        """Test BaseEntity nullable optional fields."""
        ent = BaseEntity(**base_entity_kwargs())
        assert ent.aliases is None
        assert ent.name is None
        assert ent.deck is None
        assert ent.description is None


# ---------------------------------------------------------------------------
# SearchResponse validation tests
# ---------------------------------------------------------------------------


class TestSearchResponse:
    """Validation tests for SearchResponse model."""

    def test_search_response_defaults(self):
        """Test SearchResponse defaults to empty results."""
        sr = SearchResponse()
        assert sr.results == []
        assert sr.status_code == 1

    def test_search_response_mixed_base_entity_and_search_volume(self):
        """Test SearchResponse with mixture of BaseEntity and SearchVolume objects."""
        entity = BaseEntity(**base_entity_kwargs(id=1, aliases="Test"))
        volume = SearchVolume(**search_volume_kwargs(id=2, name="Volume 1"))
        sr = SearchResponse(results=[entity, volume])
        assert len(sr.results) == 2
        assert sr.results[0].id == 1
        assert sr.results[1].id == 2
        assert isinstance(sr.results[0], BaseEntity)
        assert isinstance(sr.results[1], SearchVolume)




# ---------------------------------------------------------------------------
# DetailCharacter validation tests
# ---------------------------------------------------------------------------


class TestDetailCharacter:
    """Validation tests for DetailCharacter model."""

    def test_detail_character_collections_default(self):
        """Test DetailCharacter collections default to empty lists."""
        c = DetailCharacter(**detail_character_kwargs())
        assert c.character_enemies == []
        assert c.character_friends == []
        assert c.creators == []
        assert c.teams == []
        assert c.powers == []

    def test_detail_character_inherited_fields(self):
        """Test DetailCharacter inherits BaseEntity required fields."""
        c = DetailCharacter(**detail_character_kwargs())
        assert c.id == 1
        assert c.api_detail_url == "https://example.com/api/test/1/"


# ---------------------------------------------------------------------------
# DetailIssue validation tests
# ---------------------------------------------------------------------------


class TestDetailIssue:
    """Validation tests for DetailIssue model."""

    def test_detail_issue_collections_default(self):
        """Test DetailIssue collections default to empty lists."""
        i = DetailIssue(**detail_issue_kwargs())
        assert i.character_credits == []
        assert i.person_credits == []
        assert i.team_credits == []

    def test_detail_issue_first_appearance_fields_none(self):
        """Test DetailIssue first_appearance fields are None."""
        i = DetailIssue(**detail_issue_kwargs())
        assert i.first_appearance_characters is None
        assert i.first_appearance_concepts is None


# ---------------------------------------------------------------------------
# DetailPerson validation tests
# ---------------------------------------------------------------------------


class TestDetailPerson:
    """Validation tests for DetailPerson model."""

    def test_detail_person_collections_default(self):
        """Test DetailPerson collections default to empty lists."""
        p = DetailPerson(**detail_person_kwargs())
        assert p.created_characters == []
        assert p.issues == []
        assert p.story_arc_credits == []


# ---------------------------------------------------------------------------
# DetailPublisher validation tests
# ---------------------------------------------------------------------------


class TestDetailPublisher:
    """Validation tests for DetailPublisher model."""

    def test_detail_publisher_collections_default(self):
        """Test DetailPublisher collections default to empty lists."""
        pub = DetailPublisher(**detail_publisher_kwargs())
        assert pub.characters == []
        assert pub.story_arcs == []
        assert pub.teams == []
        assert pub.volumes == []


# ---------------------------------------------------------------------------
# DetailOrigin validation tests
# ---------------------------------------------------------------------------


class TestDetailOrigin:
    """Validation tests for DetailOrigin model."""

    def test_detail_origin_profiles_default(self):
        """Test DetailOrigin profiles default to empty list."""
        o = DetailOrigin(**detail_origin_kwargs())
        assert o.profiles == []

    def test_detail_origin_characters_default(self):
        """Test DetailOrigin characters default to empty list."""
        o = DetailOrigin(**detail_origin_kwargs())
        assert o.characters == []


# ---------------------------------------------------------------------------
# DetailTeam validation tests
# ---------------------------------------------------------------------------


class TestDetailTeam:
    """Validation tests for DetailTeam model."""

    def test_detail_team_requires_count_of_team_members(self):
        """Test DetailTeam requires count_of_team_members."""
        with pytest.raises(ValidationError) as exc:
            DetailTeam(**base_entity_kwargs())
        assert "count_of_team_members" in str(exc.value)

    def test_detail_team_with_count_of_team_members(self):
        """Test DetailTeam with count_of_team_members."""
        t = DetailTeam(**detail_team_kwargs())
        assert t.count_of_team_members == 0

    def test_detail_team_collections_default(self):
        """Test DetailTeam collections default to empty lists."""
        t = DetailTeam(**detail_team_kwargs(count_of_team_members=5))
        assert t.characters == []
        assert t.character_enemies == []
        assert t.isssues_disbanded_in == []


# ---------------------------------------------------------------------------
# DetailConcept validation tests
# ---------------------------------------------------------------------------


class TestDetailConcept:
    """Validation tests for DetailConcept model."""

    def test_detail_concept_collections_default(self):
        """Test DetailConcept collections default to empty lists."""
        c = DetailConcept(**detail_concept_kwargs())
        assert c.issue_credits == []
        assert c.movies == []
        assert c.volume_credits == []


# ---------------------------------------------------------------------------
# DetailVolume validation tests
# ---------------------------------------------------------------------------


class TestDetailVolume:
    """Validation tests for DetailVolume model."""

    def test_detail_volume_requires_count_of_issues(self):
        """Test DetailVolume requires count_of_issues."""
        with pytest.raises(ValidationError) as exc:
            DetailVolume(**base_entity_kwargs())
        assert "count_of_issues" in str(exc.value)

    def test_detail_volume_with_count_of_issues(self):
        """Test DetailVolume with count_of_issues."""
        v = DetailVolume(**detail_volume_kwargs(count_of_issues=50))
        assert v.count_of_issues == 50

    def test_detail_volume_collections_none_by_default(self):
        """Test DetailVolume collections default to None."""
        v = DetailVolume(**detail_volume_kwargs(count_of_issues=50))
        assert v.characters is None
        assert v.issues is None
        assert v.locations is None


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------

def test_filter_params_valid_and_invalid():
    fp = FilterParams()
    assert fp.limit == 100
    with pytest.raises(ValidationError):
        FilterParams(limit=0)


def test_search_params_valid_and_invalid():
    sp = SearchParams()
    assert sp.limit == 10
    with pytest.raises(ValidationError):
        SearchParams(limit=11)


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------

def test_cvresponse_defaults_and_error():
    r = CVResponse()
    assert r.status_code == 1
    assert r.error == "OK"
    with pytest.raises(ValidationError):
        CVResponse(status_code=999)  # ty:ignore[invalid-argument-type]


def test_single_and_multi_response():
    single = SingleResponse[dict](results={"foo": "bar"})
    assert single.results == {"foo": "bar"}
    multi = MultiResponse[int](results=[1, 2, 3])
    assert multi.results == [1, 2, 3]


# ---------------------------------------------------------------------------
# Validation functions
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('id,name,date_last_updated', ['id', 'name', 'date_last_updated']),
        ('id,invalid_field,name', ['id', 'name']),
        ('', None),
        ('id', ['id']),
        ('ID,NAME,DATE_LAST_UPDATED', None),  # case sensitve arguments
        ('id, name , date_last_updated', ['id']),  # with spaces
        ('count_of_issues,start_year', ['count_of_issues', 'start_year']),
        ('nonexistent', None),
        ('id,,name', ['id', 'name']),  # empty fields
    ],
)
def test_split_and_validate_field_list(input_str: str, expected: list[str] | None) -> None:
    assert split_and_validate_field_list(input_str, BaseVolume) == expected

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('id,name,monkeys,date_last_updated', 'id,name,date_last_updated'),
        ('id,invalid,name', 'id,name'),
        ('', None),
        ('id', 'id'),
        ('ID,NAME,DATE_LAST_UPDATED', None),
        ('id, name , date_last_updated', 'id'),
        ('count_of_issues,start_year', 'count_of_issues,start_year'),
        ('nonexistent', None),
        ('id,,name', 'id,name'),
    ],
)
def test_validate_field_list(input_str: str, expected: str | None) -> None:
    assert validate_field_list(input_str, BaseVolume) == expected

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('date_last_updated:2009,daft:punk,name:,id,date_last_updated:2009-01-01 01:01:01', ['date_last_updated:2009-01-01 01:01:01']),
        ('id:1,name:test', ['id:1', 'name:test']),
        ('date_added:2020-01-01 00:00:00', ['date_added:2020-01-01 00:00:00']),
        ('invalid_field:value', None),
        ('name:', None),  # empty value
        ('ID:1,name:Image,DATE_LAST_UPDATED:2009', ['name:image']),
        ('id:1|2', ['id:1|2']),  # range indicator for non-datetime
        ('date_last_updated:invalid_date', None),  # invalid date
        ('', None),
        ('id:123,date_last_updated:2020-01-01 00:00:00|2020-01-02 00:00:00', [
            'id:123',
            'date_last_updated:2020-01-01 00:00:00|2020-01-02 00:00:00']),
    ]
)
def test_split_and_validate_filter_list(input_str: str, expected: list[str] | None) -> None:
    assert split_and_validate_filter_list(input_str, BaseVolume) == expected

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('date_last_updated:2009,daft:punk,name:,id,date_last_updated:2009-01-01 01:01:01', 'date_last_updated:2009-01-01 01:01:01'),
        ('id:1,name:test', 'id:1,name:test'),
        ('date_added:2020-01-01 00:00:00', 'date_added:2020-01-01 00:00:00'),
        ('invalid_field:value', None),
        ('name:', None),
        ('id:1|2', 'id:1|2'),
        ('date_last_updated:invalid_date', None),
        ('', None),
        ('id:123,date_last_updated:2020-01-01 00:00:00|2020-01-02 00:00:00', 'id:123,date_last_updated:2020-01-01 00:00:00|2020-01-02 00:00:00'),
    ],
)
def test_validate_filter_list(input_str: str, expected: str | None) -> None:
    assert validate_filter_list(input_str, BaseVolume) == expected

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('nothing:asdasd,name:desc,id:sgbsdg', ('id', 'asc')),
        ('name:desc', ('name', 'desc')),
        ('name:Desc', ('name', 'desc')),
        ('Name:desc', None),
        ('id:asc', ('id', 'asc')),
        ('date_last_updated:desc', ('date_last_updated', 'desc')),
        ('invalid:desc', None),
        ('name:invalid', ('name', 'asc')),  # invalid direction defaults to asc
        ('', None),
        ('id', ('id', 'asc')),  # no direction
        ('name:desc,id:asc', ('id', 'asc')),  # takes last valid
        ('nonexistent:desc,invalid:asc,name:desc', ('name', 'desc')),
    ],
)
def test_split_and_validate_sort_order(input_str: str, expected: tuple[str, str] | None) -> None:
    assert split_and_validate_sort_order(input_str, BaseVolume) == expected

@pytest.mark.parametrize(
    ("input_str", "expected"),
    [
        ('nothing:asdasd,name:desc,id:sgbsdg', 'id:asc'),
        ('name:desc', 'name:desc'),
        ('id:asc', 'id:asc'),
        ('date_last_updated:desc', 'date_last_updated:desc'),
        ('invalid:desc', None),
        ('name:invalid', 'name:asc'),
        ('', None),
        ('id', 'id:asc'),
        ('name:desc,id:asc', 'id:asc'),
        ('nonexistent:desc,invalid:asc,name:desc', 'name:desc'),
    ],
)
def test_validate_sort_order(input_str: str, expected: str | None) -> None:
    assert validate_sort_order(input_str, BaseVolume) == expected
