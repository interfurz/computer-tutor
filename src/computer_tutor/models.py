"""Protocol models shared by the HUD and MCP tools; no GUI imports."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Unit = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]
ShortText = Annotated[str, Field(min_length=1, max_length=160)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Rect(StrictModel):
    """Fractional coordinates relative to ONE monitor, never the virtual desktop."""

    x: Unit
    y: Unit
    width: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]
    height: Annotated[float, Field(gt=0, le=1, allow_inf_nan=False)]

    @model_validator(mode="after")
    def contained(self) -> "Rect":
        if self.x + self.width > 1.000001 or self.y + self.height > 1.000001:
            raise ValueError("The rectangle must fit inside the selected monitor.")
        return self


class Annotation(StrictModel):
    id: Annotated[str, Field(min_length=1, max_length=64)]
    target: Rect
    label: Annotated[str, Field(min_length=1, max_length=320)]
    style: Literal["rectangle", "spotlight", "point"] = "rectangle"
    placement: Literal["auto", "above", "below", "left", "right"] = "auto"


class Step(StrictModel):
    title: ShortText
    explanation: Annotated[str, Field(min_length=1, max_length=8000)]
    annotations: list[Annotation] = Field(default_factory=list, max_length=12)

    @model_validator(mode="after")
    def unique_ids(self) -> "Step":
        ids = [annotation.id for annotation in self.annotations]
        if len(ids) != len(set(ids)):
            raise ValueError("Annotation IDs must be unique within a step.")
        return self


class Tutorial(StrictModel):
    title: ShortText
    monitor_id: str = Field(min_length=1, max_length=200)
    steps: list[Step] = Field(min_length=1, max_length=100)


class TutorState:
    """Only accessed on the GUI thread. Navigation does not execute desktop actions."""

    def __init__(self) -> None:
        self.tutorial: Tutorial | None = None
        self.step_index = 0
        self.annotations_visible = True
        self.control_enabled = False
        self.revision = 0

    @property
    def step(self) -> Step | None:
        return self.tutorial.steps[self.step_index] if self.tutorial else None

    def load(self, tutorial: Tutorial) -> None:
        self.tutorial = tutorial
        self.step_index = 0
        self.annotations_visible = True
        self.revision += 1

    def navigate(self, direction: Literal["previous", "next"]) -> None:
        if direction not in ("previous", "next"):
            raise ValueError("Unknown navigation direction.")
        if not self.tutorial:
            raise ValueError("No tutorial is loaded.")
        index = self.step_index + (1 if direction == "next" else -1)
        self.step_index = max(0, min(len(self.tutorial.steps) - 1, index))
        self.revision += 1

    def stop(self) -> None:
        self.control_enabled = False
        self.annotations_visible = False
        self.revision += 1

    def snapshot(self) -> dict:
        return {
            "tutorial_title": self.tutorial.title if self.tutorial else None,
            "monitor_id": self.tutorial.monitor_id if self.tutorial else None,
            "step_index": self.step_index,
            "step_count": len(self.tutorial.steps) if self.tutorial else 0,
            "step": self.step.model_dump() if self.step else None,
            "annotations_visible": self.annotations_visible,
            "control_enabled": self.control_enabled,
            "revision": self.revision,
        }
