# ruff: noqa: D103
import datetime
from enum import Enum
from typing import Any
from zoneinfo import ZoneInfo

from fakevine.models import cvapimodels, cvdbmodels


class AssociatedEntities(Enum):
    """Enum to choose how helper functions deal with association data."""

    NONE = 0
    MASTERED = 1
    ALL = 2

# Parsing functions for converting from a detailed API response DB ORM model instances
# For association tables where edits can be done in the wiki from both entities, these are updated
# by default from the "main" parent entity.  CV does not cascade timestamp updates to associated entities,
# so order of processing may be important (i.e. process all responses by date)
# Expensive set based uniqueness checks are in place because the data can be awful, and a good output
# is more important than a quick output.
def parse_person_response(api_response: str) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailPerson.model_validate_json(api_response)
    db_object = cvdbmodels.Person(
        birth=parse_cv_datetime(api_object.birth),
        **api_object.model_dump(include=
            {'email','gender','country','hometown','website'} if api_object.death is None else
            {'email','gender','country','hometown','website','death'}),
        **select_common_fields(api_object),
    )
    output: list[cvdbmodels.Base] = [db_object]

    # No associations editable on page

    return output

def parse_object_reponse(api_response: str) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailObject.model_validate_json(api_response)
    db_object = cvdbmodels.Object(**select_common_fields(api_object))
    output: list[cvdbmodels.Base] = [db_object]

    # No associations editable on page

    return output

def parse_concept_reponse(api_response: str) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailConcept.model_validate_json(api_response)
    db_object = cvdbmodels.Concept(**select_common_fields(api_object))
    output: list[cvdbmodels.Base] = [db_object]

    # No associations editable on page

    return output

def parse_location_reponse(api_response: str) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailLocation.model_validate_json(api_response)
    db_object = cvdbmodels.Location(**select_common_fields(api_object))
    output: list[cvdbmodels.Base] = [db_object]

    # No associations editable on page

    return output

def parse_power_reponse(api_response: str, associations: AssociatedEntities = AssociatedEntities.NONE) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailPower.model_validate_json(api_response)
    db_object = cvdbmodels.Power(
        **{k:v for k,v in select_common_fields(api_object).items() if k not in ['deck', 'image']})
    output: list[cvdbmodels.Base] = [db_object]

    if associations == AssociatedEntities.ALL:
        for entity in set(api_object.characters):
            db_object= cvdbmodels.CharacterPower(power_id=api_object.id, character_id=entity.id)
            output.append(db_object)

    return output

def parse_publisher_reponse(api_response: str) -> list[cvdbmodels.Base]:
    api_object = cvapimodels.DetailPublisher.model_validate_json(api_response)
    db_object = cvdbmodels.Publisher(
        **api_object.model_dump(include={'location_address','location_city','location_state'}),
        **select_common_fields(api_object),
    )
    output: list[cvdbmodels.Base] = [db_object]

    # No associations can be driven from the publisher editing.

    return output

def parse_character_reponse(api_response: str, associations: AssociatedEntities = AssociatedEntities.MASTERED) -> list[cvdbmodels.Base]:  # noqa: C901
    output = []

    api_object = cvapimodels.DetailCharacter.model_validate_json(api_response)
    db_object = cvdbmodels.Character(
        birth=parse_cv_birthdate(api_object.birth),
        origin_id=api_object.origin if api_object.origin is None else api_object.origin.id,
        publisher_id=api_object.publisher if api_object.publisher is None else api_object.publisher.id,
        **api_object.model_dump(include={'gender','real_name'}),
        **select_common_fields(api_object),
    )
    output.append(db_object)

    if associations in [AssociatedEntities.ALL, AssociatedEntities.MASTERED]:
        for enemy in set(api_object.character_enemies):
            if api_object.id <= enemy.id:
                enemy_object = cvdbmodels.CharacterEnemy(character_id=api_object.id, enemy_id=enemy.id)
                output.append(enemy_object)

        for friend in set(api_object.character_friends):
            if api_object.id <= friend.id:
                enemy_object = cvdbmodels.CharacterFriend(character_id=api_object.id, friend_id=friend.id)
                output.append(enemy_object)

        for creator in set(api_object.creators):
            creator_object = cvdbmodels.CharacterCreator(character_id=api_object.id, person_id=creator.id)
            output.append(creator_object)

        for death_issue in set(api_object.issues_died_in):
            issue_object = cvdbmodels.CharacterIssueDied(character_id=api_object.id, issue_id=death_issue.id)
            output.append(issue_object)

        for power in set(api_object.powers):
            power_object = cvdbmodels.CharacterPower(character_id=api_object.id, power_id=power.id)
            output.append(power_object)

    if associations == AssociatedEntities.ALL:
        for entity in set(api_object.teams):
            db_object = cvdbmodels.TeamCharacterMember(character_id=api_object.id, team_id=entity.id)
            output.append(db_object)

        for entity in set(api_object.team_enemies):
            db_object = cvdbmodels.TeamCharacterEnemy(character_id=api_object.id, team_id=entity.id)
            output.append(db_object)

        for entity in set(api_object.team_friends):
            db_object = cvdbmodels.TeamCharacterFriend(character_id=api_object.id, team_id=entity.id)
            output.append(db_object)

    return output

