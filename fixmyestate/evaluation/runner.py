from __future__ import annotations

from typing import Any
from fixmyestate.evaluation.cases import FINAL_TICKET_CASES, FOLLOW_UP_REVIEW_CASES
from fixmyestate.evaluation.draft_cases import DRAFT_EXTRACTION_CASES
from fixmyestate.extractor import TicketWorkflow
from fixmyestate.followups import filter_follow_up_questions
from fixmyestate.policy import enum_value


def _optional_status_match(actual: Any, expected: tuple[Any, ...]) -> bool:
    return not expected or actual in expected


def _optional_risk_flag_match(actual_flags: list[str], expected_flags: tuple[str, ...]) -> bool:
    if not expected_flags:
        return True
    normalized_actual = {flag.strip().lower() for flag in actual_flags}
    return all(flag.strip().lower() in normalized_actual for flag in expected_flags)


def run_draft_extraction_eval(workflow: TicketWorkflow, progress_bar=None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(DRAFT_EXTRACTION_CASES)
    for index, case in enumerate(DRAFT_EXTRACTION_CASES, start=1):
        if progress_bar:
            progress_bar.progress(index / total, text=f"Running Draft Extraction: {index}/{total}")
        try:
            ticket = workflow.extract_ticket(case.complaint)
            category_match = ticket.category == case.expected_category
            urgency_match = ticket.urgency in case.expected_urgencies
            routing_match = ticket.routing_team == case.expected_routing
            status_match = _optional_status_match(ticket.status, case.expected_statuses)
            risk_flag_match = _optional_risk_flag_match(ticket.risk_flags, case.expected_risk_flags)
            rows.append(
                {
                    "Case": index,
                    "Focus": case.focus,
                    "Complaint": case.complaint,
                    "Expected Category": enum_value(case.expected_category),
                    "Predicted Category": enum_value(ticket.category),
                    "Expected Urgency": "/".join(enum_value(value) for value in case.expected_urgencies),
                    "Predicted Urgency": enum_value(ticket.urgency),
                    "Expected Routing": enum_value(case.expected_routing),
                    "Predicted Routing": enum_value(ticket.routing_team),
                    "Expected Status": "/".join(enum_value(value) for value in case.expected_statuses),
                    "Predicted Status": enum_value(ticket.status),
                    "Required Risk Flags": ", ".join(case.expected_risk_flags),
                    "Predicted Risk Flags": ", ".join(ticket.risk_flags),
                    "Category Match": category_match,
                    "Urgency Match": urgency_match,
                    "Routing Match": routing_match,
                    "Status Match": status_match,
                    "Risk Flag Match": risk_flag_match,
                    "Operational Checks Match": status_match and risk_flag_match,
                    "Exact Label Match": category_match and urgency_match and routing_match,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "Case": index,
                    "Focus": case.focus,
                    "Complaint": case.complaint,
                    "Expected Category": enum_value(case.expected_category),
                    "Predicted Category": "error",
                    "Expected Urgency": "/".join(enum_value(value) for value in case.expected_urgencies),
                    "Predicted Urgency": "error",
                    "Expected Routing": enum_value(case.expected_routing),
                    "Predicted Routing": "error",
                    "Expected Status": "/".join(enum_value(value) for value in case.expected_statuses),
                    "Predicted Status": "error",
                    "Required Risk Flags": ", ".join(case.expected_risk_flags),
                    "Predicted Risk Flags": "error",
                    "Category Match": False,
                    "Urgency Match": False,
                    "Routing Match": False,
                    "Status Match": False,
                    "Risk Flag Match": False,
                    "Operational Checks Match": False,
                    "Exact Label Match": False,
                    "Error": str(exc),
                }
            )
    return rows


def run_follow_up_question_review(workflow: TicketWorkflow, progress_bar=None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(FOLLOW_UP_REVIEW_CASES)
    for index, case in enumerate(FOLLOW_UP_REVIEW_CASES, start=1):
        if progress_bar:
            progress_bar.progress(index / total, text=f"Running Follow-up Questions Review: {index}/{total}")
        try:
            ticket = workflow.extract_ticket(case.complaint)
            questions = ticket.suggested_follow_up_questions
            visible_questions = filter_follow_up_questions(questions)
            judgement = workflow.judge_follow_up_questions(case.complaint, visible_questions, case.review_focus)
            rows.append(
                {
                    "Case": index,
                    "Complaint": case.complaint,
                    "Generated Questions": "\n".join(visible_questions) if visible_questions else "(none)",
                    "Question Count": len(visible_questions),
                    "Review Target": case.review_focus,
                    "Judge Rating": judgement.rating,
                    "Judge Rationale": judgement.rationale,
                    "Suggested Improvement": judgement.suggested_improvement,
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "Case": index,
                    "Complaint": case.complaint,
                    "Generated Questions": f"error: {exc}",
                    "Question Count": 0,
                    "Review Target": case.review_focus,
                    "Judge Rating": "error",
                    "Judge Rationale": str(exc),
                    "Suggested Improvement": "",
                }
            )
    return rows


def run_final_ticket_eval(workflow: TicketWorkflow, progress_bar=None) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    total = len(FINAL_TICKET_CASES)
    for index, case in enumerate(FINAL_TICKET_CASES, start=1):
        if progress_bar:
            progress_bar.progress(index / total, text=f"Running Final Ticket Verification: {index}/{total}")
        try:
            draft = workflow.extract_ticket(case.complaint)
            final = workflow.finalize_ticket(case.complaint, draft, dict(case.answers))
            category_match = final.category == case.expected_category
            urgency_match = final.urgency in case.expected_urgencies
            routing_match = final.routing_team == case.expected_routing
            status_match = _optional_status_match(final.status, case.expected_statuses)
            risk_flag_match = _optional_risk_flag_match(final.risk_flags, case.expected_risk_flags)
            pass_case = category_match and urgency_match and routing_match
            rows.append(
                {
                    "Case": index,
                    "Name": case.name,
                    "Focus": case.focus,
                    "Complaint": case.complaint,
                    "Clarification": " | ".join(case.answers.values()),
                    "Expected Category": enum_value(case.expected_category),
                    "Final Category": enum_value(final.category),
                    "Expected Urgency": "/".join(enum_value(value) for value in case.expected_urgencies),
                    "Final Urgency": enum_value(final.urgency),
                    "Expected Routing": enum_value(case.expected_routing),
                    "Final Routing": enum_value(final.routing_team),
                    "Expected Status": "/".join(enum_value(value) for value in case.expected_statuses),
                    "Final Status": enum_value(final.status),
                    "Required Risk Flags": ", ".join(case.expected_risk_flags),
                    "Final Risk Flags": ", ".join(final.risk_flags),
                    "Category Match": category_match,
                    "Urgency Match": urgency_match,
                    "Routing Match": routing_match,
                    "Status Match": status_match,
                    "Risk Flag Match": risk_flag_match,
                    "Operational Checks Match": status_match and risk_flag_match,
                    "All Expected Fields Match": pass_case,
                    "Evaluation Result": "All fields match" if pass_case else "Needs review",
                }
            )
        except Exception as exc:
            rows.append(
                {
                    "Case": index,
                    "Name": case.name,
                    "Focus": case.focus,
                    "Complaint": case.complaint,
                    "Clarification": " | ".join(case.answers.values()),
                    "Expected Category": enum_value(case.expected_category),
                    "Final Category": "error",
                    "Expected Urgency": "/".join(enum_value(value) for value in case.expected_urgencies),
                    "Final Urgency": "error",
                    "Expected Routing": enum_value(case.expected_routing),
                    "Final Routing": "error",
                    "Expected Status": "/".join(enum_value(value) for value in case.expected_statuses),
                    "Final Status": "error",
                    "Required Risk Flags": ", ".join(case.expected_risk_flags),
                    "Final Risk Flags": "error",
                    "Category Match": False,
                    "Urgency Match": False,
                    "Routing Match": False,
                    "Status Match": False,
                    "Risk Flag Match": False,
                    "Operational Checks Match": False,
                    "All Expected Fields Match": False,
                    "Evaluation Result": "Error",
                    "Error": str(exc),
                }
            )
    return rows


def count_passes(rows: list[dict[str, Any]], key: str) -> tuple[int, int]:
    return sum(1 for row in rows if row.get(key)), len(rows)


def estimated_llm_calls() -> dict[str, int]:
    """Approximate live model calls for each evaluation layer."""
    draft_calls = len(DRAFT_EXTRACTION_CASES) * 2
    follow_up_calls = len(FOLLOW_UP_REVIEW_CASES) * 3
    final_calls = len(FINAL_TICKET_CASES) * 3
    return {
        "Draft": draft_calls,
        "Follow-up": follow_up_calls,
        "Final": final_calls,
        "Total": draft_calls + follow_up_calls + final_calls,
    }
