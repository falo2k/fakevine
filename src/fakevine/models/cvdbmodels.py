"""Database Model to support a static ComicTrunk.

Note that this doesn't expect foreign key constraints on the database.  This is due to both the
nature of how data is likely to be sourced, and general mistrust of the original source.  For the
same reason all relationships are view only.
"""
# ruff: noqa: D101
import datetime  # noqa: TC003 # If moved into a typecheck block, SQLAlchemy will fail

from sqlalchemy.ext.associationproxy import AssociationProxy, association_proxy
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
    real_name: Mapped[str | None]
    origin: Mapped[Origin] = relationship(
        primaryjoin="Character.origin_id == Origin.id",
        foreign_keys="[Character.origin_id]",
        viewonly=True,
    )
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Character.publisher_id == Publisher.id",
        foreign_keys="[Character.publisher_id]",
        viewonly=True,
    )

    enemies: Mapped[list[Character]] = relationship(
        secondary="cv_character_enemy",
        primaryjoin="Character.id == cv_character_enemy.c.character_id",
        secondaryjoin="cv_character_enemy.c.enemy_id == Character.id",
        viewonly=True,
    )

    friends: Mapped[list[Character]] = relationship(
        secondary="cv_character_friend",
        primaryjoin="Character.id == cv_character_friend.c.character_id",
        secondaryjoin="cv_character_friend.c.friend_id == Character.id",
        viewonly=True,
    )

    creators: Mapped[list[Person]] = relationship(
        secondary="cv_character_creator",
        primaryjoin="Character.id == cv_character_creator.c.character_id",
        secondaryjoin="cv_character_creator.c.person_id == Person.id",
        viewonly=True,
    )

    issue_credits: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_character",
        primaryjoin="Character.id == cv_issue_character.c.character_id",
        secondaryjoin="Issue.id == cv_issue_character.c.issue_id",
        viewonly=True,
    )

    issues_died_in: Mapped[list[Issue]] = relationship(
        secondary="cv_character_issue_died",
        primaryjoin="Character.id == cv_character_issue_died.c.character_id",
        secondaryjoin="Issue.id == cv_character_issue_died.c.issue_id",
        viewonly=True,
    )

    # movies is not covered by this database as it focussed on comics only

    powers: Mapped[list[Power]] = relationship(
        secondary="cv_character_power",
        primaryjoin="Character.id == cv_character_power.c.character_id",
        secondaryjoin="Power.id == cv_character_power.c.power_id",
        viewonly=True,
    )

    story_arc_credits: AssociationProxy[list[StoryArc]] = association_proxy("issue_credits", "story_arc_credits")

    team_enemies: Mapped[list[Team]] = relationship(
        secondary="cv_team_character_enemy",
        primaryjoin="Character.id == cv_team_character_enemy.c.character_id",
        secondaryjoin="Team.id == cv_team_character_enemy.c.team_id",
        viewonly=True,
    )

    team_friends: Mapped[list[Team]] = relationship(
        secondary="cv_team_character_friend",
        primaryjoin="Character.id == cv_team_character_friend.c.character_id",
        secondaryjoin="Team.id == cv_team_character_friend.c.team_id",
        viewonly=True,
    )

    teams: Mapped[list[Team]] = relationship(
        secondary="cv_team_character_member",
        primaryjoin="Character.id == cv_team_character_member.c.character_id",
        secondaryjoin="Team.id == cv_team_character_member.c.team_id",
        viewonly=True,
    )

    volume_credits: AssociationProxy[list[Volume]] = association_proxy("issue_credits", "volume")

class Concept(BaseEntity, Base):
    issue_credits: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_concept",
        primaryjoin="Concept.id == cv_issue_concept.c.concept_id",
        secondaryjoin="Issue.id == cv_issue_concept.c.issue_id",
        viewonly=True,
    )

    volume_credits: AssociationProxy[list[Volume]] = association_proxy("issue_credits", "volume")

