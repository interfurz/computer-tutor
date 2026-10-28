import math

import pytest
from pydantic import ValidationError

from computer_tutor.models import Annotation, Rect, Step, Tutorial, TutorState


def tutorial():
    return Tutorial(
        title="Speichern",
        monitor_id="test",
        steps=[
            Step(title="Öffnen", explanation="Öffne das Menü."),
            Step(title="Speichern", explanation="Wähle Speichern."),
        ],
    )


@pytest.mark.parametrize(
    "values",
    [
        dict(x=-0.1, y=0, width=0.2, height=0.2),
        dict(x=0.9, y=0, width=0.2, height=0.2),
        dict(x=0, y=0.9, width=0.2, height=0.2),
        dict(x=0, y=0, width=0, height=0.2),
        dict(x=math.nan, y=0, width=0.2, height=0.2),
        dict(x=0, y=0, width=math.inf, height=0.2),
    ],
)
def test_out_of_monitor_targets_rejected(values):
    with pytest.raises(ValidationError):
        Rect(**values)


def test_duplicate_annotation_ids_rejected():
    item = Annotation(id="same", label="Ziel", target=Rect(x=0, y=0, width=1, height=1))
    with pytest.raises(ValidationError, match="unique"):
        Step(title="Test", explanation="Text", annotations=[item, item])


def test_no_actions_can_be_smuggled_into_a_step():
    with pytest.raises(ValidationError, match="Extra inputs"):
        Step.model_validate({"title": "Test", "explanation": "Text", "action": "click"})


def test_empty_tutorial_rejected():
    with pytest.raises(ValidationError):
        Tutorial(title="Test", monitor_id="test", steps=[])


def test_navigation_is_bounded_and_does_not_grant_control():
    state = TutorState()
    state.load(tutorial())
    state.navigate("previous")
    assert state.step_index == 0
    for _ in range(3):
        state.navigate("next")
    assert state.step_index == 1
    assert not state.control_enabled
    assert state.step.title == "Speichern"
    state.load(tutorial())
    assert state.step_index == 0


def test_stop_revokes_control_but_retains_lesson():
    state = TutorState()
    state.load(tutorial())
    state.control_enabled = True
    revision = state.revision
    state.stop()
    snapshot = state.snapshot()
    assert snapshot["revision"] > revision
    assert not snapshot["control_enabled"]
    assert not snapshot["annotations_visible"]
    assert snapshot["step_count"] == 2
