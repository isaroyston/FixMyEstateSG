from __future__ import annotations

import re
from datetime import datetime, timezone
from enum import Enum
from typing import Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    LIFT_FAULT = "lift_fault"
    LIGHTING_FAULT = "lighting_fault"
    CLEANLINESS = "cleanliness"
    PEST = "pest"
    WATER_LEAKAGE = "water_leakage"
    CORRIDOR_OBSTRUCTION = "corridor_obstruction"
    NOISE = "noise"
    DAMAGED_FACILITY = "damaged_facility"
    GREENERY = "greenery"
    PARKING_ISSUE = "parking_issue"
    SAFETY_HAZARD = "safety_hazard"
    OTHER = "other"
    UNCLEAR = "unclear"


class Urgency(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"
    UNCLEAR = "unclear"


class RoutingTeam(str, Enum):
    ESTATE_MAINTENANCE = "estate_maintenance"
    CLEANING_TEAM = "cleaning_team"
    PEST_CONTROL = "pest_control"
    HORTICULTURE_TEAM = "horticulture_team"
    PARKING_ENFORCEMENT = "parking_enforcement"
    NEIGHBOUR_DISPUTE_TEAM = "neighbour_dispute_team"
    SAFETY_INSPECTION = "safety_inspection"
    WATER_SERVICES = "water_services"
    OTHER = "other"
    UNCLEAR = "unclear"


class Recurrence(str, Enum):
    ONE_OFF = "one_off"
    RECURRING = "recurring"
    UNKNOWN = "unknown"


class Status(str, Enum):
    DRAFT = "draft"
    OPEN = "open"
    NEEDS_MORE_INFO = "needs_more_info"
    ESCALATED = "escalated"
    CLOSED = "closed"


class ConfidenceLevel(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class Location(BaseModel):
    block: Optional[str] = None
    street_or_estate: Optional[str] = None
    town: Optional[str] = None
    level: Optional[str] = None
    unit: Optional[str] = None
    specific_area: Optional[str] = None


class Confidence(BaseModel):
    category: ConfidenceLevel = ConfidenceLevel.LOW
    urgency: ConfidenceLevel = ConfidenceLevel.LOW
    location: ConfidenceLevel = ConfidenceLevel.LOW
    routing: ConfidenceLevel = ConfidenceLevel.LOW


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def normalized_enum_text(value: object) -> str | None:
    if value is None:
        return None
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, str):
        return value.strip().lower().replace("-", "_").replace(" ", "_")
    return str(value).strip().lower().replace("-", "_").replace(" ", "_")


class Ticket(BaseModel):
    ticket_id: str = ""
    ticket_title: str = "Unclear estate issue"
    reported_datetime: str = Field(default_factory=now_iso)
    category: Category = Category.UNCLEAR
    urgency: Urgency = Urgency.UNCLEAR
    routing_team: RoutingTeam = RoutingTeam.UNCLEAR
    location: Location = Field(default_factory=Location)
    issue_summary: str = ""
    affected_groups: List[str] = Field(default_factory=list)
    risk_flags: List[str] = Field(default_factory=list)
    recurrence: Recurrence = Recurrence.UNKNOWN
    missing_details: List[str] = Field(default_factory=list)
    suggested_follow_up_questions: List[str] = Field(default_factory=list)
    follow_up_answers: Dict[str, str] = Field(default_factory=dict)
    evidence_quotes: List[str] = Field(default_factory=list)
    confidence: Confidence = Field(default_factory=Confidence)
    status: Status = Status.DRAFT

    @field_validator("ticket_id", "ticket_title", "reported_datetime", "issue_summary", mode="before")
    @classmethod
    def none_to_empty_string(cls, value: object) -> object:
        return "" if value is None else value

    @field_validator(
        "affected_groups",
        "risk_flags",
        "missing_details",
        "suggested_follow_up_questions",
        "evidence_quotes",
        mode="before",
    )
    @classmethod
    def none_to_list(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value

    @field_validator("follow_up_answers", mode="before")
    @classmethod
    def none_to_dict(cls, value: object) -> object:
        return {} if value is None or value == [] else value

    @field_validator("location", "confidence", mode="before")
    @classmethod
    def none_to_object(cls, value: object) -> object:
        return {} if value is None or value == [] else value

    @field_validator("category", mode="before")
    @classmethod
    def none_to_unclear_category(cls, value: object) -> object:
        normalized = normalized_enum_text(value)
        if normalized is None:
            return Category.UNCLEAR
        aliases = {
            "lighting": Category.LIGHTING_FAULT,
            "light_fault": Category.LIGHTING_FAULT,
            "lift": Category.LIFT_FAULT,
            "elevator": Category.LIFT_FAULT,
            "leakage": Category.WATER_LEAKAGE,
            "water": Category.WATER_LEAKAGE,
            "obstruction": Category.CORRIDOR_OBSTRUCTION,
            "damaged": Category.DAMAGED_FACILITY,
            "damage": Category.DAMAGED_FACILITY,
            "parking": Category.PARKING_ISSUE,
            "hazard": Category.SAFETY_HAZARD,
            "safety": Category.SAFETY_HAZARD,
        }
        return aliases.get(normalized, normalized)

    @field_validator("urgency", mode="before")
    @classmethod
    def none_to_unclear_urgency(cls, value: object) -> object:
        normalized = normalized_enum_text(value)
        if normalized is None:
            return Urgency.UNCLEAR
        aliases = {
            "urgent": Urgency.HIGH,
            "high_priority": Urgency.HIGH,
            "medium_priority": Urgency.MEDIUM,
            "low_priority": Urgency.LOW,
            "emergency": Urgency.CRITICAL,
            "immediate": Urgency.CRITICAL,
        }
        return aliases.get(normalized, normalized)

    @field_validator("routing_team", mode="before")
    @classmethod
    def none_to_unclear_routing(cls, value: object) -> object:
        normalized = normalized_enum_text(value)
        if normalized is None:
            return RoutingTeam.UNCLEAR
        aliases = {
            "maintenance": RoutingTeam.ESTATE_MAINTENANCE,
            "estate": RoutingTeam.ESTATE_MAINTENANCE,
            "cleaning": RoutingTeam.CLEANING_TEAM,
            "pest": RoutingTeam.PEST_CONTROL,
            "horticulture": RoutingTeam.HORTICULTURE_TEAM,
            "parking": RoutingTeam.PARKING_ENFORCEMENT,
            "neighbour_dispute": RoutingTeam.NEIGHBOUR_DISPUTE_TEAM,
            "neighbor_dispute": RoutingTeam.NEIGHBOUR_DISPUTE_TEAM,
            "safety": RoutingTeam.SAFETY_INSPECTION,
            "water": RoutingTeam.WATER_SERVICES,
        }
        allowed = {item.value for item in RoutingTeam}
        return aliases.get(normalized, normalized if normalized in allowed else RoutingTeam.UNCLEAR)

    @field_validator("recurrence", mode="before")
    @classmethod
    def none_to_unknown_recurrence(cls, value: object) -> object:
        normalized = normalized_enum_text(value)
        if normalized is None:
            return Recurrence.UNKNOWN
        aliases = {
            "repeated": Recurrence.RECURRING,
            "repeat": Recurrence.RECURRING,
            "repeats": Recurrence.RECURRING,
            "recurs": Recurrence.RECURRING,
            "ongoing": Recurrence.RECURRING,
            "multiple_times": Recurrence.RECURRING,
            "oneoff": Recurrence.ONE_OFF,
            "one_time": Recurrence.ONE_OFF,
            "once": Recurrence.ONE_OFF,
        }
        allowed = {item.value for item in Recurrence}
        if normalized in aliases:
            return aliases[normalized]
        if normalized in allowed:
            return normalized
        if re.fullmatch(r"\d+_(minute|minutes|hour|hours|day|days|week|weeks|month|months)", normalized):
            return Recurrence.UNKNOWN
        if normalized in {"today", "yesterday", "recently", "just_now", "unknown_duration"}:
            return Recurrence.UNKNOWN
        return Recurrence.UNKNOWN

    @field_validator("status", mode="before")
    @classmethod
    def none_to_draft_status(cls, value: object) -> object:
        normalized = normalized_enum_text(value)
        if normalized is None:
            return Status.DRAFT
        aliases = {
            "need_more_info": Status.NEEDS_MORE_INFO,
            "needs_info": Status.NEEDS_MORE_INFO,
            "more_info_needed": Status.NEEDS_MORE_INFO,
            "escalate": Status.ESCALATED,
            "urgent": Status.ESCALATED,
        }
        allowed = {item.value for item in Status}
        return aliases.get(normalized, normalized if normalized in allowed else Status.DRAFT)