class Issue(BaseEntity, Base):
    # In the API, this would return "false" for None
    # Dropping from the model as a fairly useless field
    # has_staff_review: Mapped[dict[str, str] | None] = mapped_column(JSON)  # noqa: ERA001
    volume_id: Mapped[int | None]
    volume: Mapped[Volume] = relationship(
        primaryjoin="Issue.volume_id == Volume.id",
        foreign_keys="[Issue.volume_id]",
        viewonly=True)
    issue_number: Mapped[str | None]
    cover_date: Mapped[datetime.date | None]
    store_date: Mapped[datetime.date | None]

    associated_images: Mapped[list[IssueAssociatedImage]] = relationship(
        primaryjoin="Issue.id == IssueAssociatedImage.issue_id",
        foreign_keys="[Issue.id]",
        viewonly=True,
    )

    character_credits: Mapped[list[Character]] = relationship(
        secondary="cv_issue_character",
        primaryjoin="Issue.id == cv_issue_character.c.issue_id",
        secondaryjoin="Character.id == cv_issue_character.c.character_id",
        viewonly=True,
    )

    character_died_in: Mapped[list[Character]] = relationship(
        secondary="cv_character_issue_died",
        secondaryjoin="Character.id == cv_character_issue_died.c.character_id",
        primaryjoin="Issue.id == cv_character_issue_died.c.issue_id",
        viewonly=True,
    )

    concept_credits: Mapped[list[Concept]] = relationship(
        secondary="cv_issue_concept",
        primaryjoin="Issue.id == cv_issue_concept.c.issue_id",
        secondaryjoin="Concept.id == cv_issue_concept.c.concept_id",
        viewonly=True,
    )

    location_credits: Mapped[list[Location]] = relationship(
        secondary="cv_issue_location",
        primaryjoin="Issue.id == cv_issue_location.c.issue_id",
        secondaryjoin="Location.id == cv_issue_location.c.location_id",
        viewonly=True,
    )

    object_credits: Mapped[list[Object]] = relationship(
        secondary="cv_issue_object",
        primaryjoin="Issue.id == cv_issue_object.c.issue_id",
        secondaryjoin="Object.id == cv_issue_object.c.object_id",
        viewonly=True,
    )

    person_credits: Mapped[list[IssueCredit]] = relationship(
        primaryjoin="Issue.id == IssueCredit.issue_id",
        foreign_keys="[IssueCredit.issue_id]",
        viewonly=True,
    )

    story_arc_credits: Mapped[list[StoryArc]] = relationship(
        secondary="cv_story_arc_issue",
        primaryjoin="Issue.id == cv_story_arc_issue.c.issue_id",
        secondaryjoin="StoryArc.id == cv_story_arc_issue.c.story_arc_id",
        viewonly=True,
    )

    team_credits: Mapped[list[Team]] = relationship(
        secondary="cv_issue_team",
        primaryjoin="Issue.id == cv_issue_team.c.issue_id",
        secondaryjoin="Team.id == cv_issue_team.c.team_id",
        viewonly=True,
    )

    team_disbanded_in: Mapped[list[Team]] = relationship(
        secondary="cv_team_issue_disbanded",
        primaryjoin="Issue.id == cv_team_issue_disbanded.c.issue_id",
        secondaryjoin="Team.id == cv_team_issue_disbanded.c.team_id",
        viewonly=True,
    )

class IssueAssociatedImage(Base):
    __tablename__ = 'cv_issue_associated_image'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-200)
    id: Mapped[int] = mapped_column(primary_key=True, sort_order=-150)
    caption: Mapped[str | None]
    original_url: Mapped[str | None]
    image_tags: Mapped[str | None]


class Location(BaseEntity, Base):
    issue_credits: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_location",
        secondaryjoin="Issue.id == cv_issue_location.c.issue_id",
        primaryjoin="Location.id == cv_issue_location.c.location_id",
        viewonly=True,
    )
    story_arc_credits: AssociationProxy[list[StoryArc]] = association_proxy("issue_credits", "story_arc_credits")
    volumes: AssociationProxy[list[Volume]] = association_proxy("issue_credits", "volume")

