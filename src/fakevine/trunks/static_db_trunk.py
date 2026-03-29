# ruff: noqa: EM101, D102
import logging
import os
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger
from pydantic.fields import FieldInfo
from sqlalchemy import ColumnElement, Engine, Result, Row, Select, Sequence, asc, create_engine, func, select
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Query, Session
from sqlalchemy.sql.base import ReadOnlyColumnCollection
from sqlalchemy.sql.elements import KeyedColumnElement
from sqlalchemy.sql.expression import text

from fakevine.models import cvapimodels as api
from fakevine.models import cvdbmodels as db
from fakevine.trunks.comic_trunk import ComicTrunk

if TYPE_CHECKING:
    import datetime
    from pathlib import Path


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
        self.session = Session(self.db_engine)

        try:
            with self.db_engine.connect() as conn:
                _ = conn.execute(text("SELECT 'hello engine'"))
        except DatabaseError:
            logger.exception("Input database is not a valid SQL database")
            raise


        if os.environ.get("STATICDB_LOG_QUERIES", "False").lower() == "true":
            logging.basicConfig()
            logging.getLogger("sqlalchemy.engine").setLevel(logging.INFO)

        # TODO@falo2k: Validate database schema

        self._base_entity_fields = ['id', 'api_detail_url', 'name', 'aliases', 'deck', 'description', 'image', 'site_detail_url']

    def _datetime_format(self, date_time: datetime.datetime) -> str:
        return date_time.strftime('%Y-%m-%d %H:%M:%S')

    def _rows_to_list(self, rows: Sequence[Row], container_class: type[api.BasicLinkedEntity]) -> list:
        def inner_func(row: Row) -> api.BasicLinkedEntity:
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
            elif 'str' in str(field_info.annotation):
                query = query.where(columns[filter_name].contains(filter_value))
            elif 'int' in str(field_info.annotation):
                query = query.where(columns[filter_name] == filter_value)
            else:
                error_msg = f'Do not know how to handle filter for {filter_name} with type {field_info.annotation}.  Ignoring.'
                logger.error(error_msg)

        return query

    def _generate_single_response(self, item_id: int, params: api.CommonParams, db_table: type[db.BaseTable],
                                    api_model: type[api.BaseEntity], mapping_function: Callable) -> api.SingleResponse[api.BaseModelExtra]:
        item_query: Result[db.Character] = self.session.execute(select(db_table).where(db_table.id == int(item_id)))
        item_row: Row = item_query.first()

        if item_row is None:
            return api.SingleResponse[api_model](limit=0, status_code=101)  # ty:ignore[invalid-type-form]

        if params.field_list is None or params.field_list == "":
            field_list = api_model.model_fields.keys()
            return_class = api_model
        else:
            field_list = params.field_list.split(',')
            return_class = api.filtered_model(api_model, field_list)

        item_record: db.Character = item_row[0]

        response_dict =  mapping_function(item_record, field_list)

        response_object = return_class(**response_dict)

        return api.SingleResponse[return_class](  # ty:ignore[invalid-type-form]
            limit=1,
            number_of_page_results=1,
            number_of_total_results=1,
            status_code=1,
            results=response_object)

    def _generate_multi_response(self, params: api.FilterParams, db_table: type[db.BaseTable],
                                    api_model: type[api.BaseEntity], mapping_function: Callable) -> api.MultiResponse[api.BaseModelExtra]:
        sort_params = ('id', 'asc') if params.sort is None or params.sort == "" else tuple(params.sort.split(':'))
        sort_string = f'{sort_params[0]} {sort_params[1].upper()}'

        filter_list = [] if params.filter is None else params.filter.split(',')

        item_count_query: Query = func.count(db_table.id)
        item_query: Query = select(db_table) \
            .order_by(text(sort_string)).offset(params.offset).limit(params.limit)

        if params.field_list is None or params.field_list == []:
            field_list = api_model.model_fields.keys()
            return_class = api_model
        else:
            field_list = params.field_list.split(',')
            return_class = api.filtered_model(api_model, field_list)

        item_query = self._build_filtered_query(item_query, filter_list, return_class.model_fields)

        record_count: int = self.session.execute(item_count_query).scalar()
        item_rows: Sequence[Row] = self.session.execute(item_query).all()

        if item_rows is None:
            return api.MultiResponse[api_model](limit=0, status_code=101)  # ty:ignore[invalid-type-form]

        response_objects = []

        for item_row in item_rows:
            item_record = item_row[0]

            response_dict =  mapping_function(item_record, field_list)
            response_object = return_class(**response_dict)

            response_objects.append(response_object)

        return api.MultiResponse[return_class](  # ty:ignore[invalid-type-form]
            limit=params.limit,
            offset=params.offset,
            number_of_page_results=len(item_rows),
            number_of_total_results=record_count,
            status_code=1,
            results=response_objects)

    def _get_character_data(self, db_record: db.Character, field_list: list[str]) -> dict:
        response_dict = {}

        direct_copy_fields = [*self._base_entity_fields, 'gender', 'real_name']

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)
        response_dict['birth'] = self._datetime_format(db_record.birth) if db_record.birth is not None else None
        response_dict['origin'] = db_record.origin.summary if db_record.origin is not None else None
        response_dict['publisher'] = db_record.publisher.summary if db_record.publisher is not None else None

        if 'first_appeared_in_issue' in field_list:
            query = self.session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date))).first()
            response_dict['first_appeared_in_issue'] = None if query is None else query._asdict()

        if 'issue_credits' in field_list or 'count_of_appearances' in field_list:
            query: list = self.session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id)).all()
            response_dict['count_of_issue_apperances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'issues_died_in' in field_list:
            query: list = self.session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.CharacterIssueDied).where(db.CharacterIssueDied.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.CharacterIssueDied.issue_id)).all()
            response_dict['issues_died_in'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'powers' in field_list:
            query: list = self.session.execute(
                select(db.Power.id, db.Power.name, db.Power.api_detail_url) \
                    .select_from(db.CharacterPower).where(db.CharacterPower.character_id == db_record.id) \
                    .join(db.Power, db.Power.id == db.CharacterPower.power_id)).all()
            response_dict['powers'] = self._rows_to_list(query, api.BasicLinkedEntity)

        if 'character_enemies' in field_list:
            query: list = self.session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterEnemy).where(db.CharacterEnemy.character_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterEnemy.enemy_id)).all()
            response_dict['character_enemies'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'character_friends' in field_list:
            query: list = self.session.execute(
                select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
                    .select_from(db.CharacterFriend).where(db.CharacterFriend.character_id == db_record.id) \
                    .join(db.Character, db.Character.id == db.CharacterFriend.friend_id)).all()
            response_dict['character_friends'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'creators' in field_list:
            query: list = self.session.execute(
                select(db.Person.id, db.Person.name, db.Person.api_detail_url, db.Person.site_detail_url) \
                    .select_from(db.CharacterCreator).where(db.CharacterCreator.character_id == db_record.id) \
                    .join(db.Person, db.Person.id == db.CharacterCreator.person_id)).all()
            response_dict['creators'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'story_arc_credits' in field_list:
            subq = select(db.StoryArcIssue.story_arc_id).distinct() \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueCharacter.issue_id).subquery()
            query: list = self.session.execute(
                select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
                    .join(subq, db.StoryArc.id == subq.c.story_arc_id)).all()
            response_dict['story_arc_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            query: list = self.session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id) \
                    .join(db.Volume, db.Issue.volume_id == db.Volume.id)).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_enemies' in field_list:
            query: list = self.session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterEnemy).where(db.TeamCharacterEnemy.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterEnemy.team_id)).all()
            response_dict['team_enemies'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'team_friends' in field_list:
            query: list = self.session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterFriend).where(db.TeamCharacterFriend.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterFriend.team_id)).all()
            response_dict['team_friends'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'teams' in field_list:
            query: list = self.session.execute(
                select(db.Team.id, db.Team.name, db.Team.api_detail_url, db.Team.site_detail_url) \
                    .select_from(db.TeamCharacterMember).where(db.TeamCharacterMember.character_id == db_record.id) \
                    .join(db.Team, db.Team.id == db.TeamCharacterMember.team_id)).all()
            response_dict['teams'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    def character(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailCharacter]:
        return self._generate_single_response(int(item_id), params, db.Character, api.DetailCharacter,
                self._get_character_data)  # ty:ignore[invalid-return-type]

    def characters(self, params: api.FilterParams) -> api.MultiResponse[api.BaseCharacter]:
        return self._generate_multi_response(params, db.Character, api.BaseCharacter,
                self._get_character_data)  # ty:ignore[invalid-return-type]

    def _get_concept_data(self, db_record: db.Concept, field_list: list[str]) -> dict:
        direct_copy_fields = [*self._base_entity_fields]

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'first_appeared_in_issue' in field_list or 'start_year' in field_list:
            query: Row = self.session.execute(
                select(db.Issue.id, db.Issue.issue_number, db.Issue.name, db.Issue.api_detail_url, db.Issue.cover_date) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id) \
                    .where(db.Issue.cover_date.is_not(None)) \
                    .order_by(asc(db.Issue.cover_date))).first()

            if query is not None:
                response_dict['first_appeared_in_issue'] = {
                    'id': query.id,
                    'issue_number': query.issue_number,
                    'name': query.name,
                    'api_detail_url': query.api_detail_url,
                }
                response_dict['start_year'] = str(query.cover_date.year)

        if 'issue_credits' in field_list or 'count_of_appearances' in field_list:
            query: list = self.session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id)).all()
            response_dict['count_of_issue_apperances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        if 'volume_credits' in field_list:
            query: list = self.session.execute(
                select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
                    .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
                    .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id) \
                    .join(db.Volume, db.Issue.volume_id == db.Volume.id)).all()
            response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    def concept(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailConcept]:
        return self._generate_single_response(int(item_id), params, db.Concept, api.DetailConcept,
                self._get_concept_data)  # ty:ignore[invalid-return-type]

    def concepts(self, params: api.FilterParams) -> api.MultiResponse[api.BaseConcept]:
        return self._generate_multi_response(params, db.Concept, api.BaseConcept,
                self._get_concept_data)  # ty:ignore[invalid-return-type]

    def _get_issue_data(self, db_record: db.Issue, field_list: list[str]) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'associated_images', 'issue_number', 'cover_date', 'store_date']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(db_record.date_added)
        response_dict['date_last_updated'] = self._datetime_format(db_record.date_last_updated)

        if 'volume' in field_list and db_record.volume_id is not None:
            query: Row = self.session.execute(
                select(db.Volume.id, db.Volume.api_detail_url, db.Volume.name, db.Volume.site_detail_url) \
                    .where(db.Volume.id == db_record.volume_id)).first()

            response_dict['volume'] = query._asdict()

        # if 'issue_credits' in field_list or 'count_of_appearances' in field_list:
        #     query: list = self.session.execute(
        #         select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
        #             .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
        #             .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id)).all()
        #     response_dict['count_of_issue_apperances'] = len(query)
        #     response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        # if 'volume_credits' in field_list:
        #     query: list = self.session.execute(
        #         select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
        #             .select_from(db.IssueConcept).where(db.IssueConcept.concept_id == db_record.id) \
        #             .join(db.Issue, db.Issue.id == db.IssueConcept.issue_id) \
        #             .join(db.Volume, db.Issue.volume_id == db.Volume.id)).all()
        #     response_dict['volume_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    def issue(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailIssue]:
        raise NotImplementedError("Route not implemented by trunk")

    def issues(self, params: api.FilterParams) -> api.MultiResponse[api.BaseIssue]:
        raise NotImplementedError("Route not implemented by trunk")

    def location(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    def locations(self, params: api.FilterParams) -> api.MultiResponse[api.BaseLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    def object(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailObject]:
        raise NotImplementedError("Route not implemented by trunk")

    def objects(self, params: api.FilterParams) -> api.MultiResponse[api.BaseObject]:
        raise NotImplementedError("Route not implemented by trunk")

    def origin(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    def origins(self, params: api.FilterParams) -> api.MultiResponse[api.BaseOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    def person(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPerson]:
        raise NotImplementedError("Route not implemented by trunk")

    def people(self, params: api.FilterParams) -> api.MultiResponse[api.BasePerson]:
        raise NotImplementedError("Route not implemented by trunk")

    def power(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPower]:
        raise NotImplementedError("Route not implemented by trunk")

    def powers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePower]:
        raise NotImplementedError("Route not implemented by trunk")

    def publisher(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPublisher]:
        raise NotImplementedError("Route not implemented by trunk")

    def publishers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePublisher]:
        raise NotImplementedError("Route not implemented by trunk")

    def search(self, params: api.SearchParams) -> api.SearchResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def story_arc(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    def story_arcs(self, params: api.FilterParams) -> api.MultiResponse[api.BaseStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    def team(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    def teams(self, params: api.FilterParams) -> api.MultiResponse[api.BaseTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    def volume(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailVolume]:
        raise NotImplementedError("Route not implemented by trunk")

    def volumes(self, params: api.FilterParams) -> api.MultiResponse[api.BaseVolume]:
        raise NotImplementedError("Route not implemented by trunk")

    ## The trunk only supports comic data
    def episode(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def episodes(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def movie(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def movies(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def series(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def series_list(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def videos(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_type(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_types(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_category(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_categories(self, params: api.FilterParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")
