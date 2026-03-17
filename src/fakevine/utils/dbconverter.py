import datetime
from typing import TYPE_CHECKING
from zoneinfo import ZoneInfo

import typer
from pydantic import ValidationError
from rich.progress import BarColumn, Progress, TaskID, TaskProgressColumn, TextColumn, TimeRemainingColumn
from sqlalchemy import Connection, Engine, MetaData, Table, create_engine, delete, inspect, select, text
from sqlalchemy.exc import DatabaseError, IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.sql import or_

from fakevine.models import cvapimodels, cvdbmodels, helpers
from fakevine.utils import cvstatic
from fakevine.utils.console import console

if TYPE_CHECKING:
    from collections.abc import Callable
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
    console.log("Initialising output database")
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
            increment: float = 100.0 / len(static_data.results)

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
        task_list: dict[str, TaskID] = {}
        for table_name in expected_tables:
            task_list[table_name] = table_progress.add_task(table_name, total=100, start=False)

        tables_to_process = [
            ('cv_person', helpers.parse_person_response, cvdbmodels.Person, 0),
            ('cv_object', helpers.parse_object_reponse, cvdbmodels.Object, 0),
            ('cv_concept', helpers.parse_concept_reponse, cvdbmodels.Concept, 0),
            ('cv_location', helpers.parse_location_reponse, cvdbmodels.Location, 0),
            ('cv_power', helpers.parse_power_reponse, cvdbmodels.Power, 0),
            ('cv_publisher', helpers.parse_publisher_reponse, cvdbmodels.Publisher, 0),
            ('cv_volume', helpers.parse_volume_reponse, cvdbmodels.Volume, 25000),
            ('cv_character', helpers.parse_character_reponse, cvdbmodels.Character, 20000),
            ('cv_team', helpers.parse_team_reponse, cvdbmodels.Team, 0),
            ('cv_storyarc', helpers.parse_story_arc_reponse, cvdbmodels.StoryArc, 0),
            ('cv_issue', helpers.parse_issue_reponse, cvdbmodels.Issue, 5000),
        ]

        for table_name, parse_func, db_model, commit_batch_size in tables_to_process:
            process_cv_table(table_progress, task_list[table_name], reddit_db_meta.tables[table_name],
                reddit_db_connection, output_session, parse_func, commit_batch_size)
            capture_update_record(table=table_name, db_model=db_model, session=output_session)

    finally:
        table_progress.stop()
        output_session.close()
        reddit_db_connection.close()

    console.log("All done! :white_check_mark:")

def capture_update_record(table: str, db_model: type[cvdbmodels.BaseEntity], session: Session) -> None:
    timestamp = datetime.datetime.fromtimestamp(0, tz=ZoneInfo("US/Pacific"))
    latest_record = session.execute(select(db_model).order_by(db_model.date_last_updated.desc())).first()
    if latest_record is not None:
        timestamp = latest_record[0].date_last_updated

    session.add(cvdbmodels.UpdateRecords(
        table=table,
        last_scraped_datetime_utc=datetime.datetime.now(datetime.UTC),
        last_cv_update_datetime_pt=timestamp))
    session.commit()

def process_cv_table(progress: Progress, task_id: TaskID, reddit_db_table: Table,
                         reddit_db_connection: Connection, output_session: Session,
                         parsing_function: Callable, commit_batch_size: int):
        select_stmt = select(reddit_db_table.c.raw_api_response).order_by(reddit_db_table.c.date_last_updated.asc())
        data = reddit_db_connection.execute(select_stmt).all()
        progress.start_task(task_id)
        increment: float = 100.0 / len(data)

        output_session.begin()
        counter = 0
        try:
            for data_entry in data:
                try:
                    new_records = parsing_function(data_entry[0])

                    # Special case for characters - need to clear out entries in symmetrical relationship tables
                    if reddit_db_table.name == 'cv_character' and len(new_records) > 0:
                        character_record: cvdbmodels.Character = new_records[0]
                        delete_enemies = delete(cvdbmodels.CharacterEnemy).where(
                            or_(cvdbmodels.CharacterEnemy.character_id == character_record.id,
                                cvdbmodels.CharacterEnemy.enemy_id == character_record.id))
                        output_session.execute(delete_enemies)
                        delete_friends = delete(cvdbmodels.CharacterFriend).where(
                            or_(cvdbmodels.CharacterFriend.character_id == character_record.id,
                                cvdbmodels.CharacterFriend.friend_id == character_record.id))
                        output_session.execute(delete_friends)

                    output_session.merge_all(new_records)
                    counter += 1
                    if commit_batch_size > 0 and counter > commit_batch_size:
                        output_session.commit()
                        counter = 0
                except ValidationError as exc:
                    console.log(f"Error validating row for {reddit_db_table.name}. Dropping. {data_entry}", style="error")
                    console.log(exc, style="error")
                except AttributeError:
                    console.log(
                        f"Attribute error in {reddit_db_table.name}. I probably need to loosen the API model. {data_entry}",
                        style="error")
                    console.print_exception()
                except IntegrityError:
                    raise
                except:  # noqa: E722 # I'm a bad bad person
                    console.log(f"Unrecognised exception thrown parsing row. Dropping. {data_entry}", style="error")
                    console.print_exception()
                finally:
                    progress.update(task_id, advance=increment)

            output_session.commit()
        except IntegrityError as exc:
            console.log(f"Integrity error thrown procesisng {reddit_db_table.name}.", style="error")
            console.log(exc, style="error")
            output_session.flush()
            output_session.rollback()


        progress.update(task_id, completed=100)


