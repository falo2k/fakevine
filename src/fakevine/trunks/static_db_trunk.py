# ruff: noqa: EM101, D102
import logging
import os
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import Engine, Result, Row, Sequence, create_engine, select
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session
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

    def _datetime_format(self, date_time: datetime.datetime) -> str:
        return date_time.strftime('%Y-%m-%d %H:%M:%S')

    def _rows_to_list(self, rows: Sequence[Row], container_class: type[api.BasicLinkedEntity]) -> list:
        def inner_func(row: Row) -> api.BasicLinkedEntity:
            return container_class(**row._asdict())

        return list(map(inner_func, rows))

    def character(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailCharacter]:
        character_query: Result[db.Character] = self.session.execute(select(db.Character).where(db.Character.id == int(item_id)))
        character_row: Row = character_query.first()

        if character_row is None:
            return api.SingleResponse[api.DetailCharacter](limit=0, status_code=101)

        if params.field_list is None or params.field_list == []:
            return_class = api.DetailCharacter
        else:
            field_list = params.field_list.split(',')
            return_class = api.filtered_model(api.DetailCharacter, field_list)

        direct_copy_fields = ['id', 'api_detail_url', 'name', 'aliases', 'deck', 'description', 'image', 'gender', 'real_name', 'site_detail_url']
        field_filter: list[str] | None = None if params.field_list is None else params.field_list.split(',')

        character_record: db.Character = character_row[0]

        response_dict = {}

        for copy_field in direct_copy_fields:
            if field_filter is None or copy_field in field_filter:
                response_dict[copy_field] = getattr(character_record, copy_field)

        if field_filter is None or 'date_added' in field_filter:
            response_dict['date_added'] = self._datetime_format(character_record.date_added)
        if field_filter is None or 'date_last_updated' in field_filter:
            response_dict['date_last_updated'] = self._datetime_format(character_record.date_last_updated)
        if field_filter is None or 'birth' in field_filter:
            response_dict['birth'] = self._datetime_format(character_record.birth) if character_record.birth is not None else None
        if field_filter is None or 'origin' in field_filter:
            response_dict['origin'] = character_record.origin.summary if character_record.origin is not None else None
        if field_filter is None or 'publisher' in field_filter:
            response_dict['publisher'] = character_record.publisher.summary if character_record.publisher is not None else None

        if field_filter is None or 'issue_credits' in field_filter or 'count_of_appearances' in field_filter:
            query: list = self.session.execute(
                select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
                    .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == item_id) \
                    .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id)).all()
            response_dict['count_of_issue_apperances'] = len(query)
            response_dict['issue_credits'] = self._rows_to_list(query, api.SiteLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Issue.id, db.Issue.name, db.Issue.api_detail_url, db.Issue.site_detail_url) \
        #         .select_from(db.CharacterIssueDied).where(db.CharacterIssueDied.character_id == item_id) \
        #         .join(db.Issue, db.Issue.id == db.CharacterIssueDied.issue_id)).all()
        # api_character.issues_died_in = self._rows_to_list(query, api.SiteLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Power.id, db.Power.name, db.Power.api_detail_url) \
        #         .select_from(db.CharacterPower).where(db.CharacterPower.character_id == item_id) \
        #         .join(db.Power, db.Power.id == db.CharacterPower.power_id)).all()
        # api_character.powers = self._rows_to_list(query, api.BasicLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
        #         .select_from(db.CharacterEnemy).where(db.CharacterEnemy.character_id == item_id) \
        #         .join(db.Character, db.Character.id == db.CharacterEnemy.enemy_id)).all()
        # api_character.character_enemies = self._rows_to_list(query, api.SiteLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Character.id, db.Character.name, db.Character.api_detail_url, db.Character.site_detail_url) \
        #         .select_from(db.CharacterFriend).where(db.CharacterFriend.character_id == item_id) \
        #         .join(db.Character, db.Character.id == db.CharacterFriend.friend_id)).all()
        # api_character.character_friends = self._rows_to_list(query, api.SiteLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Person.id, db.Person.name, db.Person.api_detail_url, db.Person.site_detail_url) \
        #         .select_from(db.CharacterCreator).where(db.CharacterCreator.character_id == item_id) \
        #         .join(db.Person, db.Person.id == db.CharacterCreator.person_id)).all()
        # api_character.creators = self._rows_to_list(query, api.SiteLinkedEntity)

        # subq = select(db.StoryArcIssue.story_arc_id).distinct() \
        #         .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == item_id) \
        #         .join(db.StoryArcIssue, db.StoryArcIssue.issue_id == db.IssueCharacter.issue_id).subquery()
        # query: list = self.session.execute(
        #     select(db.StoryArc.id, db.StoryArc.name, db.StoryArc.api_detail_url, db.StoryArc.site_detail_url) \
        #         .join(subq, db.StoryArc.id == subq.c.story_arc_id)).all()
        # api_character.story_arc_credits = self._rows_to_list(query, api.SiteLinkedEntity)

        # query: list = self.session.execute(
        #     select(db.Volume.id, db.Volume.name, db.Volume.api_detail_url, db.Volume.site_detail_url) \
        #         .select_from(db.IssueCharacter).where(db.IssueCharacter.character_id == item_id) \
        #         .join(db.Issue, db.Issue.id == db.IssueCharacter.issue_id) \
        #         .join(db.Volume, db.Issue.volume_id == db.Volume.id)).all()
        # api_character.volume_credits = self._rows_to_list(query, api.SiteLinkedEntity)

        # team_enemies = character_record.team_enemies,
        # team_friends = character_record.team_friends,
        # teams = character_record.teams,

        response_object = return_class(**response_dict)


        return api.SingleResponse[return_class](  # ty:ignore[invalid-type-form]
            limit=1,
            number_of_page_results=1,
            number_of_total_results=1,
            status_code=1,
            results=response_object)

    def characters(self, params: api.CommonParams) -> api.MultiResponse[api.BaseCharacter]:
        raise NotImplementedError("Route not implemented by trunk")

    def concept(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailConcept]:
        raise NotImplementedError("Route not implemented by trunk")

    def concepts(self, params: api.CommonParams) -> api.MultiResponse[api.BaseConcept]:
        raise NotImplementedError("Route not implemented by trunk")

    def issue(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailIssue]:
        raise NotImplementedError("Route not implemented by trunk")

    def issues(self, params: api.CommonParams) -> api.MultiResponse[api.BaseIssue]:
        raise NotImplementedError("Route not implemented by trunk")

    def location(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    def locations(self, params: api.CommonParams) -> api.MultiResponse[api.BaseLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    def object(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailObject]:
        raise NotImplementedError("Route not implemented by trunk")

    def objects(self, params: api.CommonParams) -> api.MultiResponse[api.BaseObject]:
        raise NotImplementedError("Route not implemented by trunk")

    def origin(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    def origins(self, params: api.CommonParams) -> api.MultiResponse[api.BaseOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    def person(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPerson]:
        raise NotImplementedError("Route not implemented by trunk")

    def people(self, params: api.CommonParams) -> api.MultiResponse[api.BasePerson]:
        raise NotImplementedError("Route not implemented by trunk")

    def power(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPower]:
        raise NotImplementedError("Route not implemented by trunk")

    def powers(self, params: api.CommonParams) -> api.MultiResponse[api.BasePower]:
        raise NotImplementedError("Route not implemented by trunk")

    def publisher(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPublisher]:
        raise NotImplementedError("Route not implemented by trunk")

    def publishers(self, params: api.CommonParams) -> api.MultiResponse[api.BasePublisher]:
        raise NotImplementedError("Route not implemented by trunk")

    def search(self, params: api.SearchParams) -> api.SearchResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def story_arc(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    def story_arcs(self, params: api.CommonParams) -> api.MultiResponse[api.BaseStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    def team(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    def teams(self, params: api.CommonParams) -> api.MultiResponse[api.BaseTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    def volume(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailVolume]:
        raise NotImplementedError("Route not implemented by trunk")

    def volumes(self, params: api.FilterParams) -> api.MultiResponse[api.BaseVolume]:
        raise NotImplementedError("Route not implemented by trunk")

    ## The trunk only supports comic data
    def episode(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def episodes(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def movie(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def movies(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def series(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def series_list(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def videos(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_type(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_types(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_category(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")

    def video_categories(self, params: api.CommonParams) -> api.MultiResponse[api.BaseModelExtra]:
        raise NotImplementedError("Route not implemented by trunk")
