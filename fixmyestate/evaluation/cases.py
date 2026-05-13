from __future__ import annotations

from dataclasses import dataclass

from fixmyestate.models import Category, RoutingTeam, Status, Urgency


@dataclass(frozen=True)
class FollowUpReviewCase:
    complaint: str
    review_focus: str


@dataclass(frozen=True)
class FinalTicketCase:
    name: str
    complaint: str
    answers: dict[str, str]
    expected_category: Category
    expected_urgencies: tuple[Urgency, ...]
    expected_routing: RoutingTeam
    focus: str = ""
    expected_statuses: tuple[Status, ...] = ()
    expected_risk_flags: tuple[str, ...] = ()


FIXED_LOCATION_QUESTION = "Please describe the incident location in as much detail as possible."
FIXED_INJURY_QUESTION = "Is anyone injured or trapped?"
FIXED_ACCESS_QUESTION = "Is access affected for residents or vulnerable users?"
FIXED_TIMING_QUESTION = "When did this issue start?"
ADDITIONAL_CLARIFICATION = "Additional clarification"


FOLLOW_UP_REVIEW_CASES = [
    FollowUpReviewCase(
        complaint="The light along the corridor of my floor is broken.",
        review_focus=(
            "Good questions should avoid block/floor/timing duplication and only ask for a "
            "complaint-specific hazard, such as exposed wiring, sparks, or broken glass."
        ),
    ),
    FollowUpReviewCase(
        complaint="The lift at Block 54 is not working.",
        review_focus=(
            "Good questions should avoid asking for general location because the fixed location "
            "field captures it. A useful custom question may ask whether another lift remains usable."
        ),
    ),
    FollowUpReviewCase(
        complaint="There is water leaking from the ceiling near the walkway.",
        review_focus=(
            "Good questions should ask about leak-specific risks, such as electrical fittings, "
            "slippery floors, or flooding, not generic safety wording."
        ),
    ),
    FollowUpReviewCase(
        complaint="There are rats near the rubbish chute at my block.",
        review_focus=(
            "It is acceptable to ask no extra questions if the fixed location field is enough for "
            "operations to inspect the site."
        ),
    ),
    FollowUpReviewCase(
        complaint="Someone left bulky furniture along the common corridor.",
        review_focus=(
            "Good questions should avoid asking for location and instead probe whether the obstruction "
            "blocks evacuation, wheelchair access, or the main walking path."
        ),
    ),
    FollowUpReviewCase(
        complaint="The playground swing looks loose and children are still playing there.",
        review_focus=(
            "Good questions should ask about facility-specific risk, such as whether the swing is detached, "
            "sharp, unstable, or already cordoned off."
        ),
    ),
    FollowUpReviewCase(
        complaint="The void deck smells very bad near the letterboxes.",
        review_focus=(
            "Good questions should ask about cleanliness-specific evidence, such as spill, waste, vomit, "
            "or stagnant water, without duplicating timing or location."
        ),
    ),
    FollowUpReviewCase(
        complaint="asdfasdf lol test ticket!!!",
        review_focus=(
            "Good output should usually ask no extra follow-up questions because the input is non-actionable."
        ),
    ),
]


