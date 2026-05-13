from __future__ import annotations

from dataclasses import dataclass

from fixmyestate.models import Category, RoutingTeam, Status, Urgency


@dataclass(frozen=True)
class DraftExtractionCase:
    complaint: str
    expected_category: Category
    expected_urgencies: tuple[Urgency, ...]
    expected_routing: RoutingTeam
    focus: str = ""
    expected_statuses: tuple[Status, ...] = ()
    expected_risk_flags: tuple[str, ...] = ()


DRAFT_EXTRACTION_CASES = [
    DraftExtractionCase(
        "The lift at Blk 123 Tampines keeps breaking down. My mum uses a wheelchair and cannot go downstairs.",
        Category.LIFT_FAULT,
        (Urgency.HIGH,),
        RoutingTeam.ESTATE_MAINTENANCE,
        "High-priority accessibility impact from an estate facility fault.",
        (Status.ESCALATED,),
    ),
    DraftExtractionCase(
        "There are rats near the rubbish chute at Blk 55 Bedok.",
        Category.PEST,
        (Urgency.MEDIUM,),
        RoutingTeam.PEST_CONTROL,
        "Routine actionable estate issue with enough category signal.",
    ),
    DraftExtractionCase(
        "Water is leaking near the electrical riser at level 8.",
        Category.WATER_LEAKAGE,
        (Urgency.CRITICAL,),
        RoutingTeam.WATER_SERVICES,
        "Critical escalation when water is near electrical infrastructure.",
        (Status.ESCALATED,),
    ),
    DraftExtractionCase(
        "The corridor light outside my unit has been flickering for 3 days.",
        Category.LIGHTING_FAULT,
        (Urgency.MEDIUM,),
        RoutingTeam.ESTATE_MAINTENANCE,
        "Medium estate maintenance issue without explicit hazard.",
    ),
    DraftExtractionCase(
        "My neighbour keeps blocking the corridor with bicycles and plants.",
        Category.CORRIDOR_OBSTRUCTION,
        (Urgency.MEDIUM, Urgency.HIGH),
        RoutingTeam.SAFETY_INSPECTION,
        "Taxonomy boundary between routine obstruction and access/safety risk.",
    ),
    DraftExtractionCase(
        "The playground slide is cracked and children are still using it.",
        Category.DAMAGED_FACILITY,
        (Urgency.HIGH,),
        RoutingTeam.ESTATE_MAINTENANCE,
        "Damaged public facility with children exposed to risk.",
        (Status.ESCALATED,),
    ),
    DraftExtractionCase(
        "The grass and trees near the walkway are overgrown.",
        Category.GREENERY,
        (Urgency.LOW, Urgency.MEDIUM),
        RoutingTeam.HORTICULTURE_TEAM,
        "Low/medium severity boundary for greenery not clearly blocking access.",
    ),
    DraftExtractionCase(
        "Someone keeps parking illegally near the loading bay.",
        Category.PARKING_ISSUE,
        (Urgency.MEDIUM,),
        RoutingTeam.PARKING_ENFORCEMENT,
        "Parking enforcement routing rather than estate maintenance.",
    ),
    DraftExtractionCase(
        "The void deck floor near the letterboxes is dirty and smells like spilled food.",
        Category.CLEANLINESS,
        (Urgency.MEDIUM,),
        RoutingTeam.CLEANING_TEAM,
        "Cleanliness complaint from smell and spilled food evidence.",
    ),
    DraftExtractionCase(
        "My upstairs neighbour keeps drilling loudly after midnight every night.",
        Category.NOISE,
        (Urgency.MEDIUM,),
        RoutingTeam.NEIGHBOUR_DISPUTE_TEAM,
        "Recurring late-night neighbour noise without estate defect.",
    ),
    DraftExtractionCase(
        "asdfasdf lol test ticket!!!",
        Category.UNCLEAR,
        (Urgency.LOW, Urgency.UNCLEAR),
        RoutingTeam.UNCLEAR,
        "Non-actionable/test input should not become an invented ticket.",
        (Status.CLOSED,),
        ("non_actionable_input",),
    ),
]
