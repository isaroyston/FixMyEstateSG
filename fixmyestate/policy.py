from __future__ import annotations

from datetime import datetime
from typing import Dict, Iterable, List
from uuid import uuid4

from .models import Category, ConfidenceLevel, Location, RoutingTeam, Status, Ticket, Urgency, now_iso


ROUTING_BY_CATEGORY: Dict[Category, RoutingTeam] = {
    Category.LIFT_FAULT: RoutingTeam.ESTATE_MAINTENANCE,
    Category.LIGHTING_FAULT: RoutingTeam.ESTATE_MAINTENANCE,
    Category.CLEANLINESS: RoutingTeam.CLEANING_TEAM,
    Category.PEST: RoutingTeam.PEST_CONTROL,
    Category.WATER_LEAKAGE: RoutingTeam.WATER_SERVICES,
    Category.CORRIDOR_OBSTRUCTION: RoutingTeam.SAFETY_INSPECTION,
    Category.NOISE: RoutingTeam.NEIGHBOUR_DISPUTE_TEAM,
    Category.DAMAGED_FACILITY: RoutingTeam.ESTATE_MAINTENANCE,
    Category.GREENERY: RoutingTeam.HORTICULTURE_TEAM,
    Category.PARKING_ISSUE: RoutingTeam.PARKING_ENFORCEMENT,
    Category.SAFETY_HAZARD: RoutingTeam.SAFETY_INSPECTION,
    Category.OTHER: RoutingTeam.OTHER,
    Category.UNCLEAR: RoutingTeam.UNCLEAR,
}

STATUS_RELEVANT_MISSING_DETAILS = {
    "usable location",
    "affected lift or lift lobby",
    "safety or accessibility impact",
    "leakage safety risk",
}


def enum_value(value: object) -> str:
    return getattr(value, "value", str(value))


def make_ticket_id() -> str:
    return f"FME-{datetime.now().strftime('%Y%m%d')}-{uuid4().hex[:6].upper()}"


def has_text(value: str | None) -> bool:
    return bool(value and value.strip())


def unique_nonempty_text(items: Iterable[str]) -> List[str]:
    """Clean repeated values inside one ticket's list fields only."""
    seen = set()
    result: List[str] = []
    for item in items:
        cleaned = item.strip()
        key = cleaned.lower()
        if cleaned and key not in seen:
            result.append(cleaned)
            seen.add(key)
    return result


def display_location(location: Location) -> str:
    parts = [
        location.block,
        location.street_or_estate,
        location.town,
        location.level,
        location.unit,
        location.specific_area,
    ]
    visible = unique_nonempty_text(part for part in parts if has_text(part))
    return ", ".join(visible) if visible else "Unclear"


def derive_status(ticket: Ticket) -> Status:
    normalized_flags = {flag.strip().lower() for flag in ticket.risk_flags}
    if (
        "non_actionable_input" in normalized_flags
        and ticket.category == Category.UNCLEAR
        and ticket.urgency in {Urgency.LOW, Urgency.UNCLEAR}
    ):
        return Status.CLOSED

    if ticket.urgency in {Urgency.HIGH, Urgency.CRITICAL}:
        return Status.ESCALATED

    normalized_missing = {detail.strip().lower() for detail in ticket.missing_details}
    if STATUS_RELEVANT_MISSING_DETAILS.intersection(normalized_missing):
        return Status.NEEDS_MORE_INFO

    return Status.OPEN


def apply_ticket_guardrails(ticket: Ticket) -> Ticket:
    ticket.ticket_id = ticket.ticket_id or make_ticket_id()
    ticket.reported_datetime = ticket.reported_datetime or now_iso()
    ticket.ticket_title = ticket.ticket_title or "Unclear estate issue"
    ticket.routing_team = ROUTING_BY_CATEGORY.get(ticket.category, RoutingTeam.UNCLEAR)
    ticket.confidence.routing = (
        ConfidenceLevel.HIGH if ticket.routing_team != RoutingTeam.UNCLEAR else ConfidenceLevel.LOW
    )
    ticket.missing_details = unique_nonempty_text(ticket.missing_details)
    ticket.suggested_follow_up_questions = unique_nonempty_text(ticket.suggested_follow_up_questions)[:3]
    ticket.risk_flags = unique_nonempty_text(ticket.risk_flags)
    ticket.evidence_quotes = unique_nonempty_text(ticket.evidence_quotes)
    ticket.status = derive_status(ticket)
    return ticket
