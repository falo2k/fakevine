"""Database Model to support a static ComicTrunk.

Note that this doesn't expect foreign key constraints on the database.  This is due to both the
nature of how data is likely to be sourced, and general mistrust of the original source.
"""
# ruff: noqa: D101
import datetime  # noqa: TC003 # If moved into a typecheck block, SQLAlchemy will fail

from sqlalchemy.orm import DeclarativeBase, Mapped, declared_attr, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass

class UpdateRecords(Base):
    __tablename__ = "cv_updaterecords"

    table: Mapped[str] = mapped_column(primary_key=True, sort_order=-200)
    last_scraped_datetime_utc: Mapped[datetime.datetime] = mapped_column(sort_order=-100)
    last_cv_update_datetime_pt: Mapped[datetime.datetime] = mapped_column(sort_order=0)

class BaseTable:
    @declared_attr.directive
    def __tablename__(self) -> str:  # noqa: D105
        return f'cv_{self.__name__.lower()}'  # ty:ignore[unresolved-attribute]

    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-200)
    api_detail_url: Mapped[str] = mapped_column(sort_order=-198)
    name: Mapped[str | None] = mapped_column(sort_order=-199)
    site_detail_url: Mapped[str] = mapped_column(sort_order=-197)

class BaseEntity(BaseTable):
    aliases: Mapped[str | None] = mapped_column(sort_order=-140)
    date_added: Mapped[datetime.datetime] = mapped_column(sort_order=-150)
    date_last_updated: Mapped[datetime.datetime] = mapped_column(sort_order=-151)
    deck: Mapped[str | None] = mapped_column(sort_order=-100)
    description: Mapped[str | None] = mapped_column(sort_order=-90)
    image: Mapped[dict[str,str | None] | None] = mapped_column(JSON(none_as_null=True), sort_order=-80)

class Character(BaseEntity, Base):
    birth: Mapped[datetime.date | None]
    gender: Mapped[int]
    origin_id: Mapped[int | None]
    publisher_id: Mapped[int | None]
    real_name: Mapped[str | None]

# No constraints, but assumes that id <= enemy_id and is symmetrical.
class CharacterEnemy(Base):
    __tablename__ = 'cv_character_enemy'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character: Mapped[Character] = relationship(
        primaryjoin="CharacterEnemy.character_id == Character.id",
        foreign_keys="[CharacterEnemy.character_id]")
    enemy_id: Mapped[int] = mapped_column(primary_key=True)
    enemy: Mapped[Character] = relationship(
        primaryjoin="CharacterEnemy.enemy_id == Character.id",
        foreign_keys="[CharacterEnemy.enemy_id]")

# No constraints, but assumes that id <= friend_id and is symmetrical.
class CharacterFriend(Base):
    __tablename__ = 'cv_character_friend'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character: Mapped[Character] = relationship(
        primaryjoin="CharacterFriend.character_id == Character.id",
        foreign_keys="[CharacterFriend.character_id]")
    friend_id: Mapped[int] = mapped_column(primary_key=True)
    friend: Mapped[Character] = relationship(
        primaryjoin="CharacterFriend.friend_id == Character.id",
        foreign_keys="[CharacterFriend.friend_id]")

class CharacterPower(Base):
    __tablename__ = 'cv_character_power'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    power_id: Mapped[int] = mapped_column(primary_key=True)

class Concept(BaseEntity, Base):
    ...

class Issue(BaseEntity, Base):
    # In the API, this would return "false" for None
    # Dropping from the model as a fairly useless field
    # has_staff_review: Mapped[dict[str, str] | None] = mapped_column(JSON)  # noqa: ERA001
    volume_id: Mapped[int | None]
    volume: Mapped[Volume] = relationship(
        primaryjoin="Issue.volume_id == Volume.id",
        foreign_keys="[Issue.volume_id]")
    issue_number: Mapped[str | None]
    cover_date: Mapped[datetime.date | None]
    store_date: Mapped[datetime.date | None]

class IssueAssociatedImage(Base):
    __tablename__ = 'cv_issue_associated_image'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-200)
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-150)
    caption: Mapped[str | None]
    original_url: Mapped[str | None]
    image_tags: Mapped[str | None]


class Location(BaseEntity, Base):
    ...

class Object(BaseEntity, Base):
    ...

class Origin(BaseTable, Base):
    ...

# Don't actually use the deck/image columns
class Person(BaseEntity, Base):
    email: Mapped[str | None]
    birth: Mapped[datetime.datetime | None]
    gender: Mapped[int | None]
    country: Mapped[str | None]
    death: Mapped[dict | None] = mapped_column(JSON)
    hometown: Mapped[str | None]
    website: Mapped[str | None]

class Power(BaseEntity, Base):
    ...

class Publisher(BaseEntity, Base):
    location_address: Mapped[str | None]
    location_city: Mapped[str | None]
    location_state: Mapped[str | None]

class StoryArc(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="StoryArc.publisher_id == Publisher.id",
        foreign_keys="[StoryArc.publisher_id]",
    )

class Team(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Team.publisher_id == Publisher.id",
        foreign_keys="[Team.publisher_id]",
    )

class TeamCharacterFriend(Base):
    __tablename__ = 'cv_team_character_friend'

    team_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class TeamCharacterEnemy(Base):
    __tablename__ = 'cv_team_character_enemy'

    team_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class TeamCharacterMember(Base):
    __tablename__ = 'cv_team_character_member'

    team_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class TeamIssueDisbanded(Base):
    __tablename__ = 'cv_team_issue_disbanded'

    team_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    issue_id: Mapped[int] = mapped_column(primary_key=True)

class Type(Base):
    __tablename__ = 'cv_type'

    id: Mapped[int] = mapped_column(sort_order=-200)
    detail_resource_name: Mapped[str]  = mapped_column(primary_key=True)
    list_resource_name: Mapped[str] =  mapped_column(primary_key=True)

class Volume(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Volume.publisher_id == Publisher.id",
        foreign_keys="[Volume.publisher_id]",
    )
    start_year: Mapped[str | None]

class IssueLocation(Base):
    __tablename__ = 'cv_issue_location'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    location_id: Mapped[int] = mapped_column(primary_key=True)

class IssueTeam(Base):
    __tablename__ = 'cv_issue_team'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    team_id: Mapped[int] = mapped_column(primary_key=True)

class IssueCharacter(Base):
    __tablename__ = 'cv_issue_character'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class CharacterIssueDied(Base):
    __tablename__ = 'cv_character_issue_died'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)

class IssueCredit(Base):
    __tablename__ = 'cv_issue_credit'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    person_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-50)

    role: Mapped[str]

class IssueConcept(Base):
    __tablename__ = 'cv_issue_concept'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    concept_id: Mapped[int] = mapped_column(primary_key=True)

class IssueObject(Base):
    __tablename__ = 'cv_issue_object'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(primary_key=True)

class StoryArcIssue(Base):
    __tablename__ = 'cv_storyarc_issue'

    storyarc_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    issue_id: Mapped[int] = mapped_column(primary_key=True)

class CharacterCreator(Base):
    __tablename__= 'cv_character_creator'

    person_id:  Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)
