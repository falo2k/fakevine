#ruff: noqa: TC002, D103
from pathlib import Path
from typing import Annotated

import typer
from rich.markdown import Markdown
from sqlalchemy import create_mock_engine
from sqlalchemy.engine.mock import MockConnection
from sqlalchemy.schema import ExecutableDDLElement

from fakevine.models import cvdbmodels
from fakevine.utils import dbconverter
from fakevine.utils.console import console

typer_app = typer.Typer()

@typer_app.command()
def print_schema() -> None:
    console.log("CV SIMPLE DB SCHEMA:")
    def dump(sql: ExecutableDDLElement, *multiparams, **params) -> None:  # noqa: ANN002, ANN003, ARG001
        console.log(sql.compile(dialect=engine.dialect))

    engine: MockConnection = create_mock_engine(url="sqlite:///:memory:", executor=dump)
    cvdbmodels.Base.metadata.create_all(engine, checkfirst=False)

@typer_app.command()
def readme() -> None:
    with Path.open(Path(Path(__file__).parent, 'README.md')) as markdown_file:
        md = Markdown(markdown_file.read())
        console.log(md)

@typer_app.command()
def convert_db(
        reddit_db: Annotated[Path, typer.Argument(help="The reddit sourced dump file")],
        output_db: Annotated[Path, typer.Argument(help="Output filename for the new database")] = Path('fakevine.db'),
        overwrite: Annotated[bool, typer.Option(help="Overwrite the output file")] = False,  # noqa: FBT002
        ) -> None:
    if not reddit_db.is_file():
        console.log(f'{reddit_db} is not a file', style='error')
        raise typer.Exit

    if output_db.exists():
        if overwrite and output_db.is_file():
            console.log(f'{output_db} exists and overwrite is enabled. Deleting.', style='warning')
            output_db.unlink()
        else:
            console.log(f'{output_db} exists/is a path and overwriting is not enabled', style='error')
            raise typer.Exit

    dbconverter.convert_db(reddit_db, output_db)
    # Can we guarantee the order of messages?  If not, we likely have to do a check for multiple IDs / reaction to
    # breaking primary key constraints at the end


def main() -> None:
    typer_app()
