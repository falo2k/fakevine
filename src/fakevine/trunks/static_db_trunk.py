from pathlib import Path

from loguru import logger
from sqlalchemy import Engine, create_engine
from sqlalchemy.exc import DatabaseError
from sqlalchemy.orm import Session
from sqlalchemy.sql.expression import text

from fakevine.models import cvapimodels, cvdbmodels
from fakevine.trunks.comic_trunk import (
    ComicTrunk,
    UnsupportedResponseError,
)


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

        # TODO@falo2k: Validate database schema

    def character(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailCharacter]:
        raise UnsupportedResponseError

    def characters(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseCharacter]:
        raise UnsupportedResponseError

    def concept(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailConcept]:
        raise UnsupportedResponseError

    def concepts(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseConcept]:
        raise UnsupportedResponseError

    def issue(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailIssue]:
        raise UnsupportedResponseError

    def issues(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseIssue]:
        raise UnsupportedResponseError

    def location(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailLocation]:
        raise UnsupportedResponseError

    def locations(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseLocation]:
        raise UnsupportedResponseError

    def object(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailObject]:
        raise UnsupportedResponseError

    def objects(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseObject]:
        raise UnsupportedResponseError

    def origin(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailOrigin]:
        raise UnsupportedResponseError

    def origins(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseOrigin]:
        raise UnsupportedResponseError

    def person(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailPerson]:
        raise UnsupportedResponseError

    def people(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BasePerson]:
        raise UnsupportedResponseError

    def power(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailPower]:
        raise UnsupportedResponseError

    def powers(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BasePower]:
        raise UnsupportedResponseError

    def publisher(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailPublisher]:
        raise UnsupportedResponseError

    def publishers(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BasePublisher]:
        raise UnsupportedResponseError

    def search(self, params: cvapimodels.SearchParams) -> cvapimodels.SearchResponse:
        raise UnsupportedResponseError

    def story_arc(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailStoryArc]:
        raise UnsupportedResponseError

    def story_arcs(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseStoryArc]:
        raise UnsupportedResponseError

    def team(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailTeam]:
        raise UnsupportedResponseError

    def teams(self, params: cvapimodels.CommonParams) -> cvapimodels.MultiResponse[cvapimodels.BaseTeam]:
        raise UnsupportedResponseError

    def volume(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.SingleResponse[cvapimodels.DetailVolume]:
        raise UnsupportedResponseError

    def volumes(self, params: cvapimodels.FilterParams) -> cvapimodels.MultiResponse[cvapimodels.BaseVolume]:
        raise UnsupportedResponseError


    ## The trunk only supports comic data
    def episode(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def episodes(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def movie(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def movies(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def series(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def series_list(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def video(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def videos(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def video_type(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def video_types(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def video_category(self, item_id: str, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError

    def video_categories(self, params: cvapimodels.CommonParams) -> cvapimodels.CVResponse:
        raise UnsupportedResponseError