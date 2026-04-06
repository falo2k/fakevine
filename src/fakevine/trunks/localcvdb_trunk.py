# ruff: noqa: EM101, D102
import datetime
import json
import re
from typing import TYPE_CHECKING, Any

from loguru import logger
from sqlalchemy import Engine, Row, Select, Sequence, String, asc, create_engine, func, literal, or_, select
from sqlalchemy.exc import DatabaseError
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.sql.expression import text

from fakevine.models import cvapimodels as api
from fakevine.models import localcvdbmodels as db
from fakevine.trunks.comic_trunk import ComicTrunk, ObjectNotFoundError

if TYPE_CHECKING:
    from collections.abc import Callable
    from pathlib import Path

    from pydantic.fields import FieldInfo
    from sqlalchemy.orm import Query
    from sqlalchemy.sql.base import ReadOnlyColumnCollection
    from sqlalchemy.sql.elements import KeyedColumnElement


class LocalCVDBTrunk(ComicTrunk):
    """A Comic Trunk backed by the reddit localcvdb dump.

    As such, only supports data available in that dump's schema.
    """

    def __init__(self, database_path: Path) -> None:
        """Create a Local CV DB Trunk.

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

        self._base_entity_fields = ['id']

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

    async def character(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailCharacter]:
        raise NotImplementedError("Route not implemented by trunk")

    async def characters(self, params: api.FilterParams) -> api.MultiResponse[api.BaseCharacter]:
        raise NotImplementedError("Route not implemented by trunk")

    async def concept(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailConcept]:
        raise NotImplementedError("Route not implemented by trunk")

    async def concepts(self, params: api.FilterParams) -> api.MultiResponse[api.BaseConcept]:
        raise NotImplementedError("Route not implemented by trunk")

    async def _get_issue_data(self, db_record: db.Issue, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'name', 'issue_number', 'cover_date', 'store_date',
            'description', 'site_detail_url']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['date_last_updated'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['api_detail_url'] = f'https://comicvine.gamespot.com/api/issue/4000-{db_record.id}'

        if 'volume' in field_list and db_record.volume_id is not None:
            await session.refresh(db_record, ['volume'])
            response_dict['volume'] = {
                'id': db_record.volume.id,
                'name': db_record.volume.name,
                'api_detail_url': f'https://comicvine.gamespot.com/api/volume/4050-{db_record.volume.id}',
                'site_detail_url': db_record.volume.site_detail_url,
            }

        if 'character_credits' in field_list and db_record.character_credits is not None:
            response_dict['character_credits'] = json.loads(db_record.character_credits)

        if 'associated_images' in field_list and db_record.associated_images is not None:
            response_dict['associated_images'] = json.loads(db_record.associated_images)

        if 'person_credits' in field_list and db_record.person_credits is not None:
            response_dict['person_credits'] = json.loads(db_record.person_credits)

        if 'team_credits' in field_list and db_record.team_credits is not None:
            response_dict['team_credits'] = json.loads(db_record.team_credits)

        if 'location_credits' in field_list and db_record.location_credits is not None:
            response_dict['location_credits'] = json.loads(db_record.location_credits)

        if 'story_arc_credits' in field_list and db_record.story_arc_credits is not None:
            response_dict['story_arc_credits'] = json.loads(db_record.story_arc_credits)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def issue(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailIssue]:
        return await self._generate_single_response(int(item_id), params, db.Issue, api.DetailIssue,
                self._get_issue_data)  # ty:ignore[invalid-return-type]

    async def issues(self, params: api.FilterParams) -> api.MultiResponse[api.BaseIssue]:
        return await self._generate_multi_response(params, db.Issue, api.BaseIssue,
                self._get_issue_data)  # ty:ignore[invalid-return-type]

    async def location(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    async def locations(self, params: api.FilterParams) -> api.MultiResponse[api.BaseLocation]:
        raise NotImplementedError("Route not implemented by trunk")

    async def object(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailObject]:
        raise NotImplementedError("Route not implemented by trunk")

    async def objects(self, params: api.FilterParams) -> api.MultiResponse[api.BaseObject]:
        raise NotImplementedError("Route not implemented by trunk")

    async def origin(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    async def origins(self, params: api.FilterParams) -> api.MultiResponse[api.BaseOrigin]:
        raise NotImplementedError("Route not implemented by trunk")

    async def _get_person_data(self, db_record: db.Person, field_list: list[str], session: AsyncSession) -> dict:  # noqa: ARG002
        direct_copy_fields = [*self._base_entity_fields, 'name']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['date_last_updated'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['api_detail_url'] = f'https://comicvine.gamespot.com/api/person/4040-{db_record.id}'
        response_dict['site_detail_url'] = f'https://comicvine.gamespot.com/person/4040-{db_record.id}'

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def person(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPerson]:
        return await self._generate_single_response(int(item_id), params, db.Person, api.DetailPerson,
                self._get_person_data)  # ty:ignore[invalid-return-type]

    async def people(self, params: api.FilterParams) -> api.MultiResponse[api.BasePerson]:
        return await self._generate_multi_response(params, db.Person, api.BasePerson,
                self._get_person_data)  # ty:ignore[invalid-return-type]

    async def power(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPower]:
        raise NotImplementedError("Route not implemented by trunk")

    async def powers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePower]:
        raise NotImplementedError("Route not implemented by trunk")

    async def _get_publisher_data(self, db_record: db.Publisher, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'name', 'site_detail_url']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['date_last_updated'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['api_detail_url'] = f'https://comicvine.gamespot.com/api/publisher/4010-{db_record.id}'

        if 'volumes' in field_list:
            query: list = (await session.execute(
                select(db.Volume.id, db.Volume.name,
                    func.concat(literal("https://comicvine.gamespot.com/api/volume/4050-"), db.Volume.id).label('api_detail_url'),
                    func.concat(literal("https://comicvine.gamespot.com/volume/4050-"), db.Volume.id).label('site_detail_url')) \
                    .where(db.Volume.publisher_id == db_record.id))).all()
            response_dict['volumes'] = self._rows_to_list(query, api.SiteLinkedEntity)

        return {k:v for k,v in response_dict.items() if k in field_list}

    async def publisher(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailPublisher]:
        return await self._generate_single_response(int(item_id), params, db.Publisher, api.DetailPublisher,
                self._get_publisher_data)  # ty:ignore[invalid-return-type]

    async def publishers(self, params: api.FilterParams) -> api.MultiResponse[api.BasePublisher]:
        return await self._generate_multi_response(params, db.Publisher, api.BasePublisher,
                self._get_publisher_data)  # ty:ignore[invalid-return-type]

    async def search(self, params: api.SearchParams) -> api.SearchResponse:
        if params.query is None or params.query == "":
            raise ObjectNotFoundError

        if params.field_list is None or params.field_list == []:
            volume_model = api.BaseVolume
            return_class = api.SearchResponse
        else:
            field_list = params.field_list.split(',')
            volume_model = api.filtered_model(api.BaseVolume, field_list)
            return_class = api.MultiResponse[volume_model]  # ty:ignore[invalid-type-form]

        if params.resources is None or params.resources == "" or "volume" in params.resources:
            api_model = volume_model
            mapping_function = self._get_volume_data

            response_objects = []

            async with self.session() as session:
                rowid_query = select(db.VolumeFTS.rowid)

                def clean_token(token: str) -> str:
                    dialect_string = String().literal_processor(dialect=self.db_engine.dialect)(value=token)
                    if re.search(r"[^a-zA-Z0-9]",dialect_string[1:-1]) is not None:
                        dialect_string = "'\"" + dialect_string[1:-1].replace('"', '') + "\"'"
                    return dialect_string

                name_query_clauses = [text(f"volume_fts.name MATCH {clean_token(token)}") for token in params.query.split(' ') if token != '']
                aliases_query_clauses = [text(f"volume_fts.aliases MATCH {clean_token(token)}") for token in params.query.split(' ') if token != '']
                rowid_query = rowid_query.where(or_(*name_query_clauses, *aliases_query_clauses)).order_by(text('rank'))

                item_count_query: Query = select(func.count(db.Volume.id)).where(db.Volume.id.in_(rowid_query))
                item_query = select(db.Volume).where(db.Volume.id.in_(rowid_query)) \
                    .offset(params.offset).limit(params.limit)

                if params.field_list is None or params.field_list == []:
                    field_list = api_model.model_fields.keys()

                record_count: int = (await session.execute(item_count_query)).scalar()
                item_rows: Sequence[Row] = (await session.execute(item_query)).all()

                if item_rows is None:
                    return api.SearchResponse(limit=0, status_code=101)

                for item_row in item_rows:
                    item_record = item_row[0]

                    response_dict =  await mapping_function(item_record, field_list, session)
                    response_object = api_model(**response_dict)

                    response_objects.append(response_object)
            return return_class(
                limit=params.limit,
                offset=params.offset,
                number_of_page_results=len(response_objects),
                number_of_total_results=record_count,
                status_code=1,
                results=response_objects)


        return api.SearchResponse(
            limit=params.limit,
            offset=params.offset,
            number_of_page_results=0,
            number_of_total_results=0,
            status_code=1,
            results=[])

    async def story_arc(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    async def story_arcs(self, params: api.FilterParams) -> api.MultiResponse[api.BaseStoryArc]:
        raise NotImplementedError("Route not implemented by trunk")

    async def team(self, item_id: int, params: api.CommonParams) -> api.SingleResponse[api.DetailTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    async def teams(self, params: api.FilterParams) -> api.MultiResponse[api.BaseTeam]:
        raise NotImplementedError("Route not implemented by trunk")

    async def _get_volume_data(self, db_record: db.Volume, field_list: list[str], session: AsyncSession) -> dict:
        direct_copy_fields = [*self._base_entity_fields, 'name', 'aliases', 'start_year',
            'description', 'site_detail_url']

        response_dict = {}

        for copy_field in direct_copy_fields:
            response_dict[copy_field] = getattr(db_record, copy_field)

        response_dict['date_added'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['date_last_updated'] = self._datetime_format(datetime.datetime.fromtimestamp(0))  # noqa: DTZ006
        response_dict['api_detail_url'] = f'https://comicvine.gamespot.com/api/volume/4050-{db_record.id}'

        if 'publisher' in field_list and db_record.publisher_id is not None:
            await session.refresh(db_record, ['publisher'])
            response_dict['publisher'] = {
                'id': db_record.publisher.id,
                'name': db_record.publisher.name,
                'api_detail_url': f'https://comicvine.gamespot.com/api/publisher/4010-{db_record.publisher.id}',
                'site_detail_url': db_record.publisher.site_detail_url,
            }

        if 'issues' in field_list or 'count_of_issues' in field_list or \
             'first_issue' in field_list or 'last_issue' in field_list:
            query: list = (await session.execute(
                select(
                    db.Issue.id,
                    db.Issue.name,
                    func.concat(literal("https://comicvine.gamespot.com/api/issue/4000-"), db.Issue.id).label('api_detail_url'),
                    func.concat(literal("https://comicvine.gamespot.com/issue/4000-"), db.Issue.id).label('site_detail_url'),
                    db.Issue.issue_number) \
                    .where(db.Issue.volume_id == db_record.id) \
                    .order_by(asc(db.Issue.cover_date)))).all()
            response_dict['count_of_issues'] = len(query)
            response_dict['issues'] = self._rows_to_list(query, api.SiteLinkedIssue)
            if len(query) > 0:
                response_dict['first_issue'] = query[0]._asdict()
                response_dict['last_issue'] = query[-1]._asdict()

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
        """Check health of the local database by validating connectivity.

        Returns
        -------
        dict[str, str]
            Dictionary with 'status' set to 'ok' and 'trunk' set to 'localcvdb'.

        Raises
        ------
        RuntimeError
            If database connection cannot be established.

        """
        try:
            async with self.session() as session:
                await session.execute(text("SELECT 1"))
        except Exception as exc:
            message = f"LocalCVDB health check failed: {exc}"
            raise RuntimeError(message) from exc
        return {"status": "ok", "trunk": "localcvdb"}
