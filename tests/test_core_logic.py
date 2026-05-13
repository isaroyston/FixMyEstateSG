from __future__ import annotations

import pytest
from pydantic import ValidationError

from fixmyestate.evaluation import (
    estimated_llm_calls,
    run_draft_extraction_eval,
    run_final_ticket_eval,
    run_follow_up_question_review,
)
from fixmyestate.evaluation.cases import FINAL_TICKET_CASES
from fixmyestate.evaluation.draft_cases import DRAFT_EXTRACTION_CASES
from fixmyestate.extractor import FollowUpJudgement, FollowUpPlan, get_workflow
from fixmyestate.followups import filter_follow_up_questions
from fixmyestate.models import Category, Location, RoutingTeam, Ticket, Urgency
from fixmyestate.policy import ROUTING_BY_CATEGORY, apply_ticket_guardrails, display_location, unique_nonempty_text
from fixmyestate.prompts import POLICY_PROMPT


class StaticWorkflow:
    """Tiny test double for evaluator tests; product code has no alternate extraction path."""

    def extract_ticket(self, complaint: str) -> Ticket:
        for case in DRAFT_EXTRACTION_CASES:
            if complaint == case.complaint:
                return apply_ticket_guardrails(
                    Ticket(
                        category=case.expected_category,
                        urgency=case.expected_urgencies[0],
                        issue_summary=complaint,
                        risk_flags=list(case.expected_risk_flags),
                        suggested_follow_up_questions=["Are there exposed wires or sparks near the issue?"],
                    )
                )
        return apply_ticket_guardrails(
            Ticket(issue_summary=complaint, suggested_follow_up_questions=["Are there exposed wires or sparks near the issue?"])
        )

    def finalize_ticket(self, complaint: str, draft: Ticket, follow_up_answers: dict[str, str]) -> Ticket:
        for case in FINAL_TICKET_CASES:
            if complaint == case.complaint and dict(case.answers) == follow_up_answers:
                return apply_ticket_guardrails(
                    Ticket(
                        category=case.expected_category,
                        urgency=case.expected_urgencies[0],
                        issue_summary=complaint,
                        risk_flags=list(case.expected_risk_flags),
                        follow_up_answers=follow_up_answers,
                    )
                )
        return apply_ticket_guardrails(draft)

    def judge_follow_up_questions(
        self,
        complaint: str,
        generated_questions: list[str],
        review_focus: str,
    ) -> FollowUpJudgement:
        return FollowUpJudgement(
            rating="strong",
            rationale="The questions are relevant and non-duplicative.",
            suggested_improvement="",
        )


def test_schema_rejects_invalid_enum_value() -> None:
    with pytest.raises(ValidationError):
        Ticket.model_validate({"category": "not_a_category"})


def test_schema_accepts_nulls_for_missing_model_fields() -> None:
    ticket = Ticket.model_validate(
        {
            "ticket_id": None,
            "ticket_title": None,
            "reported_datetime": None,
            "category": None,
            "urgency": None,
            "routing_team": None,
            "location": None,
            "issue_summary": None,
            "affected_groups": None,
            "risk_flags": None,
            "recurrence": None,
            "missing_details": None,
            "suggested_follow_up_questions": None,
            "follow_up_answers": None,
            "evidence_quotes": None,
            "confidence": None,
            "status": None,
        }
    )

    assert ticket.category == Category.UNCLEAR
    assert ticket.affected_groups == []
    assert ticket.follow_up_answers == {}


def test_schema_tolerates_common_llm_shape_mistakes() -> None:
    ticket = Ticket.model_validate(
        {
            "follow_up_answers": [],
            "location": [],
            "confidence": [],
            "risk_flags": "sharp debris",
            "missing_details": "usable location",
        }
    )

    assert ticket.follow_up_answers == {}
    assert ticket.location == Location()
    assert ticket.risk_flags == ["sharp debris"]
    assert ticket.missing_details == ["usable location"]


def test_schema_normalizes_common_llm_enum_aliases() -> None:
    ticket = Ticket.model_validate(
        {
            "category": "lighting",
            "urgency": "high priority",
            "routing_team": "maintenance",
            "recurrence": "repeated",
            "status": "escalate",
        }
    )

    assert ticket.category == Category.LIGHTING_FAULT
    assert ticket.urgency == Urgency.HIGH
    assert ticket.routing_team == RoutingTeam.ESTATE_MAINTENANCE
    assert ticket.recurrence.value == "recurring"
    assert ticket.status.value == "escalated"


def test_schema_treats_duration_recurrence_values_as_unknown() -> None:
    ticket = Ticket.model_validate({"recurrence": "1_day"})

    assert ticket.recurrence.value == "unknown"