class Object(BaseEntity, Base):
    issue_credits: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_object",
        secondaryjoin="Issue.id == cv_issue_object.c.issue_id",
        primaryjoin="Object.id == cv_issue_object.c.object_id",
        viewonly=True,
    )

    story_arc_credits: AssociationProxy[list[StoryArc]] = association_proxy("issue_credits", "story_arc_credits")
    volumes: AssociationProxy[list[Volume]] = association_proxy("issue_credits", "volume")

class Origin(BaseTable, Base):
    characters: Mapped[list[Character]] = relationship(
        primaryjoin="Character.origin_id == Origin.id",
        foreign_keys="[Character.origin_id]",
        viewonly=True,
    )

# Don't actually use the deck/image columns
class Person(BaseEntity, Base):
    email: Mapped[str | None]
    birth: Mapped[datetime.datetime | None]
    gender: Mapped[int | None]
    country: Mapped[str | None]
    death: Mapped[dict | None] = mapped_column(JSON)
    hometown: Mapped[str | None]
    website: Mapped[str | None]

    created_characters: Mapped[list[Character]] = relationship(
        secondary="cv_character_creator",
        primaryjoin="cv_character_creator.c.person_id == Person.id",
        secondaryjoin="Character.id == cv_character_creator.c.character_id",
        viewonly=True,
    )

    issues: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_credit",
        primaryjoin="cv_issue_credit.c.person_id == Person.id",
        secondaryjoin="Issue.id == cv_issue_credit.c.issue_id",
        viewonly=True,
    )

    story_arc_credits: AssociationProxy[list[StoryArc]] = association_proxy("issues", "story_arc_credits")
    volumes: AssociationProxy[list[Volume]] = association_proxy("issues", "volume")

class Power(BaseEntity, Base):
    characters: Mapped[list[Character]] = relationship(
        secondary="cv_character_power",
        primaryjoin="Power.id == cv_character_power.c.power_id",
        secondaryjoin="Character.id == cv_character_power.c.character_id",
        viewonly=True,
    )

class Publisher(BaseEntity, Base):
    location_address: Mapped[str | None]
    location_city: Mapped[str | None]
    location_state: Mapped[str | None]

    characters: Mapped[list[Character]] = relationship(
        primaryjoin="Character.publisher_id == Publisher.id",
        foreign_keys="[Character.publisher_id]",
        viewonly=True,
    )

    story_arcs: AssociationProxy[list[StoryArc]] = association_proxy("characters", "story_arc_credits")

    teams: Mapped[list[Team]] = relationship(
        primaryjoin="Publisher.id == Team.publisher_id",
        foreign_keys="[Team.publisher_id]",
        viewonly=True,
    )

    volumes: Mapped[list[Volume]] = relationship(
        primaryjoin="Publisher.id == Volume.publisher_id",
        foreign_keys="[Publisher.id]",
        viewonly=True,
    )

class StoryArc(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="StoryArc.publisher_id == Publisher.id",
        foreign_keys="[StoryArc.publisher_id]",
        viewonly=True,
    )

    issues: Mapped[list[Issue]] = relationship(
        secondary="cv_story_arc_issue",
        primaryjoin="StoryArc.id == cv_story_arc_issue.c.story_arc_id",
        secondaryjoin="Issue.id == cv_story_arc_issue.c.issue_id",
        viewonly=True,
    )

class Team(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Team.publisher_id == Publisher.id",
        foreign_keys="[Team.publisher_id]",
        viewonly=True,
    )

    character_enemies: Mapped[list[Character]] = relationship(
        secondary="cv_team_character_enemy",
        primaryjoin="Team.id == cv_team_character_enemy.c.team_id",
        secondaryjoin="Character.id == cv_team_character_enemy.c.character_id",
        viewonly=True,
    )

    character_friends: Mapped[list[Character]] = relationship(
        secondary="cv_team_character_friend",
        primaryjoin="Team.id == cv_team_character_friend.c.team_id",
        secondaryjoin="Character.id == cv_team_character_friend.c.character_id",
        viewonly=True,
    )

    characters: Mapped[list[Character]] = relationship(
        secondary="cv_team_character_member",
        primaryjoin="Team.id == cv_team_character_member.c.team_id",
        secondaryjoin="Character.id == cv_team_character_member.c.character_id",
        viewonly=True,
    )

    issue_credits: Mapped[list[Issue]] = relationship(
        secondary="cv_issue_team",
        primaryjoin="Team.id == cv_issue_team.c.team_id",
        secondaryjoin="Issue.id == cv_issue_team.c.issue_id",
        viewonly=True,
    )

    disbanded_in_issues: Mapped[list[Issue]] = relationship(
        secondary="cv_team_issue_disbanded",
        primaryjoin="Team.id == cv_team_issue_disbanded.c.team_id",
        secondaryjoin="Issue.id == cv_team_issue_disbanded.c.issue_id",
        viewonly=True,
    )

    story_arc_credits: AssociationProxy[list[StoryArc]] = association_proxy("issue_credits", "story_arc_credits")
    volumes: AssociationProxy[list[Volume]] = association_proxy("issue_credits", "volume")

