import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import typer
from rich.progress import BarColumn, Progress, TaskID, TaskProgressColumn, TextColumn, TimeRemainingColumn
from sqlalchemy import Engine, MetaData, create_engine, inspect, select, text
from sqlalchemy.exc import DatabaseError, SQLAlchemyError
from sqlalchemy.orm import Session

from fakevine.models import cvapimodels, cvdbmodels
from fakevine.utils import cvstatic
from fakevine.utils.console import console

if TYPE_CHECKING:
    from pathlib import Path

    from sqlalchemy.engine.reflection import Inspector


def convert_db(reddit_db: Path, output_db: Path):
    # Basic sanity check that the input DB has the tables we want
    console.log("Validating input DB structure")
    reddit_db_engine: Engine = create_engine(f"sqlite:///{reddit_db.absolute()}")
    inspector: Inspector = inspect(reddit_db_engine)

    try:
        with reddit_db_engine.connect() as conn:
            _ = conn.execute(text("SELECT 'hello engine'"))
    except DatabaseError as exc:
        console.log("Input database is not a valid SQL database", style='error')
        raise typer.Exit from exc

    expected_tables = [
        'cv_character',
        'cv_concept',
        'cv_issue',
        'cv_location',
        'cv_object',
        'cv_person',
        'cv_power',
        'cv_publisher',
        'cv_storyarc',
        'cv_team',
        'cv_volume',
    ]

    expected_columns: list[str] = ['id', 'date_last_updated', 'site_detail_url', 'raw_api_response']

    for expected in expected_tables:
        if expected not in inspector.get_table_names():
            console.log(f'Could not find table {expected} in the input file', style='error')
            raise typer.Exit

        column_names: list[str] = [col['name'] for col in inspector.get_columns(table_name=expected)]

        for expected_col in expected_columns:
            if expected_col not in column_names:
                console.log(f'Missing column {expected_col} in table {expected} in the input file', style='error')
                raise typer.Exit

    console.log("Input file looks good :white_check_mark:")
    console.log("Initilising output database")
    try:
        output_db_engine: Engine = create_engine(f"sqlite:///{output_db.absolute()}")
        cvdbmodels.Base.metadata.create_all(output_db_engine)
    except SQLAlchemyError as exc:
        console.log("Unknown SQLAlchmey error creating database")
        raise typer.Exit from exc

    console.log("Setting up static table data")

    static_progress = Progress(
        TextColumn(" " * 13),
        TextColumn("[progress.description]{task.description}", style='italic'),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console)
    static_progress.start()

    try:
        origin_task: TaskID = static_progress.add_task('cv_origin', total=100, start=True)
        type_task: TaskID = static_progress.add_task('cv_type', total=100, start=True)

        for task_id, source_data, db_model, api_model in \
            [(origin_task, cvstatic.origins, cvdbmodels.Origin, cvapimodels.BaseOrigin),
             (type_task, cvstatic.types, cvdbmodels.Type, cvapimodels.BaseTypes)]:
            static_data: cvapimodels.MultiResponse[api_model] = \
                cvapimodels.MultiResponse[api_model].model_validate_json(source_data)
            increment: float = 1.0 / len(static_data.results)

            with Session(output_db_engine) as output_session:
                for x in static_data.results:
                    new_data = db_model(**x.model_dump())  # ty:ignore[no-matching-overload]
                    output_session.add(new_data)
                    static_progress.update(task_id, advance=increment)

                output_session.commit()

            static_progress.update(task_id, completed=100)
    finally:
        static_progress.stop()


    table_progress = Progress(
        TextColumn(" " * 13),
        TextColumn("[progress.description]{task.description}", style='italic'),
        BarColumn(),
        TaskProgressColumn(),
        TimeRemainingColumn(),
        console=console)
    table_progress.start()

    console.log("Processing source tables into new database")
    reddit_db_meta = MetaData()
    reddit_db_meta.reflect(reddit_db_engine)
    reddit_db_connection = reddit_db_engine.connect()
    output_session = Session(output_db_engine)
    try:
        common_mappings: dict[str,str] = {
            'aliases': 'aliases',
            'date_added': 'date_added',
            'date_last_updated': 'date_last_updated',
            'description': 'description',
        }

        task_list: dict[str, TaskID] = {}
        for table_name in expected_tables:
            task_list[table_name] = table_progress.add_task(table_name, total=100, start=False)

        # I thought about making this all data driven, but it's just an absolute arse to do it reliably given the nature
        # of the data.  It's better to just get it done to get a good data set sorted out.

        # cv_person
        table_name = 'cv_person'
        table_progress.start_task(task_list[table_name])
        reflected_table = reddit_db_meta.tables[table_name]
        select_stmt = select(reflected_table.c.raw_api_response).order_by(reflected_table.c.date_last_updated.asc())
        data = reddit_db_connection.execute(select_stmt).all()
        increment: float = 1.0 / len(data)

        output_session.begin()
        for data_entry in data:
            try:
                api_object = cvapimodels.DetailPerson.model_validate_json(data_entry[0])
                db_object = cvdbmodels.Person(
                    birth=parse_cv_datetime(api_object.birth),
                    **api_object.model_dump(include={'email','gender','country','death','hometown','website'}),
                    **select_common_fields(api_object),
                )
                output_session.add(db_object)
            except:  # noqa: E722 # I'm a bad bad person
                console.log(f"Exceptions thrown parsing row. Dropping from results. {data_entry}", style="error")
                console.print_exception()
            finally:
                table_progress.update(task_list[table_name], advance=increment)
        output_session.commit()

        table_progress.update(task_list[table_name], completed=100)

        # cv_object
        # cv_concept
        # cv_location
        # cv_power
        # cv_publisher
        # cv_character
        # cv_team
        # cv_volume
        # cv_issue
        # cv_storyarc

    finally:
        table_progress.stop()
        output_session.close()
        reddit_db_connection.close()

    console.log("All done! :white_check_mark:")

def select_common_fields(api_object: cvapimodels.BaseEntity):
    return api_object.model_dump(include=
    {'id', 'site_detail_url', 'api_detail_url', 'name', 'image', 'description', 'deck', 'aliases'}) | \
    {
        'date_added' : parse_cv_datetime(api_object.date_added),
        'date_last_updated' : parse_cv_datetime(api_object.date_last_updated),
    }

def parse_cv_datetime(input_datetime: str | None) -> datetime.datetime | None:  # noqa: D103
    if input_datetime is None:
        return None

    return datetime.datetime.strptime(input_datetime, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("US/Pacific"))


def parse_cv_date(input_date: str | None) -> datetime.date  | None:  # noqa: D103
    if input_date is None:
        return None

    return datetime.date.strptime(input_date, "%Y-%m-%d")