def test_follow_up_plan_tolerates_string_values() -> None:
    plan = FollowUpPlan.model_validate(
        {
            "missing_details": "usable location",
            "suggested_follow_up_questions": "Which block is affected?",
        }
    )

    assert plan.missing_details == ["usable location"]
    assert plan.suggested_follow_up_questions == ["Which block is affected?"]


def test_overlapping_follow_up_questions_are_filtered() -> None:
    questions = filter_follow_up_questions(
        [
            "Please provide the block number or specific location of the broken light.",
            "How long has the light been broken?",
            "Is the broken light causing any safety or accessibility issues?",
            "Which floor or level is the corridor light broken on?",
            "Are there exposed wires or sparks near the broken light?",
        ]
    )

    assert questions == ["Are there exposed wires or sparks near the broken light?"]


def test_guardrails_apply_routing_and_status() -> None:
    ticket = apply_ticket_guardrails(
        Ticket(
            category=Category.WATER_LEAKAGE,
            urgency=Urgency.CRITICAL,
            missing_details=["usable location"],
        )
    )

    assert ROUTING_BY_CATEGORY[Category.WATER_LEAKAGE] == RoutingTeam.WATER_SERVICES
    assert ticket.routing_team == RoutingTeam.WATER_SERVICES
    assert ticket.status.value == "escalated"
    assert len(ticket.suggested_follow_up_questions) <= 3


def test_guardrail_list_cleanup_is_per_ticket_text_cleanup_only() -> None:
    assert unique_nonempty_text(["usable location", "Usable location", "", " sharp debris "]) == [
        "usable location",
        "sharp debris",
    ]


def test_missing_critical_location_sets_needs_more_info() -> None:
    ticket = apply_ticket_guardrails(
        Ticket(category=Category.PEST, urgency=Urgency.MEDIUM, missing_details=["usable location"])
    )

    assert ticket.status.value == "needs_more_info"


def test_non_actionable_ticket_is_closed() -> None:
    ticket = apply_ticket_guardrails(
        Ticket(category=Category.UNCLEAR, urgency=Urgency.LOW, risk_flags=["non_actionable_input"])
    )

    assert ticket.routing_team == RoutingTeam.UNCLEAR
    assert ticket.status.value == "closed"


def test_policy_prompt_rejects_impossible_or_joke_locations() -> None:
    assert "Impossible or joke locations" in POLICY_PROMPT
    assert "moon" in POLICY_PROMPT
    assert "non-actionable" in POLICY_PROMPT


def test_policy_prompt_rejects_invalid_evidence_quotes() -> None:
    assert "Evidence quotes" in POLICY_PROMPT
    assert "gibberish" in POLICY_PROMPT
    assert "non-actionable evidence" in POLICY_PROMPT


def test_policy_prompt_requires_canonical_missing_detail_labels() -> None:
    assert "use these exact labels" in POLICY_PROMPT
    assert "usable location" in POLICY_PROMPT
    assert "Do not invent near-equivalent labels" in POLICY_PROMPT


def test_policy_prompt_treats_fixed_impact_answers_as_claims_to_evaluate() -> None:
    assert "Self-reported impact checks" in POLICY_PROMPT
    assert "not automatic urgency upgrades" in POLICY_PROMPT
    assert "hurt ears" in POLICY_PROMPT


def test_policy_prompt_includes_triage_priority_and_few_shot_calibration() -> None:
    assert "Triage priority order" in POLICY_PROMPT
    assert "Few-shot calibration" in POLICY_PROMPT
    assert "Water leaking near electrical riser" in POLICY_PROMPT


def test_display_location_falls_back_to_unclear() -> None:
    assert display_location(Location()) == "Unclear"


def test_get_workflow_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        get_workflow()


def test_draft_extraction_eval_compares_expected_fields() -> None:
    rows = run_draft_extraction_eval(StaticWorkflow())

    assert rows
    assert all(row["Exact Label Match"] for row in rows)


def test_follow_up_review_uses_llm_judge_fields() -> None:
    rows = run_follow_up_question_review(StaticWorkflow())

    assert rows
    assert all("Generated Questions" in row for row in rows)
    assert all(row["Judge Rating"] == "strong" for row in rows)
    assert all("Judge Rationale" in row for row in rows)


def test_final_ticket_eval_compares_expected_fields() -> None:
    rows = run_final_ticket_eval(StaticWorkflow())

    assert rows
    assert all(row["All Expected Fields Match"] for row in rows)


def test_estimated_llm_calls_reflects_current_eval_shape() -> None:
    calls = estimated_llm_calls()

    assert calls["Draft"] == len(DRAFT_EXTRACTION_CASES) * 2
    assert calls["Final"] == len(FINAL_TICKET_CASES) * 3
    assert calls["Total"] == calls["Draft"] + calls["Follow-up"] + calls["Final"]