class Type(Base):
    __tablename__ = 'cv_type'

    id: Mapped[int] = mapped_column(sort_order=-200)
    detail_resource_name: Mapped[str]  = mapped_column(primary_key=True)
    list_resource_name: Mapped[str] =  mapped_column(primary_key=True)

class Volume(BaseEntity, Base):
    publisher_id: Mapped[int | None]
    publisher: Mapped[Publisher] = relationship(
        primaryjoin="Volume.publisher_id == Publisher.id",
        foreign_keys="[Publisher.id]",
        viewonly=True,
    )
    start_year: Mapped[str | None]

    issues: Mapped[Issue] = relationship(
        primaryjoin="Issue.volume_id == Volume.id",
        foreign_keys="[Issue.volume_id]",
        viewonly=True,
    )

    characters: AssociationProxy[list[Character]] = association_proxy("issues", "character_credits")
    locations: AssociationProxy[list[Location]] = association_proxy("issues", "location_credits")
    objects: AssociationProxy[list[Object]] = association_proxy("issues", "object_credits")

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

class CharacterCreator(Base):
    __tablename__= 'cv_character_creator'

    person_id:  Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

# There isn't way to do symmetrical self-relationships like this that satisfied me without data
# duplication so updates to the table will need to consider the reflection of any relationship.
# Could have kept a constraint of id<id2 but that would just shift the problem to query side.
class CharacterEnemy(Base):
    __tablename__ = 'cv_character_enemy'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    enemy_id: Mapped[int] = mapped_column(primary_key=True)

class CharacterFriend(Base):
    __tablename__ = 'cv_character_friend'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    friend_id: Mapped[int] = mapped_column(primary_key=True)

class CharacterIssueDied(Base):
    __tablename__ = 'cv_character_issue_died'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)

class CharacterPower(Base):
    __tablename__ = 'cv_character_power'

    character_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    power_id: Mapped[int] = mapped_column(primary_key=True)

class IssueCharacter(Base):
    __tablename__ = 'cv_issue_character'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    character_id: Mapped[int] = mapped_column(primary_key=True)

class IssueCredit(Base):
    __tablename__ = 'cv_issue_credit'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    person_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-50)
    person: Mapped[Person] = relationship(
        primaryjoin="IssueCredit.person_id == Person.id",
        foreign_keys="[IssueCredit.person_id]",
        viewonly=True,
    )

    role: Mapped[str]

class IssueConcept(Base):
    __tablename__ = 'cv_issue_concept'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    concept_id: Mapped[int] = mapped_column(primary_key=True)

class IssueLocation(Base):
    __tablename__ = 'cv_issue_location'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    location_id: Mapped[int] = mapped_column(primary_key=True)

class IssueObject(Base):
    __tablename__ = 'cv_issue_object'

    issue_id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(primary_key=True)

class IssueTeam(Base):
    __tablename__ = 'cv_issue_team'

    issue_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    team_id: Mapped[int] = mapped_column(primary_key=True)

class StoryArcIssue(Base):
    __tablename__ = 'cv_story_arc_issue'

    story_arc_id: Mapped[int] = mapped_column(primary_key=True, sort_order=-100)
    issue_id: Mapped[int] = mapped_column(primary_key=True)