def parse_team_reponse(api_response: str, associations: AssociatedEntities = AssociatedEntities.MASTERED) -> list[cvdbmodels.Base]:
    output = []

    api_object = cvapimodels.DetailTeam.model_validate_json(api_response)
    db_object = cvdbmodels.Team(
        publisher_id=api_object.publisher if api_object.publisher is None else api_object.publisher.id,
        **select_common_fields(api_object),
    )
    output.append(db_object)

    if associations in [AssociatedEntities.ALL, AssociatedEntities.MASTERED]:
        for enemy in set(api_object.character_enemies):
            enemy_object = cvdbmodels.TeamCharacterEnemy(team_id=api_object.id, character_id=enemy.id)
            output.append(enemy_object)

        for friend in set(api_object.character_friends):
            friend_object = cvdbmodels.TeamCharacterFriend(team_id=api_object.id, character_id=friend.id)
            output.append(friend_object)

        for character in set(api_object.characters):
            character_object = cvdbmodels.TeamCharacterMember(team_id=api_object.id, character_id=character.id)
            output.append(character_object)

        for issue in set(api_object.isssues_disbanded_in):
            issue_object = cvdbmodels.TeamIssueDisbanded(team_id=api_object.id, issue_id=issue.id)
            output.append(issue_object)

    return output

def parse_volume_reponse(api_response: str) -> list[cvdbmodels.Base]:
    output = []

    api_object = cvapimodels.DetailVolume.model_validate_json(api_response)
    db_object = cvdbmodels.Volume(
        start_year=api_object.start_year,
        publisher_id=api_object.publisher if api_object.publisher is None else api_object.publisher.id,
        **select_common_fields(api_object),
    )
    output.append(db_object)

    # No associations can be driven from the publisher editing.

    return output

def parse_storyarc_reponse(api_response: str, associations: AssociatedEntities = AssociatedEntities.NONE) -> list[cvdbmodels.Base]:
    output = []

    api_object = cvapimodels.DetailStoryArc.model_validate_json(api_response)
    db_object = cvdbmodels.StoryArc(
        publisher_id=api_object.publisher if api_object.publisher is None else api_object.publisher.id,
        **select_common_fields(api_object),
    )
    output.append(db_object)

    if associations == AssociatedEntities.ALL:
        for entity in set(api_object.issues):
            db_object = cvdbmodels.StoryArcIssue(storyarc_id=api_object.id, issue_id=entity.id)
            output.append(db_object)

    return output

def parse_issue_reponse(api_response: str, associations: AssociatedEntities = AssociatedEntities.MASTERED) -> list[cvdbmodels.Base]:
    output = []

    api_object = cvapimodels.DetailIssue.model_validate_json(api_response)
    db_object = cvdbmodels.Issue(
        issue_number=api_object.issue_number,
        cover_date=parse_cv_date(api_object.cover_date),
        store_date=parse_cv_date(api_object.store_date),
        **select_common_fields(api_object),
    )
    output.append(db_object)

    # Associated images should always be included as they don't have their own source
    if api_object.associated_images is not None:
        for image in api_object.associated_images:
            db_object = cvdbmodels.IssueAssociatedImage(
                issue_id=api_object.id,
                id = image.id,
                caption = image.caption,
                original_url = image.original_url,
                image_tags = image.image_tags,
            )
            output.append(db_object)

    if associations in [AssociatedEntities.ALL, AssociatedEntities.MASTERED]:
        for credit in set(api_object.character_credits):
            db_object = cvdbmodels.IssueCharacter(issue_id=api_object.id, character_id=credit.id)
            output.append(db_object)

        for credit in set(api_object.concept_credits):
            db_object = cvdbmodels.IssueConcept(issue_id=api_object.id, concept_id=credit.id)
            output.append(db_object)

        for credit in set(api_object.location_credits):
            db_object = cvdbmodels.IssueLocation(issue_id=api_object.id, location_id=credit.id)
            output.append(db_object)

        for credit in set(api_object.object_credits):
            db_object = cvdbmodels.IssueObject(issue_id=api_object.id, object_id=credit.id)
            output.append(db_object)

        for credit in set(api_object.person_credits):
            db_object = cvdbmodels.IssueCredit(issue_id=api_object.id, person_id=credit.id, role=credit.role)
            output.append(db_object)

        for credit in set(api_object.team_credits):
            db_object = cvdbmodels.IssueTeam(issue_id=api_object.id, team_id=credit.id)
            output.append(db_object)

        for credit in set(api_object.story_arc_credits):
            db_object = cvdbmodels.StoryArcIssue(issue_id=api_object.id, storyarc_id=credit.id)
            output.append(db_object)

    return output

def select_common_fields(api_object: cvapimodels.BaseEntity)-> dict[str, Any]:
    return api_object.model_dump(include=
    {'id', 'site_detail_url', 'api_detail_url', 'name', 'image', 'description', 'deck', 'aliases'}) | \
    {
        'date_added' : parse_cv_datetime(api_object.date_added),
        'date_last_updated' : parse_cv_datetime(api_object.date_last_updated),
    }

def parse_cv_datetime(input_datetime: str | None) -> datetime.datetime | None:
    if input_datetime is None:
        return None

    # Absolute scenes in the CV dataset
    input_datetime = input_datetime.removeprefix('-')

    try:
        return datetime.datetime.strptime(input_datetime, "%Y-%m-%d %H:%M:%S").replace(tzinfo=ZoneInfo("US/Pacific"))
    except:  # noqa: E722 # There is only so much I'm willing to sanitise badly managed data
        return None

def parse_cv_date(input_date: str | None) -> datetime.date  | None:
    if input_date is None:
        return None

    # Absolute scenes in the CV dataset
    input_date = input_date.removeprefix('-')

    try:
        return datetime.date.strptime(input_date, "%Y-%m-%d")
    except:  # noqa: E722 # There is only so much I'm willing to sanitise badly managed data
        return None

def parse_cv_birthdate(input_date: str | None) -> datetime.date  | None:
    if input_date is None:
        return None

    try:
        return datetime.date.strptime(input_date, "%b %d, %Y")
    except:  # noqa: E722 # There is only so much I'm willing to sanitise badly managed data
        return None
