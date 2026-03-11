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

    endpoint: Mapped[str] = mapped_column(primary_key=True)
    last_scraped_datetime_utc: Mapped[datetime.datetime]
    last_cv_update_datetime_pt: Mapped[datetime.datetime]

class BaseTable:
    @declared_attr.directive
    def __tablename__(cls) -> str:  # noqa: D105
        return f'cv_{cls.__name__.lower()}'  # ty:ignore[unresolved-attribute]

    id: Mapped[int] = mapped_column(primary_key=True)
    api_detail_url: Mapped[str]
    name: Mapped[str | None]
    site_detail_url: Mapped[str]

class BaseEntity(BaseTable):
    aliases: Mapped[str | None]
    date_added: Mapped[datetime.datetime]
    date_last_updated: Mapped[datetime.datetime]
    deck: Mapped[str | None]
    description: Mapped[str | None]
    image: Mapped[dict[str,str | None] | None] = mapped_column(JSON)

class Character(BaseEntity, Base):
    first_appeared_in_issue_id : Mapped[int | None]
    # first_appeared_in_issue: Mapped[Issue] = relationship(
    #     primaryjoin="Charater.first_appeared_in_issue_id == Issue.id",
    #     foreign_keys="[Character.first_appeared_in_issue_id]")
    birth: Mapped[datetime.datetime | None]
    gender: Mapped[int]
    origin_id: Mapped[int | None]
    # origin: Mapped[Origin] = relationship(
    #     primaryjoin="Charater.origin_id == Origin.id",
    #     foreign_keys="[Character.origin_id]")
    publisher_id: Mapped[int | None]
    # publisher: Mapped[Publisher] = relationship(
    #     primaryjoin="Character.publisher_id == Publisher.id",
    #     foreign_keys="[Character.publisher_id]")
    real_name: Mapped[str | None]
    # count_of_issue_appearances: int
    # enemies
    # friends
    # issues

# TODO(@falo2k): Come back to this later to sort out symmetrical relationships.  Maybe add constraints to ensure id > id and then unions.
class CharacterEnemy(Base):
    __tablename__ = 'cv_character_enemy'

    character_id: Mapped[int] = mapped_column(primary_key=True)
    character: Mapped[Character] = relationship(
        primaryjoin="CharacterEnemy.character_id == Character.id",
        foreign_keys="[CharacterEnemy.character_id]")
    enemy_id: Mapped[int] = mapped_column(primary_key=True)
    enemy: Mapped[Character] = relationship(
        primaryjoin="CharacterEnemy.enemy_id == Character.id",
        foreign_keys="[CharacterEnemy.enemy_id]")

class CharacterFriend(Base):
    __tablename__ = 'cv_character_friend'

    character_id: Mapped[int] = mapped_column(primary_key=True)
    character: Mapped[Character] = relationship(
        primaryjoin="CharacterFriend.character_id == Character.id",
        foreign_keys="[CharacterFriend.character_id]")
    friend_id: Mapped[int] = mapped_column(primary_key=True)
    friend: Mapped[Character] = relationship(
        primaryjoin="CharacterFriend.friend_id == Character.id",
        foreign_keys="[CharacterFriend.friend_id]")

class Concept(BaseEntity, Base):
    # first_appeared_in_issue
    # start_year = earliest issue
    # count_of_issue_appearances: int
    ...

class Issue(BaseEntity, Base):
    # In the API, this would return "false" for None
    has_staff_review: Mapped[dict[str, str] | None] = mapped_column(JSON)
    volume_id: Mapped[int | None]
    volume: Mapped[Volume] = relationship(
        primaryjoin="Issue.volume_id == Volume.id",
        foreign_keys="[Issue.volume_id]")
    issue_number: Mapped[str | None]
    cover_date: Mapped[datetime.date | None]
    store_date: Mapped[datetime.date | None]
    #location_credits: Mapped[list[Location]] = relationship(secondary="IssueLocation")
    #character_credits
    #concept_credits
    #object_credits
    #person_credits
    #storyarc_credits
    #team_credits
    #team_disbanded_in

class Location(BaseEntity, Base):
    # first_appeared_in_issue : Mapped[int | None]
    # start_year = earliest issue
    # count_of_issue_appearances: int
    ...

class Object(BaseEntity, Base):
    # first_appeared_in_issue : Mapped[int | None]
    # start_year = earliest issue
    # count_of_issue_appearances: int
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
    # count_of_issue_appearances: int

class Power(BaseEntity, Base):
    ...

class Publisher(BaseEntity, Base):
    location_address: Mapped[str | None]
    location_city: Mapped[str | None]
    location_state: Mapped[str | None]

class StoryArc(BaseEntity, Base):
    # first_appeared_in_issue : Mapped[int | None]
    # count_of_issue_appearances: int
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
    #count_of_team_members: int
    # first_appeared_in_issue : Mapped[int | None]
    # count_of_issue_appearances: int

class Type(Base):
    __tablename__ = 'cv_type'

    id: Mapped[int]
    detail_resource_name: Mapped[str]  = mapped_column(primary_key=True)
    list_resource_name: Mapped[str] =  mapped_column(primary_key=True)

class Volume(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Volume.publisher_id == Publisher.id",
        foreign_keys="[Volume.publisher_id]",
    )
    # first_issue
    # last_issue
    start_year: Mapped[str | None]
    #count_of_issues: int
    #issues
    #characters
    #locations
    #objects

class IssueLocation(Base):
    __tablename__ = 'cv_issue_location'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    location_id: Mapped[int] = mapped_column(primary_key=True)

class IssueTeam(Base):
    __tablename__ = 'cv_issue_team'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(primary_key=True)

class TeamIssueDisbanded(Base):
    __tablename__ = 'cv_team_issue_disbanded'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(primary_key=True)

class IssueCharacter(Base):
    __tablename__ = 'cv_issue_character'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class CharacterIssueDied(Base):
    __tablename__ = 'cv_character_issue_died'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class IssueCredit(Base):
    __tablename__ = 'cv_issue_credit'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    person_id: Mapped[int] = mapped_column(primary_key=True)

    role: Mapped[str]

class IssueConcept(Base):
    __tablename__ = 'cv_issue_concept'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    concept_id: Mapped[int] = mapped_column(primary_key=True)

class IssueObject(Base):
    __tablename__ = 'cv_issue_object'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(primary_key=True)

class StoryArcIssue(Base):
    __tablename__ = 'cv_storyarc_issue'

    storyarc_id: Mapped[int] = mapped_column(primary_key=True)
    issue_id: Mapped[int] = mapped_column(primary_key=True)

