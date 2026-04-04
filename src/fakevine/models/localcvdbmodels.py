"""Database Model to support a static ComicTrunk based on the reddit localcvdb format."""
# ruff: noqa: D101
from sqlalchemy import ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship


class Base(DeclarativeBase):
    pass

class BaseTable:
    @declared_attr.directive
    def __tablename__(self) -> str:  # noqa: D105
        return f'cv_{self.__name__.lower()}'  # ty:ignore[unresolved-attribute]

    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-400)

class Publisher(BaseTable, Base):
    name: Mapped[str | None]
    image_url: Mapped[str | None]
    site_detail_url: Mapped[str | None]
    volumes: Mapped[list[Volume]] = relationship(back_populates="publisher")

class Person(BaseTable, Base):
    name: Mapped[str | None]

class Volume(BaseTable, Base):
    name: Mapped[str]
    aliases: Mapped[str | None]
    start_year: Mapped[str | None]
    publisher_id: Mapped[int | None] = mapped_column(ForeignKey("cv_publisher.id"))
    publisher: Mapped[Publisher] = relationship(back_populates="volumes")
    count_of_issues: Mapped[int | None]
    issues: Mapped[list[Issue]] = relationship(back_populates="volume")
    description: Mapped[str | None]
    image_url: Mapped[str | None]
    site_detail_url: Mapped[str | None]

class Issue(BaseTable, Base):
    volume_id: Mapped[int] = mapped_column(ForeignKey("cv_volume.id"))
    volume: Mapped[Volume] = relationship(back_populates="issues")
    name: Mapped[str | None]
    issue_number: Mapped[str | None]
    cover_date: Mapped[str | None]
    store_date: Mapped[str | None]
    description: Mapped[str | None]
    image_url: Mapped[str | None]
    site_detail_url: Mapped[str | None]
    character_credits: Mapped[str | None]
    person_credits: Mapped[str | None]
    team_credits: Mapped[str | None]
    location_credits: Mapped[str | None]
    story_arc_credits: Mapped[str | None]
    associated_images: Mapped[str | None]

class VolumeFTS(Base):
    __tablename__ = 'volume_fts'

    rowid: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str | None]
    aliases: Mapped[str | None]
