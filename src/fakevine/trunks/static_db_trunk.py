# ruff: noqa: TRY003, EM101
import logging
import os
from typing import TYPE_CHECKING

from loguru import logger
from sqlalchemy import Engine, Row, create_engine, select
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
    def __init__(self, database_path: Path):
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

    def character(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailCharacter]:
        character_query: Row = self.session.execute(select(db.Character).where(db.Character.id == int(item_id))).first()

        if character_query is None:
            return api.SingleResponse[api.DetailCharacter](limit=0, status_code=101)

        character_record: db.Character = character_query[0]

        api_character = api.DetailCharacter(
                id = character_record.id,
                api_detail_url = character_record.api_detail_url,
                name = character_record.name,
                site_detail_url = character_record.api_detail_url,
                aliases = character_record.aliases,
                date_added = self._datetime_format(character_record.date_added),
                date_last_updated = self._datetime_format(character_record.date_last_updated),
                deck = character_record.deck,
                description = character_record.description,
                image = character_record.image,
                birth = self._datetime_format(character_record.birth) if character_record.birth is not None else None,
                count_of_issue_apperances = 0,
                first_appeared_in_issue = None,
                gender = character_record.gender,
                origin = None,
                publisher = None,
                real_name = character_record.real_name,
            )

        #issue_credits

        #api_character.count_of_issue_apperances = self.session.execute(
        #    select(func.count("*")).where(db.IssueCharacter.character_id == item_id)).first()[0]
        print(character_record.publisher)

        print(character_record.origin)

        return api.SingleResponse[api.DetailCharacter](
            limit=1,
            number_of_page_results=1,
            number_of_total_results=1,
            status_code=1,
            results=api_character)

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
    def episode(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def episodes(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def movie(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def movies(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def series(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def series_list(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def video(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def videos(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def video_type(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def video_types(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def video_category(self, item_id: int, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")

    def video_categories(self, params: api.CommonParams) -> api.CVResponse:
        raise NotImplementedError("Route not implemented by trunk")