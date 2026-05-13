from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, Literal, Protocol

from pydantic import BaseModel, Field, ValidationError, field_validator

from .followups import filter_follow_up_questions
from .models import Ticket
from .policy import apply_ticket_guardrails
from .prompts import POLICY_PROMPT, SYSTEM_PROMPT, schema_instruction


DEFAULT_MODEL = "gpt-4.1-mini"


class TicketWorkflow(Protocol):
    def extract_ticket(self, complaint: str) -> Ticket:
        ...

    def finalize_ticket(self, complaint: str, draft: Ticket, follow_up_answers: Dict[str, str]) -> Ticket:
        ...

    def judge_follow_up_questions(
        self,
        complaint: str,
        generated_questions: list[str],
        review_focus: str,
    ) -> "FollowUpJudgement":
        ...


class FollowUpPlan(BaseModel):
    missing_details: list[str] = Field(default_factory=list)
    suggested_follow_up_questions: list[str] = Field(default_factory=list)

    @field_validator("missing_details", "suggested_follow_up_questions", mode="before")
    @classmethod
    def none_or_string_to_list(cls, value: object) -> object:
        if value is None:
            return []
        if isinstance(value, str):
            return [value]
        return value


class FollowUpJudgement(BaseModel):
    rating: Literal["strong", "medium", "weak"] = "weak"
    rationale: str = ""
    suggested_improvement: str = ""

    @field_validator("rating", mode="before")
    @classmethod
    def normalize_rating(cls, value: object) -> object:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"strong", "good", "excellent"}:
                return "strong"
            if normalized in {"medium", "fair", "okay", "ok", "acceptable"}:
                return "medium"
            if normalized in {"weak", "poor", "bad"}:
                return "weak"
        return value


def parse_json_object(text: str) -> Dict[str, Any]:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = re.sub(r"^```(?:json)?", "", cleaned, flags=re.IGNORECASE).strip()
        cleaned = re.sub(r"```$", "", cleaned).strip()
    return json.loads(cleaned)


def validate_ticket_json(content: str) -> Ticket:
    try:
        return Ticket.model_validate(parse_json_object(content))
    except (json.JSONDecodeError, ValidationError) as exc:
        raise ValueError(f"Model returned invalid ticket JSON: {exc}") from exc


