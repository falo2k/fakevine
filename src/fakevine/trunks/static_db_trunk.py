# ruff: noqa: EM101, D102
import re
from typing import TYPE_CHECKING, Any

from cachetools import TTLCache
from cachetools.keys import hashkey
from cachetools_async import cached
from loguru import logger
from sqlalchemy import (
    Engine,
    Float,
    Integer,
    Row,
    Select,
    Sequence,
    String,
    asc,
    cast,
    create_engine,
    func,
    literal_column,
    or_,
    select,
)
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql.expression import text

from fakevine.models import cvapimodels as api
from fakevine.models import cvdbmodels as db
from fakevine.trunks.comic_trunk import ComicTrunk, ObjectNotFoundError

if TYPE_CHECKING:
    import datetime
    from collections.abc import Callable
    from pathlib import Path

    from pydantic.fields import FieldInfo
    from sqlalchemy.orm import Query
    from sqlalchemy.sql.base import ReadOnlyColumnCollection
    from sqlalchemy.sql.elements import KeyedColumnElement


class StaticDBTrunk(ComicTrunk):
    """A Comic Trunk backed by a static SQLite database of data.

    The database used should adhere to the schema defined in fakevine-utils.  Only supports
    comic data, not TV/Movies.
    """

    def __init__(self, database_path: Path) -> None:
        """Create a Static DB Trunk.

        Args:
            database_path (Path): Path to the database file.  Schema should match that returned by fakevine-utils.

        """
        self.db_engine: Engine = create_engine(f"sqlite:///{database_path.absolute()}")
        self.async_engine: AsyncEngine = create_async_engine(f"sqlite+aiosqlite:///{database_path.absolute()}")
        self.session = async_sessionmaker(self.async_engine, expire_on_commit=False)

        try:
            with self.db_engine.connect() as conn:
                conn.execute(text("SELECT 'hello engine'"))
        except DatabaseError:
            logger.exception("Input database is not a valid SQL database")
            raise

        # TODO@falo2k: Validate database schema

        self._base_entity_fields = ['id', 'api_detail_url', 'name', 'aliases', 'deck', 'description', 'image', 'site_detail_url']

    def _datetime_format(self, date_time: datetime.datetime) -> str:
        return date_time.strftime('%Y-%m-%d %H:%M:%S')

    def _date_format(self, date: datetime.date) -> str:
        return date.strftime('%Y-%m-%d')

    def _birth_date_format(self, date: datetime.date) -> str:
        return date.strftime('%b %d, %Y')

    def _rows_to_list(self, rows: Sequence[Row], container_class: type[api.BaseModel]) -> list:
        def inner_func(row: Row) -> api.BaseModel:
            return container_class(**row._asdict())

        return list(map(inner_func, rows))

    def _build_filtered_query(self, query: Select, filter_list: list[str], field_list: dict[str, FieldInfo]) -> Query:
        columns: ReadOnlyColumnCollection[str, KeyedColumnElement[Any]] = query.get_final_froms()[0].columns

        for filter_entry in filter_list:
            if ':' not in filter_entry:
                logger.error(f"A filter ({filter_entry}) that isn't well formatted has slipped through.  Ignoring.")
                continue

            filter_name, filter_value = filter_entry.split(':')

            if filter_name not in field_list:
                logger.error(f"A filter ({filter_name}) that isn't possible has slipped through.  Ignoring.")
                continue

            field_info = field_list[filter_name]
            if api.FieldType.DateTime in field_info.metadata:
                try:
                    if '|' in filter_value:
                        lower_bound, upper_bound = tuple(filter_value.split('|'))
                        query = query \
                            .where(columns[filter_name] >= api.parse_date_string(lower_bound)) \
                            .where(columns[filter_name] <= api.parse_date_string(upper_bound))
                    else:
                        query = query.where(columns[filter_name] == api.parse_date_string(filter_value))
                except ValueError:
                    logger.error(f'Could not parse date filter values {filter_value} for {filter_name}.  Ignoring.')
                    continue
            elif filter_name == 'gender':
                # Special case on Character models.  Rejects anything after a pipe.
                query = query.where(columns[filter_name] == api.CharacterGender[filter_value.split('|')[0]])
            elif 'str' in str(field_info.annotation):
                query = query.where(columns[filter_name].contains(filter_value))
            # Special case for volume as it is id mapped
            elif 'int' in str(field_info.annotation) or filter_name == 'volume':
                column_name = 'volume_id' if filter_name == 'volume' else filter_name
                # Undocumented search feature for ids (the only integer filters) to have an "OR" list pipe delimited
                query = query.where(columns[column_name].in_(filter_value.split('|')))
            else:
                error_msg = f'Do not know how to handle filter for {filter_name} with type {field_info.annotation}.  Ignoring.'
                logger.error(error_msg)

        return query

    @cached(cache=TTLCache(ttl=360, maxsize=128), key=lambda _, params, db_table, *__:
        hashkey(params.field_list, db_table.__tablename__))
    async def _generate_single_response(self, item_id: int, params: api.CommonParams, db_table: type[db.BaseTable],
                            api_model: type[api.BaseModelExtra], mapping_function: Callable) -> api.SingleResponse[api.BaseModelExtra]:
        async with self.session() as session:
            item_query: Query = await session.execute(select(db_table).where(db_table.id == int(item_id)))
            item_row: Row = item_query.first()

            if item_row is None:
                return api.SingleResponse[api_model](limit=0, status_code=101)  # ty:ignore[invalid-type-form]

            if params.field_list is None or params.field_list == "":
                field_list = api_model.model_fields.keys()
                return_class = api_model
            else:
                field_list = params.field_list.split(',')
                return_class = api.filtered_model(api_model, field_list)

            item_record = item_row[0]

            response_dict =  await mapping_function(item_record, field_list, session)

            response_object = return_class(**response_dict)

            return api.SingleResponse[return_class](  # ty:ignore[invalid-type-form]
                limit=1,
                number_of_page_results=1,
                number_of_total_results=1,
                status_code=1,
                results=response_object)

    @cached(cache=TTLCache(ttl=360, maxsize=128), key=lambda _, params, db_table, *__:
        hashkey(params.field_list, params.limit, params.offset, params.sort, params.filter, params.page, db_table.__tablename__))
    async def _generate_multi_response(self, params: api.FilterParams, db_table: type[db.BaseTable], api_model: type[api.BaseModelExtra],
                                        mapping_function: Callable) -> api.MultiResponse[api.BaseModelExtra]:
        async with self.session() as session:
            sort_params = ('id', 'asc') if params.sort is None or params.sort == "" else tuple(params.sort.split(':'))
            sort_string = f'{sort_params[0]} {sort_params[1].upper()}'

            filter_list = [] if params.filter is None else params.filter.split(',')

            item_count_query: Query = select(func.count(db_table.id))
            item_query: Query = select(db_table) \
                .order_by(text(sort_string)).offset(params.offset).limit(params.limit)

            if params.field_list is None or params.field_list == []:
                field_list = api_model.model_fields.keys()
                return_class = api_model
            else:
                field_list = params.field_list.split(',')
                return_class = api.filtered_model(api_model, field_list)

            item_query = self._build_filtered_query(item_query, filter_list, api_model.model_fields)
            item_count_query = self._build_filtered_query(item_count_query, filter_list, api_model.model_fields)

            record_count: int = (await session.execute(item_count_query)).scalar()
            if record_count is None:
                record_count = 0
            item_rows: Sequence[Row] = (await session.execute(item_query)).all()

            if item_rows is None:
                return api.MultiResponse[api_model](limit=0, status_code=101)  # ty:ignore[invalid-type-form]

            response_objects = []

            for item_row in item_rows:
                item_record = item_row[0]

                response_dict =  await mapping_function(item_record, field_list, session)
                response_object = return_class(**response_dict)

                response_objects.append(response_object)

            return api.MultiResponse[return_class](  # ty:ignore[invalid-type-form]
                limit=params.limit,
                offset=params.offset,
                number_of_page_results=len(item_rows),
                number_of_total_results=record_count,
                status_code=1,
                results=response_objects)

    async def _get_character_data(self, db_record: db.Character, field_list: list[str], session: AsyncSession) -> dict:  # noqa: C901, PLR0912
        response_dict = {}

        direct_copy_fields = [*self._base_entity_fields, 'gender', 'real_name']

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        response_dict['birth'] = self._birth_date_format(db_record.birth) if db_record.birth is not None else None
        await session.refresh(db_record, ['origin', 'publisher'])
        response_dict['origin'] = db_record.origin.summary if db_record.origin is not None else None
        response_dict['publisher'] = db_record.publisher.summary if db_record.publisher is not None else None

        if 'first_appeared_in_issue' in field_list:
            query = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()
            response_dict['first_appeared_in_issue'] = None if query is None else query._asdict()

        if 'issue_credits' in field_list or 'count_of_issue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id))).all()
            response_dict['count_of_issue_appearances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'issues_died_in' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.CharacterIssueDied).where(db.CharacterIssueDied.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.CharacterIssueDied.issue_id))).all()
            response_dict['issues_died_in'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'powers' in field_list:
            query: list = (await session.execute(
                select(db.Power.id, db.Power.name, db.Power.api_detail_url) \
                    .select_from(db.CharacterPower).where(db.CharacterPower.character_id == db_record.id) \
                    .join(db.Power, db.Power.id == db.CharacterPower.power_id))).all()
            response_dict['powers'] = self._rows_to_list(query, api.BasicLinkedEntity)

        if 'character_enemies' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterEnemy).where(db.CharacterEnemy.character_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterEnemy.enemy_id))).all()
            response_dict['character_enemies'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'character_friends' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterFriend).where(db.CharacterFriend.character_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterFriend.friend_id))).all()
            response_dict['character_friends'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'creators' in field_list:
            query: list = (await session.execute(
                select(db.Person.id, db.Person.name, db.Person.api_detail_url, db.Person.site_detail_url) \
                    .select_from(db.CharacterCreator).where(db.CharacterCreator.character_id == db_record.id) \
                    .join(db.Person, db.Person.id == db.CharacterCreator.person_id))).all()
            response_dict['creators'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueCharacter.issue_id).subquery()
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_enemies' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterEnemy).where(db.TeamCharacterEnemy.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterEnemy.team_id))).all()
            response_dict['team_enemies'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_friends' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterFriend).where(db.TeamCharacterFriend.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterFriend.team_id))).all()
            response_dict['team_friends'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'teams' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterMember).where(db.TeamCharacterMember.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterMember.team_id))).all()
            response_dict['teams'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def character(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailCharacter]:
        return await self._generate_single_response(int(item_id), params, db.Character, api.DetailCharacter,
                self._get_character_data)  # ty:ignore[invalid-return-type]

    async def characters(self, params: api.FilterParams) -> api.MultiResponse[api.BaseCharacter]:
        return await self._generate_multi_response(params, db.Character, api.BaseCharacter,
                self._get_character_data)  # ty:ignore[invalid-return-type]

    async def _get_concept_data(self, db_record: db.Concept, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'first_appeared_in_issue' in field_list or 'start_year' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }
                response_dict['start_year'] = str(query.cover_date.year)

        if 'issue_credits' in field_list or 'count_of_isssue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id))).all()
            response_dict['count_of_isssue_appearances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def concept(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailConcept]:
        return await self._generate_single_response(int(item_id), params, db.Concept, api.DetailConcept,
                self._get_concept_data)  # ty:ignore[invalid-return-type]

    async def concepts(self, params: api.FilterParams) -> api.MultiResponse[api.BaseConcept]:
        return await self._generate_multi_response(params, db.Concept, api.BaseConcept,
                self._get_concept_data)  # ty:ignore[invalid-return-type]

    async def _get_issue_data(self, db_record: db.Issue, field_list: list[str], session: AsyncSession) -> dict:  # noqa: C901
        direct_copy_fields = [*self._base_entity_fields, 'issue_number']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        response_dict['cover_date'] = None if db_record.cover_date is None else self._date_format(db_record.cover_date)
        response_dict['store_date'] = None if db_record.cover_date is None else self._date_format(db_record.cover_date)

        if 'associated_images' in field_list:
            query: list = (await session.execute(
                select(db.IssueAssociatedImage.id, db.IssueAssociatedImage.caption,
                       db.IssueAssociatedImage.original_url, db.IssueAssociatedImage.image_tags) \
                    .where(db.IssueAssociatedImage.issue_id == db_record.id))).all()

            response_dict['associated_images'] = self._rows_to_list(query, api.AssociatedImages)

        if 'volume' in field_list and db_record.volume_id is not None:
            query: Row = (await session.execute(
                select(db.Volume.id, db.Volume.api_detail_url, db.Volume.name, db.Volume.site_detail_url) \
                    .where(db.Volume.id == db_record.volume_id))).first()

            response_dict['volume'] = query._asdict()

        if 'character_credits' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.issue_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.IssueCharacter.character_id))).all()
            response_dict['character_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'character_died_in' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterIssueDied).where(db.CharacterIssueDied.issue_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterIssueDied.character_id))).all()
            response_dict['character_died_in'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'concept_credits' in field_list:
            query: list = (await session.execute(
                select(db.Concept.id, db.Concept.name, db.Concept.api_detail_url, db.Concept.site_detail_url) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.issue_id == db_record.id) \
                    .join(db.Concept, db.Concept.id == db.IssueConcept.concept_id))).all()
            response_dict['concept_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'location_credits' in field_list:
            query: list = (await session.execute(
                select(db.Location.id, db.Location.name, db.Location.api_detail_url, db.Location.site_detail_url) \
                    .select_from(db.IssueLocation).where(db.IssueLocation.issue_id == db_record.id) \
                    .join(db.Location, db.Location.id == db.IssueLocation.location_id))).all()
            response_dict['location_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'object_credits' in field_list:
            query: list = (await session.execute(
                select(db.Object.id, db.Object.name, db.Object.api_detail_url, db.Object.site_detail_url) \
                    .select_from(db.IssueObject).where(db.IssueObject.issue_id == db_record.id) \
                    .join(db.Object, db.Object.id == db.IssueObject.object_id))).all()
            response_dict['object_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'person_credits' in field_list:
            query: list = (await session.execute(
                select(db.Person.id, db.Person.name, db.Person.api_detail_url, db.Person.site_detail_url, db.IssueCredit.role) \
                    .select_from(db.IssueCredit).where(db.IssueCredit.issue_id == db_record.id) \
                    .join(db.Person, db.Person.id == db.IssueCredit.person_id))).all()
            response_dict['person_credits'] = self._rows_to_list(query, api.PersonCredits)

        if 'story_arc_credits' in field_list:
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .select_from(db.StoryArcIssue).where(db.StoryArcIssue.issue_id == db_record.id) \
                    .join(db.StoryArc, db.StoryArc.id == db.StoryArcIssue.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_credits' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.IssueTeam).where(db.IssueTeam.issue_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.IssueTeam.team_id))).all()
            response_dict['team_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_disbanded_in' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamIssueDisbanded).where(db.TeamIssueDisbanded.issue_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamIssueDisbanded.team_id))).all()
            response_dict['team_disbanded_in'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def issue(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailIssue]:
        return await self._generate_single_response(int(item_id), params, db.Issue, api.DetailIssue,
                self._get_issue_data)  # ty:ignore[invalid-return-type]

    async def issues(self, params: api.FilterParams) -> api.MultiResponse[api.BaseIssue]:
        return await self._generate_multi_response(params, db.Issue, api.BaseIssue,
                self._get_issue_data)  # ty:ignore[invalid-return-type]

    async def _get_location_data(self, db_record: db.Location, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'first_appeared_in_issue' in field_list or 'start_year' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueLocation).where(db.IssueLocation.location_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueLocation.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }
                response_dict['start_year'] = str(query.cover_date.year)

        if 'issue_credits' in field_list or 'count_of_issue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueLocation).where(db.IssueLocation.location_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueLocation.issue_id))).all()
            response_dict['count_of_issue_appearances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueLocation).where(db.IssueLocation.location_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueLocation.issue_id).subquery()
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueLocation).where(db.IssueLocation.location_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueLocation.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def location(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailLocation]:
        return await self._generate_single_response(int(item_id), params, db.Location, api.DetailLocation,
                self._get_location_data)  # ty:ignore[invalid-return-type]

    async def locations(self, params: api.FilterParams) -> api.MultiResponse[api.BaseLocation]:
        return await self._generate_multi_response(params, db.Location, api.BaseLocation,
                self._get_location_data)  # ty:ignore[invalid-return-type]

    async def _get_object_data(self, db_record: db.Object, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'first_appeared_in_issue' in field_list or 'start_year' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueObject).where(db.IssueObject.object_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueObject.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }
                response_dict['start_year'] = str(query.cover_date.year)

        if 'issue_credits' in field_list or 'count_of_issue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueObject).where(db.IssueObject.object_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueObject.issue_id))).all()
            response_dict['count_of_issue_appearances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueObject).where(db.IssueObject.object_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueObject.issue_id).subquery()
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueObject).where(db.IssueObject.object_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueObject.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def object(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailObject]:
        return await self._generate_single_response(int(item_id), params, db.Object, api.DetailObject,
                self._get_object_data)  # ty:ignore[invalid-return-type]

    async def objects(self, params: api.FilterParams) -> api.MultiResponse[api.BaseObject]:
        return await self._generate_multi_response(params, db.Object, api.BaseObject,
                self._get_object_data)  # ty:ignore[invalid-return-type]

    async def _get_origin_data(self, db_record: db.Origin, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = ['id', 'api_detail_url', 'name', 'site_detail_url']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        if 'first_appeared_in_issue' in field_list or 'start_year' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueObject).where(db.IssueObject.object_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueObject.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }
                response_dict['start_year'] = str(query.cover_date.year)

        if 'characters' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .where(db.Character.origin_id == db_record.id))).all()
            response_dict['characters'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def origin(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailOrigin]:
        return await self._generate_single_response(int(item_id), params, db.Origin, api.DetailOrigin,
                self._get_origin_data)  # ty:ignore[invalid-return-type]

    async def origins(self, params: api.FilterParams) -> api.MultiResponse[api.BaseOrigin]:
        return await self._generate_multi_response(params, db.Origin, api.BaseOrigin,
                self._get_origin_data)  # ty:ignore[invalid-return-type]

    async def _get_person_data(self, db_record: db.Person, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'country', 'email', 'gender', 'hometown', 'website']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        response_dict['birth'] = None if db_record.birth is None else self._datetime_format(db_record.birth)
        response_dict['death'] = None if db_record.death is None else db_record.death

        if 'issues' in field_list or 'count_of_isssue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueCredit).where(db.IssueCredit.person_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCredit.issue_id))).all()
            response_dict['count_of_isssue_appearances'] = len(query)
            response_dict['issues'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'created_characters' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterCreator).where(db.CharacterCreator.person_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterCreator.character_id))).all()
            response_dict['created_characters'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueCredit).where(db.IssueCredit.person_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueCredit.issue_id).subquery()
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueCredit).where(db.IssueCredit.person_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCredit.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def person(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPerson]:
        return await self._generate_single_response(int(item_id), params, db.Person, api.DetailPerson,
                self._get_person_data)  # ty:ignore[invalid-return-type]

    async def people(self, params: api.FilterParams) -> api.MultiResponse[api.BasePerson]:
        return await self._generate_multi_response(params, db.Person, api.BasePerson,
                self._get_person_data)  # ty:ignore[invalid-return-type]

    async def _get_power_data(self, db_record: db.Power, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [field for field in self._base_entity_fields if field not in ['deck', 'image']]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'characters' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterPower).where(db.CharacterPower.power_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterPower.character_id))).all()
            response_dict['characters'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def power(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPower]:
        return await self._generate_single_response(int(item_id), params, db.Power, api.DetailPower,
                self._get_power_data)  # ty:ignore[invalid-return-type]

    async def powers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePower]:
        return await self._generate_multi_response(params, db.Power, api.BasePower,
                self._get_power_data)  # ty:ignore[invalid-return-type]

    async def _get_publisher_data(self, db_record: db.Publisher, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'location_address', 'location_city', 'location_state']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'characters' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .where(db.Character.publisher_id == db_record.id))).all()
            response_dict['characters'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'teams' in field_list:
            query: list = (await session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .where(db.Team.publisher_id == db_record.id))).all()
            response_dict['teams'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arcs' in field_list:
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .where(db.StoryArc.publisher_id == db_record.id))).all()
            response_dict['story_arcs'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volumes' in field_list:
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .where(db.Volume.publisher_id == db_record.id))).all()
            response_dict['volumes'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def publisher(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPublisher]:
        return await self._generate_single_response(int(item_id), params, db.Publisher, api.DetailPublisher,
                self._get_publisher_data)  # ty:ignore[invalid-return-type]

    async def publishers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePublisher]:
        return await self._generate_multi_response(params, db.Publisher, api.BasePublisher,
                self._get_publisher_data)  # ty:ignore[invalid-return-type]

    @cached(cache=TTLCache(ttl=360, maxsize=128), key=lambda _, params:
        hashkey(params.field_list, params.limit, params.offset, params.sort, params.filter, params.page, params.resources, params.query))
    async def search(self, params: api.SearchParams) -> api.SearchResponse:
        if params.query is None or params.query == "":
            raise ObjectNotFoundError

        response_objects = []

        if params.field_list is None or params.field_list == []:
            character_model = api.BaseCharacter
            concept_model = api.BaseConcept
            issue_model = api.BaseIssue
            location_model = api.BaseLocation
            object_model = api.BaseObject
            origin_model = api.BaseOrigin
            person_model = api.BasePerson
            publisher_model = api.BasePublisher
            storyarc_model = api.BaseStoryArc
            team_model = api.BaseTeam
            volume_model = api.BaseVolume
            entity_model = api.BaseEntity
            return_class = api.SearchResponse
        else:
            field_list = params.field_list.split(',')
            character_model = api.filtered_model(api.BaseCharacter, field_list)
            concept_model = api.filtered_model(api.BaseConcept, field_list)
            issue_model = api.filtered_model(api.BaseIssue, field_list)
            location_model = api.filtered_model(api.BaseLocation, field_list)
            object_model = api.filtered_model(api.BaseObject, field_list)
            origin_model = api.filtered_model(api.BaseOrigin, field_list)
            person_model = api.filtered_model(api.BasePerson, field_list)
            publisher_model = api.filtered_model(api.BasePublisher, field_list)
            storyarc_model = api.filtered_model(api.BaseStoryArc, field_list)
            team_model = api.filtered_model(api.BaseTeam, field_list)
            volume_model = api.filtered_model(api.BaseVolume, field_list)
            entity_model = api.filtered_model(api.BaseEntity, field_list)
            filtered_classes = character_model | concept_model | issue_model | location_model | object_model | \
                origin_model | person_model | publisher_model | storyarc_model |  team_model | volume_model | entity_model
            return_class = api.MultiResponse[filtered_classes]  # ty:ignore[invalid-type-form]

        # Trunk doesn't support video, if it's the only parameter, then bow out
        if params.resources is None or params.resources == "":
            resources: list[str] = ["character", "concept", "origin", "object", "location", "issue", "story_arc",
                                    "volume", "publisher", "person", "team"]
        elif params.resources == "video":
            raise ObjectNotFoundError
        else:
            resources: list[str] = [resource for resource in params.resources.split(',') if resource != 'video']

        resource_map: dict[str, tuple[str, type[db.FTSBase], type[db.BaseTable], type[api.BaseModelExtra], Callable]] = {
            "character": ("cv_character_fts", db.CharacterFTS, db.Character, character_model, self._get_character_data),
            "concept": ("cv_concept_fts", db.ConceptFTS, db.Concept, concept_model, self._get_concept_data),
            "origin": ("cv_origin_fts", db.OriginFTS, db.Origin, origin_model, self._get_origin_data),
            "object": ("cv_object_fts", db.ObjectFTS, db.Object, object_model, self._get_object_data),
            "location": ("cv_location_fts", db.LocationFTS, db.Location, location_model, self._get_location_data),
            "issue": ("cv_issue_fts", db.IssueFTS, db.Issue, issue_model, self._get_issue_data),
            "story_arc": ("cv_storyarc_fts", db.StoryArcFTS, db.StoryArc, storyarc_model, self._get_story_arc_data),
            "volume": ("cv_volume_fts", db.VolumeFTS, db.Volume, volume_model, self._get_volume_data),
            "publisher": ("cv_publisher_fts", db.PublisherFTS, db.Publisher, publisher_model, self._get_publisher_data),
            "person": ("cv_person_fts", db.PersonFTS, db.Person, person_model, self._get_person_data),
            "team": ("cv_team_fts", db.TeamFTS, db.Team, team_model, self._get_team_data),
            #"video": ("cv_video_fts", ???, entity_model),  # noqa: ERA001
        }

        def clean_token(token: str) -> str:
            dialect_string = String().literal_processor(dialect=self.db_engine.dialect)(value=token)
            if re.search(r"[^a-zA-Z0-9]",dialect_string[1:-1]) is not None:
                dialect_string = "'\"" + dialect_string[1:-1].replace('"', '') + "\"'"
            return dialect_string

        cleaned_query_tokens = [clean_token(token) for token in params.query.split(' ') if token != '']

        # Create an empty selection to load unions against
        selection_set = select(
            literal_column("0", Integer).label('rowid'),
            literal_column("'resource'", String).label('resource_type'),
            literal_column("-0.0", Float).label('rank'))

        selection_set = []

        for resource in resources:
            fts_table, fts_orm, *_ = resource_map[resource]
            resource_query = select(fts_orm.rowid, literal_column(f"'{resource}'", String).label('resource_type'), text('rank'))
            query_clauses = [text(f"{fts_table} MATCH {token}") for token in cleaned_query_tokens]
            resource_query = resource_query.where(or_(*query_clauses))

            selection_set.append(resource_query)

        union_query = selection_set[0] if len(selection_set) == 1 else selection_set[0].union_all(*selection_set[1:])

        count_query = select(func.count(text('rowid'))).select_from(union_query.subquery())
        data_query = union_query.order_by(text('rank')).offset(params.offset).limit(params.limit)

        async with self.session() as session:
            item_count: int = (await session.execute(count_query)).scalar()
            if item_count is None:
                item_count = 0
            data: Sequence[Row] = (await session.execute(data_query)).all()

            if data is None:
                    return api.SearchResponse(limit=0, status_code=101)

            for result in data:
                resource_type = result.resource_type
                _, _, resource_db_table, resource_api_model, mapping_function = resource_map[resource_type]
                item_query = select(resource_db_table).where(resource_db_table.id == result.rowid)
                item_result = (await session.execute(item_query)).first()

                if item_result is None:
                    logger.error(f'FTS returned a result that could not be found in the data {resource_type}:{result.rowid}')
                    continue

                item_record = item_result[0]

                if params.field_list is None or params.field_list == []:
                    field_list = resource_api_model.model_fields.keys()

                response_dict = await mapping_function(item_record, field_list, session)
                response_object = resource_api_model(**response_dict)

                response_objects.append(response_object)

            return return_class(
                limit=params.limit,
                offset=params.offset,
                number_of_page_results=len(response_objects),
                number_of_total_results=item_count,
                status_code=1,
                results=response_objects)

    async def _get_story_arc_data(self, db_record: db.StoryArc, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        await session.refresh(db_record, ['publisher'])
        response_dict['publisher'] = db_record.publisher.summary if db_record.publisher is not None else None

        if 'first_appeared_in_issue' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.StoryArcIssue).where(db.StoryArcIssue.story_arc_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.StoryArcIssue.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }

        if 'issues' in field_list or 'count_of_isssue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.StoryArcIssue).where(db.StoryArcIssue.story_arc_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.StoryArcIssue.issue_id))).all()
            response_dict['count_of_isssue_appearances'] = len(query)
            response_dict['issues'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def story_arc(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailStoryArc]:
        return await self._generate_single_response(int(item_id), params, db.StoryArc, api.DetailStoryArc,
                self._get_story_arc_data)  # ty:ignore[invalid-return-type]

    async def story_arcs(self, params: api.FilterParams) -> api.MultiResponse[api.BaseStoryArc]:
        return await self._generate_multi_response(params, db.StoryArc, api.BaseStoryArc,
                self._get_story_arc_data)  # ty:ignore[invalid-return-type]

    async def _get_team_data(self, db_record: db.Team, field_list: list[str], session: AsyncSession) -> dict:  # noqa: C901
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        await session.refresh(db_record, ['publisher'])
        response_dict['publisher'] = db_record.publisher.summary if db_record.publisher is not None else None

        if 'first_appeared_in_issue' in field_list:
            query: Row = (await session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueTeam).where(db.IssueTeam.team_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueTeam.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date)))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }

        if 'issue_credits' in field_list or 'count_of_isssue_appearances' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueTeam).where(db.IssueTeam.team_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueTeam.issue_id))).all()
            response_dict['count_of_isssue_appearances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'character_enemies' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.TeamCharacterEnemy).where(db.TeamCharacterEnemy.team_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.TeamCharacterEnemy.character_id))).all()
            response_dict['team_enemies'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'character_friends' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.TeamCharacterFriend).where(db.TeamCharacterFriend.team_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.TeamCharacterFriend.character_id))).all()
            response_dict['team_friends'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'characters' in field_list or 'count_of_team_members' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.TeamCharacterMember).where(db.TeamCharacterMember.team_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.TeamCharacterMember.character_id))).all()
            response_dict['teams'] = self._rows_to_list(query, api.SiteLinkedEntity)
            response_dict['count_of_team_members'] = len(query)

        if 'disbanded_in_issues' in field_list or 'isssues_disbanded_in' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.TeamIssueDisbanded).where(db.TeamIssueDisbanded.team_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.TeamIssueDisbanded.issue_id))).all()
            data = self._rows_to_list(query, api.SiteLinkedEntity)
            response_dict['disbanded_in_issues'] = data
            response_dict['isssues_disbanded_in'] = data

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueTeam).where(db.IssueTeam.team_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueTeam.issue_id).subquery()
            query: list = (await session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id))).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            subq = select(db.Issue.volume_id).distinct() \
                    .select_from(db.IssueTeam).where(db.IssueTeam.team_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueTeam.issue_id).subquery()
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .join(subq, db.Volume.id == subq.c.volume_id))).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def team(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailTeam]:
        return await self._generate_single_response(int(item_id), params, db.Team, api.DetailTeam,
                self._get_team_data)  # ty:ignore[invalid-return-type]

    async def teams(self, params: api.FilterParams) -> api.MultiResponse[api.BaseTeam]:
        return await self._generate_multi_response(params, db.Team, api.BaseTeam,
                self._get_team_data)  # ty:ignore[invalid-return-type]

    async def _get_volume_data(self, db_record: db.Volume, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'start_year']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        await session.refresh(db_record, ['publisher'])
        response_dict['publisher'] = db_record.publisher.summary if db_record.publisher is not None else None

        if 'issues' in field_list or 'count_of_issues' in field_list or \
             'first_issue' in field_list or 'last_issue' in field_list:
            query: list = (await session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url, db.Issue.issue_number) \
                    .where(db.Issue.volume_id == db_record.id) \
                    .order_by(asc(db.Issue.cover_date)))).all()
            response_dict['count_of_issues'] = len(query)
            response_dict['issues'] = self._rows_to_list(query, api.SiteLinkedIssue)
            if len(query) > 0:
                response_dict['first_issue'] = query[0]._asdict()
                response_dict['last_issue'] = query[-1]._asdict()

        if 'characters' in field_list:
            query: list = (await session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url,
                         cast(func.count(db.Issue.id), String).label('count')) \
                    .join(db.IssueCharacter, db.Character.id == db.IssueCharacter.character_id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id) \
                    .where(db.Issue.volume_id == db_record.id) \
                    .group_by(db.Character.id).order_by(text('count DESC')))).all()
            response_dict['characters'] = self._rows_to_list(query, api.CountedSiteLinkedEntity)

        if 'locations' in field_list:
            query: list = (await session.execute(
                select(db.Location.id, db.Location.name, db.Location.api_detail_url, db.Location.site_detail_url,
                         cast(func.count(db.Issue.id), String).label('count')) \
                    .join(db.IssueLocation, db.Location.id == db.IssueLocation.location_id) \
                    .join(db.Issue, db.Issue.id == db.IssueLocation.issue_id) \
                    .where(db.Issue.volume_id == db_record.id) \
                    .group_by(db.Location.id).order_by(text('count DESC')))).all()
            response_dict['locations'] = self._rows_to_list(query, api.CountedSiteLinkedEntity)

        # This is actually broken in ComicVine - they return the characters again under the objects element
        # So technically this is a bug?
        if 'objects' in field_list:
            query: list = (await session.execute(
                select(db.Object.id, db.Object.name, db.Object.api_detail_url, db.Object.site_detail_url,
                         cast(func.count(db.Issue.id), String).label('count')) \
                    .join(db.IssueObject, db.Object.id == db.IssueObject.object_id) \
                    .join(db.Issue, db.Issue.id == db.IssueObject.issue_id) \
                    .where(db.Issue.volume_id == db_record.id) \
                    .group_by(db.Object.id).order_by(text('count DESC')))).all()
            response_dict['objects'] = self._rows_to_list(query, api.CountedSiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def volume(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailVolume]:
        return await self._generate_single_response(int(item_id), params, db.Volume, api.DetailVolume,
                self._get_volume_data)  # ty:ignore[invalid-return-type]

    async def volumes(self, params: api.FilterParams) -> api.MultiResponse[api.BaseVolume]:
        return await self._generate_multi_response(params, db.Volume, api.BaseVolume,
                self._get_volume_data)  # ty:ignore[invalid-return-type]

    ## The trunk only supports comic data
    async def episode(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def episodes(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def movie(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def movies(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def series(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def series_list(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def video(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def videos(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def video_type(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def video_types(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def video_category(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def video_categories(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    async def health_check(self) -> dict[str, str]:
        """Check health of the database by validating connectivity.

        Returns
        -------
        dict[str, str]
            Dictionary with 'status' set to 'ok' and 'trunk' set to 'staticdb'.

        Raises
        ------
        RuntimeError
            If database connection cannot be established.

        """
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            message = f"StaticDB health check failed: {exc}"
            raise RuntimeError(message) from exc
        return {"status": "ok", "trunk": "staticdb"}