FINAL_TICKET_CASES = [
    FinalTicketCase(
        name="Lighting fault without hazard stays medium",
        complaint="The light at my block is broken.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 54 Choa Chu Kang corridor level 8",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Today",
            ADDITIONAL_CLARIFICATION: "No glass, no exposed wires, just dark.",
        },
        expected_category=Category.LIGHTING_FAULT,
        expected_urgencies=(Urgency.MEDIUM,),
        expected_routing=RoutingTeam.ESTATE_MAINTENANCE,
        focus="Finalisation should not over-escalate a lighting fault when hazard checks are negative.",
    ),
    FinalTicketCase(
        name="Lighting fault with glass upgrades to high",
        complaint="The light at my block is broken.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 54 Choa Chu Kang corridor level 8",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Today",
            ADDITIONAL_CLARIFICATION: "The cover broke and there are glass shards everywhere.",
        },
        expected_category=Category.LIGHTING_FAULT,
        expected_urgencies=(Urgency.HIGH,),
        expected_routing=RoutingTeam.ESTATE_MAINTENANCE,
        focus="Same base complaint should escalate when clarification reveals sharp glass.",
        expected_statuses=(Status.ESCALATED,),
    ),
    FinalTicketCase(
        name="Lift fault with wheelchair access impact upgrades to high",
        complaint="The lift at my block is not working.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 123 Tampines lift lobby A",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "Yes",
            FIXED_TIMING_QUESTION: "1-3 days ago",
            ADDITIONAL_CLARIFICATION: "My mother uses a wheelchair and cannot go downstairs.",
        },
        expected_category=Category.LIFT_FAULT,
        expected_urgencies=(Urgency.HIGH,),
        expected_routing=RoutingTeam.ESTATE_MAINTENANCE,
        focus="Fixed access answer must be tied to a concrete estate facility fault before escalation.",
        expected_statuses=(Status.ESCALATED,),
    ),
    FinalTicketCase(
        name="Water leak near electrical riser is critical",
        complaint="Water is leaking at the corridor.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 88 Bedok level 8 beside the electrical riser",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Just now",
            ADDITIONAL_CLARIFICATION: "The water is flowing near electrical fittings.",
        },
        expected_category=Category.WATER_LEAKAGE,
        expected_urgencies=(Urgency.CRITICAL,),
        expected_routing=RoutingTeam.WATER_SERVICES,
        focus="Clarification can upgrade a vague leak into an electrical-risk critical case.",
        expected_statuses=(Status.ESCALATED,),
    ),
    FinalTicketCase(
        name="Pest report remains medium after location clarification",
        complaint="There are rats near the rubbish chute.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 55 Bedok rubbish chute at level 3",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "More than 3 days ago",
            ADDITIONAL_CLARIFICATION: "Residents saw two rats near the chute area.",
        },
        expected_category=Category.PEST,
        expected_urgencies=(Urgency.MEDIUM,),
        expected_routing=RoutingTeam.PEST_CONTROL,
        focus="Location clarification should preserve routine pest-control routing.",
    ),
    FinalTicketCase(
        name="Corridor obstruction affecting wheelchair access is high",
        complaint="Someone left bulky items along the corridor.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 12 Yishun level 5 corridor outside unit 05-120",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "Yes",
            FIXED_TIMING_QUESTION: "Today",
            ADDITIONAL_CLARIFICATION: "The sofa blocks most of the corridor and wheelchair users cannot pass.",
        },
        expected_category=Category.CORRIDOR_OBSTRUCTION,
        expected_urgencies=(Urgency.HIGH,),
        expected_routing=RoutingTeam.SAFETY_INSPECTION,
        focus="Physical wheelchair blockage should escalate even if nobody is injured.",
        expected_statuses=(Status.ESCALATED,),
    ),
    FinalTicketCase(
        name="Dirty void deck remains medium",
        complaint="The void deck smells bad and the floor is dirty.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 21 Ang Mo Kio void deck beside the letterboxes",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "1-3 days ago",
            ADDITIONAL_CLARIFICATION: "There is spilled food and rubbish on the floor.",
        },
        expected_category=Category.CLEANLINESS,
        expected_urgencies=(Urgency.MEDIUM,),
        expected_routing=RoutingTeam.CLEANING_TEAM,
        focus="Bad smell plus visible food/rubbish should stay a cleaning issue, not a vague hazard.",
    ),
    FinalTicketCase(
        name="Loose playground swing with children nearby is high",
        complaint="The playground swing looks loose.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 310 Jurong West playground near the fitness corner",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Today",
            ADDITIONAL_CLARIFICATION: "The chain is partly detached and children are still using it.",
        },
        expected_category=Category.DAMAGED_FACILITY,
        expected_urgencies=(Urgency.HIGH,),
        expected_routing=RoutingTeam.ESTATE_MAINTENANCE,
        focus="Damaged public facility still being used should become high priority.",
        expected_statuses=(Status.ESCALATED,),
    ),
    FinalTicketCase(
        name="Overgrown greenery near walkway is low or medium",
        complaint="The bushes near the walkway are overgrown.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 44 Sengkang walkway between the lift lobby and carpark",
            FIXED_INJURY_QUESTION: "No",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "More than 3 days ago",
            ADDITIONAL_CLARIFICATION: "The bushes are messy but not blocking the path.",
        },
        expected_category=Category.GREENERY,
        expected_urgencies=(Urgency.LOW, Urgency.MEDIUM),
        expected_routing=RoutingTeam.HORTICULTURE_TEAM,
        focus="Greenery not blocking the path is a low/medium boundary case.",
    ),
    FinalTicketCase(
        name="Gibberish input becomes non-actionable",
        complaint="asdfasdf lol test ticket!!!",
        answers={
            FIXED_LOCATION_QUESTION: "Not sure",
            FIXED_INJURY_QUESTION: "Not sure",
            FIXED_ACCESS_QUESTION: "Not sure",
            FIXED_TIMING_QUESTION: "Not sure",
            ADDITIONAL_CLARIFICATION: "This was just a test and not an estate issue.",
        },
        expected_category=Category.UNCLEAR,
        expected_urgencies=(Urgency.LOW, Urgency.UNCLEAR),
        expected_routing=RoutingTeam.UNCLEAR,
        focus="Test/gibberish input should stay closed even after clarification fields are filled.",
        expected_statuses=(Status.CLOSED,),
        expected_risk_flags=("non_actionable_input",),
    ),
    FinalTicketCase(
        name="Noise complaint with unsupported injury claim stays medium",
        complaint="My neighbour keeps making noise from 1am to 6am.",
        answers={
            FIXED_LOCATION_QUESTION: "Tower A Novena Velocity Office Towers level 17",
            FIXED_INJURY_QUESTION: "Yes",
            FIXED_ACCESS_QUESTION: "Yes",
            FIXED_TIMING_QUESTION: "Recurring issue",
            ADDITIONAL_CLARIFICATION: "The noise hurt my ears, but there is no obstruction or estate defect.",
        },
        expected_category=Category.NOISE,
        expected_urgencies=(Urgency.MEDIUM,),
        expected_routing=RoutingTeam.NEIGHBOUR_DISPUTE_TEAM,
        focus="Unsupported injury/access claims should not upgrade a noise complaint.",
    ),
    FinalTicketCase(
        name="Personal injury without estate cause stays non-actionable",
        complaint="I stubbed my toe.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 54",
            FIXED_INJURY_QUESTION: "Yes",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Just now",
            ADDITIONAL_CLARIFICATION: "I just stubbed my toe. There is no broken tile, obstruction, or estate defect.",
        },
        expected_category=Category.UNCLEAR,
        expected_urgencies=(Urgency.LOW, Urgency.UNCLEAR),
        expected_routing=RoutingTeam.UNCLEAR,
        focus="Personal injury without an estate cause should not become a municipal defect ticket.",
        expected_statuses=(Status.CLOSED,),
        expected_risk_flags=("non_actionable_input",),
    ),
    FinalTicketCase(
        name="Injury caused by broken public-area tile is critical",
        complaint="I tripped at the void deck.",
        answers={
            FIXED_LOCATION_QUESTION: "Blk 54 void deck beside the letterboxes",
            FIXED_INJURY_QUESTION: "Yes",
            FIXED_ACCESS_QUESTION: "No",
            FIXED_TIMING_QUESTION: "Just now",
            ADDITIONAL_CLARIFICATION: "A broken floor tile caused me to trip and cut my foot.",
        },
        expected_category=Category.SAFETY_HAZARD,
        expected_urgencies=(Urgency.CRITICAL,),
        expected_routing=RoutingTeam.SAFETY_INSPECTION,
        focus="Personal injury becomes actionable only when tied to a public-area estate hazard.",
        expected_statuses=(Status.ESCALATED,),
    ),
]