class OpenAIWorkflow:
    def __init__(
        self,
        api_key: str,
        base_url: str | None = None,
        model_name: str = DEFAULT_MODEL,
    ) -> None:
        from openai import OpenAI

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        self.model_name = model_name

    def _json_call(self, user_content: str) -> str:
        response = self.client.chat.completions.create(
            model=self.model_name,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": user_content},
            ],
            temperature=0,
        )
        return response.choices[0].message.content or "{}"

    def extract_ticket(self, complaint: str) -> Ticket:
        draft = self._draft_ticket(complaint)
        plan = self._plan_follow_ups(complaint, draft)
        draft.missing_details = plan.missing_details
        draft.suggested_follow_up_questions = plan.suggested_follow_up_questions
        return apply_ticket_guardrails(draft)

    def finalize_ticket(self, complaint: str, draft: Ticket, follow_up_answers: Dict[str, str]) -> Ticket:
        clean_answers = {key: value.strip() for key, value in follow_up_answers.items() if value and value.strip()}
        content = self._json_call(
            f"""
{POLICY_PROMPT}

Finalize the ticket after reading the original complaint, the draft ticket, and the operator's
fixed-form and follow-up answers. Re-evaluate the whole ticket, including whether the complaint
is actionable at all. Treat clarification answers as evidence to judge, not as automatic labels.
If the original complaint is gibberish, trolling, abusive text without a
service request, test text, or still does not describe an identifiable estate issue, keep it
non-actionable with category "unclear", urgency "low", routing_team "unclear", and
risk_flags ["non_actionable_input"].

If the draft was non-actionable and the follow-up answers only add a block/location, timing,
or an injury/access yes-no answer without naming an estate defect or public-area hazard, keep the
final ticket non-actionable. Do not convert a personal injury into a safety_hazard unless the user
links it to an estate issue that operations can inspect or fix.

If the answers reveal estate-related hazards such as broken glass, glass shards, sharp debris,
exposed wiring, slippery floors, trapped people due to a facility fault, or accessibility impact
from a lift/obstruction/facility issue, update risk_flags, urgency, status-relevant fields,
evidence_quotes, and missing_details accordingly.

If a noise complaint has late-night recurrence plus a self-reported "injury" or "access affected"
answer, keep it as a noise ticket unless the answer explains a concrete safety threat, harassment
pattern, public-area obstruction, or estate defect. Do not escalate merely because a fixed yes/no field
was answered "Yes".

The final ticket should have no missing_details or follow-up questions for details that were answered.
Keep unanswered important gaps only. Use the canonical missing_details labels from the policy prompt;
for example, use "usable location" exactly when the supplied location is missing, gibberish, impossible,
or not actionable for operations.

{schema_instruction()}

Original complaint:
{complaint}

Draft ticket JSON:
{draft.model_dump_json()}

Follow-up answers JSON:
{json.dumps(clean_answers)}
""".strip()
        )
        ticket = validate_ticket_json(content)
        ticket.follow_up_answers.update(clean_answers)
        return apply_ticket_guardrails(ticket)

    def judge_follow_up_questions(
        self,
        complaint: str,
        generated_questions: list[str],
        review_focus: str,
    ) -> FollowUpJudgement:
        content = self._json_call(
            f"""
You are judging follow-up questions for a public-sector estate complaint triage prototype.

Rate the generated follow-up questions as:
- strong: questions are relevant, non-duplicative, operationally useful, specific to the complaint,
  and do not repeat fixed fields such as location, timing, injury, or access impact.
- medium: questions are mostly useful but include some vagueness, overlap, or missed opportunity.
- weak: questions are irrelevant, duplicative, generic, excessive, or miss the key operational gap.

The product separately asks fixed fields for detailed location, injury/trapped status, access impact,
and timing. Do not reward questions that merely repeat those fields.

Return only this JSON shape:
{{
  "rating": "strong|medium|weak",
  "rationale": "short reason",
  "suggested_improvement": "short improvement, or empty string if strong"
}}

Complaint:
{complaint}

Generated questions:
{json.dumps(generated_questions)}

Review target:
{review_focus}
""".strip()
        )
        try:
            return FollowUpJudgement.model_validate(parse_json_object(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Model returned invalid follow-up judgement JSON: {exc}") from exc

    def _draft_ticket(self, complaint: str) -> Ticket:
        content = self._json_call(
            f"""
{POLICY_PROMPT}

Fill as much of the ticket schema as possible from the complaint. Capture uncertainty explicitly.
Prioritise the operational triage fields first: actionability, category, urgency, routing-relevant
risk, usable location, affected asset/facility, safety or access impact, and timing or recurrence.
Treat descriptive enrichment as secondary.
Do not ask follow-up questions in this step.

{schema_instruction()}

Complaint:
{complaint}
""".strip()
        )
        return validate_ticket_json(content)

    def _plan_follow_ups(self, complaint: str, draft: Ticket) -> FollowUpPlan:
        content = self._json_call(
            f"""
{POLICY_PROMPT}

Given the complaint and draft ticket, identify the most important missing operational details.
The UI always asks these fixed fields separately:
- "Please describe the incident location in as much detail as possible."
- "Is anyone injured or trapped?"
- "Is access affected for residents or vulnerable users?"
- "When did this issue start?"

Do not spend one of your 3 questions on general location, exact location, block, street,
estate, town, postal code, floor, level, corridor, lobby, unit, area, injury/trapped yes-no,
access affected yes-no, or basic timing. Generate at most 3 custom follow-up questions only
for important details not covered by these fixed fields.
Prefer 1 useful custom question for thin but actionable complaints when it would materially improve
dispatch, escalation, or officer safety. Use 2-3 only when separate high-value gaps remain.
Return no questions only when the complaint plus fixed fields would already be enough for dispatch.
Ask nothing that is already answered in the draft.
Do not ask "How long has this been happening?", "When was this first noticed?", "Which block?",
"Which floor or level?", "Which corridor/lobby/area?", "What is the specific location?",
or generic "Is this causing safety/accessibility issues?" because the fixed controls already
collect those answers.

Use this internal checklist before choosing questions, but do not output the checklist:
1. Location, injury/trapped, access impact, and timing will be collected separately.
2. Is there a specific asset, facility, lift, lobby, pipe, light, playground item, or vehicle detail
   that the operator still needs?
3. Is there a complaint-specific hazard detail not captured by the fixed fields?
4. Can one question retrieve multiple related details without becoming confusing?

Good custom question examples by issue type:
- Lighting: "Are there exposed wires, sparks, broken glass, or sharp debris around the faulty light?"
- Lift: "Is another lift still usable for residents while this lift is down?"
- Water leakage: "Is the leak near electrical fittings, causing flooding, or making the floor slippery?"
- Pest: "Roughly how many pests were seen and are they entering homes or shared facilities?"
- Corridor obstruction: "Does the item block the main walking path, fire escape route, or wheelchair passage?"
- Damaged facility: "Is the damaged part loose, sharp, unstable, or still being used by residents?"
- Cleanliness or smell: "Is there visible waste, spill, vomit, stagnant water, or another source of the smell?"

Return only this JSON shape:
{{
  "missing_details": ["..."],
  "suggested_follow_up_questions": ["..."]
}}

Complaint:
{complaint}

Draft ticket JSON:
{draft.model_dump_json()}
""".strip()
        )
        try:
            plan = FollowUpPlan.model_validate(parse_json_object(content))
        except (json.JSONDecodeError, ValidationError) as exc:
            raise ValueError(f"Model returned invalid follow-up plan JSON: {exc}") from exc
        plan.suggested_follow_up_questions = filter_follow_up_questions(plan.suggested_follow_up_questions)
        return plan


def get_workflow() -> TicketWorkflow:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY is required for ticket extraction.")
    return OpenAIWorkflow(
        api_key=api_key,
        base_url=os.getenv("OPENAI_BASE_URL") or None,
        model_name=os.getenv("MODEL_NAME", DEFAULT_MODEL),
    )


def get_extractor() -> TicketWorkflow:
    return get_workflow()


def api_key_configured() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))
