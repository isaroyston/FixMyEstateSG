from __future__ import annotations

from html import escape
from time import perf_counter
from typing import Any, Dict, List

import streamlit as st

from fixmyestate.evaluation import (
    count_passes,
    estimated_llm_calls,
    run_draft_extraction_eval,
    run_final_ticket_eval,
    run_follow_up_question_review,
)
from fixmyestate.extractor import api_key_configured, get_extractor
from fixmyestate.followups import filter_follow_up_questions
from fixmyestate.models import Ticket
from fixmyestate.policy import display_location, enum_value


st.set_page_config(page_title="FixMyEstate SG", layout="wide")

LOCATION_QUESTION = "Please describe the incident location in as much detail as possible. Example: e.g. Blk 73 Woodlands Street 689102 Lift Lobby A"
LOCATION_PLACEHOLDER = "e.g. Blk 73 Woodlands Street 689102 Lift Lobby A"
INJURY_QUESTION = "Is anyone injured or trapped?"
ACCESS_QUESTION = "Is access affected for residents or vulnerable users?"
TIMING_QUESTION = "When did this issue start?"

INJURY_OPTIONS = ["Not sure", "No", "Yes"]
ACCESS_OPTIONS = ["Not sure", "No", "Yes"]
TIMING_OPTIONS = ["Not sure", "Just now", "Today", "1-3 days ago", "More than 3 days ago", "Recurring issue"]


st.markdown(
    """
    <style>
      .main .block-container { padding-top: 1.5rem; max-width: 1180px; }
      h1, h2, h3 { letter-spacing: 0; }
      .ticket-section {
        border: 1px solid var(--primary-color, #e5e7eb);
        border-radius: 8px;
        padding: 16px;
        background: transparent;
        margin: 12px 0;
      }
      .field-label { color: var(--text-color); opacity: 0.7; font-size: 0.86rem; margin-bottom: 2px; }
      .field-value { color: var(--text-color); font-weight: 600; margin-bottom: 10px; }
      .indicator {
        display: inline-block;
        width: 0.68rem;
        height: 0.68rem;
        border-radius: 999px;
        margin-right: 0.4rem;
        vertical-align: middle;
      }
      .indicator-green { background: #16a34a; }
      .indicator-orange { background: #f97316; }
      .indicator-red { background: #dc2626; }
      .queue-row {
        border-bottom: 1px solid var(--secondary-background-color, #f3f4f6);
        padding: 0.45rem 0;
        color: var(--text-color);
      }
      .queue-meta { color: var(--text-color); opacity: 0.7; font-size: 0.9rem; margin-left: 0.4rem; }
      .json-scroll {
        max-height: 360px;
        overflow: auto;
        border: 1px solid var(--primary-color, #e5e7eb);
        border-radius: 8px;
        background: var(--secondary-background-color, #f9fafb);
        padding: 0.75rem;
        font-size: 0.82rem;
        line-height: 1.35;
        white-space: pre;
      }
    </style>
    """,
    unsafe_allow_html=True,
)


def init_state() -> None:
    st.session_state.setdefault("tickets", [])
    st.session_state.setdefault("draft_ticket", None)
    st.session_state.setdefault("draft_complaint", "")
    st.session_state.setdefault("last_created_ticket", None)


def indicator_class(ticket: Ticket) -> str:
    if enum_value(ticket.urgency) in {"high", "critical"} or enum_value(ticket.status) == "escalated":
        return "indicator-red"
    if enum_value(ticket.status) == "needs_more_info" or enum_value(ticket.urgency) in {"medium", "unclear"}:
        return "indicator-orange"
    return "indicator-green"


def indicator_label(ticket: Ticket) -> str:
    if indicator_class(ticket) == "indicator-red":
        return "High attention"
    if indicator_class(ticket) == "indicator-orange":
        return "Needs review"
    return "Routine"


def as_table_row(ticket: Ticket) -> Dict[str, str]:
    return {
        "Signal": indicator_label(ticket),
        "Ticket ID": ticket.ticket_id,
        "Title": ticket.ticket_title,
        "Category": enum_value(ticket.category),
        "Urgency": enum_value(ticket.urgency),
        "Routing Team": enum_value(ticket.routing_team),
        "Location": display_location(ticket.location),
        "Status": enum_value(ticket.status),
    }


def render_list(label: str, values: List[str]) -> None:
    st.markdown(f"**{label}**")
    if values:
        for value in values:
            st.write(f"- {value}")
    else:
        st.caption("None")


def render_queue_signal(ticket: Ticket) -> None:
    title = escape(ticket.ticket_title)
    ticket_id = escape(ticket.ticket_id)
    urgency = escape(enum_value(ticket.urgency))
    status = escape(enum_value(ticket.status))
    location = escape(display_location(ticket.location))
    signal_class = indicator_class(ticket)
    st.markdown(
        (
            f'<div class="queue-row"><span class="indicator {signal_class}"></span>'
            f"<strong>{ticket_id}</strong> {title}"
            f'<span class="queue-meta">{urgency} &middot; {status} &middot; {location}</span></div>'
        ),
        unsafe_allow_html=True,
    )


def render_ticket_card(ticket: Ticket) -> None:
    title = escape(ticket.ticket_title)
    category = escape(enum_value(ticket.category))
    urgency = escape(enum_value(ticket.urgency))
    routing_team = escape(enum_value(ticket.routing_team))
    location = escape(display_location(ticket.location))
    status = escape(enum_value(ticket.status))
    signal = escape(indicator_label(ticket))
    signal_class = indicator_class(ticket)

    st.markdown('<div class="ticket-section">', unsafe_allow_html=True)
    col1, col2, col3 = st.columns(3)
    with col1:
        st.markdown('<div class="field-label">Ticket title</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{title}</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-label">Category</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{category}</div>', unsafe_allow_html=True)
    with col2:
        st.markdown('<div class="field-label">Urgency</div>', unsafe_allow_html=True)
        st.markdown(
            f'<div class="field-value"><span class="indicator {signal_class}"></span>{urgency} &middot; {signal}</div>',
            unsafe_allow_html=True,
        )
        st.markdown('<div class="field-label">Routing team</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{routing_team}</div>', unsafe_allow_html=True)
    with col3:
        st.markdown('<div class="field-label">Location</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{location}</div>', unsafe_allow_html=True)
        st.markdown('<div class="field-label">Status</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="field-value">{status}</div>', unsafe_allow_html=True)

    st.markdown("**Issue summary**")
    st.write(ticket.issue_summary or "No summary available.")
    st.markdown("</div>", unsafe_allow_html=True)


def render_created_ticket_feedback(ticket: Ticket) -> None:
    ticket_id = escape(ticket.ticket_id)
    title = escape(ticket.ticket_title)
    signal = escape(indicator_label(ticket))
    signal_class = indicator_class(ticket)
    urgency = escape(enum_value(ticket.urgency))
    status = escape(enum_value(ticket.status))
    routing_team = escape(enum_value(ticket.routing_team))
    location = escape(display_location(ticket.location))

    st.markdown(
        (
            '<div class="ticket-section">'
            f'<div class="field-value"><span class="indicator {signal_class}"></span>'
            f"Created {ticket_id} &middot; {signal}</div>"
            f"<div><strong>{title}</strong></div>"
            f'<div class="queue-meta">{urgency} &middot; {status} &middot; {routing_team} &middot; {location}</div>'
            "</div>"
        ),
        unsafe_allow_html=True,
    )


def render_ticket_json(ticket: Ticket) -> None:
    payload = escape(ticket.model_dump_json(indent=2))
    st.markdown(f'<pre class="json-scroll">{payload}</pre>', unsafe_allow_html=True)


def run_all_evaluations() -> None:
    extractor = get_extractor()
    runtimes: dict[str, float] = {}

    progress_bar = st.progress(0, text="Starting Evaluation Pipeline...")

    started = perf_counter()
    st.session_state.draft_eval_results = run_draft_extraction_eval(extractor, progress_bar)
    runtimes["Draft"] = perf_counter() - started

    started = perf_counter()
    st.session_state.follow_up_review_results = run_follow_up_question_review(extractor, progress_bar)
    runtimes["Follow-up"] = perf_counter() - started

    started = perf_counter()
    st.session_state.final_eval_results = run_final_ticket_eval(extractor, progress_bar)
    runtimes["Final"] = perf_counter() - started
    
    progress_bar.empty()
    
    runtimes["Total"] = sum(runtimes.values())
    st.session_state.eval_runtimes = runtimes


def run_single_evaluation(name: str, session_key: str, runner: Any) -> None:
    progress_bar = st.progress(0, text=f"Running {name}...")
    started = perf_counter()
    st.session_state[session_key] = runner(get_extractor(), progress_bar)
    progress_bar.empty()
    runtimes = dict(st.session_state.get("eval_runtimes", {}))
    runtimes[name] = perf_counter() - started
    runtimes["Total"] = sum(value for key, value in runtimes.items() if key != "Total")
    st.session_state.eval_runtimes = runtimes


def render_runtime_metric(label: str, runtime_key: str) -> None:
    runtimes = st.session_state.get("eval_runtimes", {})
    runtime = runtimes.get(runtime_key)
    st.metric(label, "not run" if runtime is None else f"{runtime:.2f}s")


def evaluation_count(rows: list[dict[str, Any]] | None, key: str) -> str:
    if not rows:
        return "Not run"
    passed, total = count_passes(rows, key)
    return f"{passed}/{total}"


def runtime_text(runtime_key: str) -> str:
    runtime = st.session_state.get("eval_runtimes", {}).get(runtime_key)
    return "Not run" if runtime is None else f"{runtime:.2f}s"


def follow_up_rating_summary(rows: list[dict[str, Any]] | None) -> str:
    if not rows:
        return "Not run"
    counts = {"strong": 0, "medium": 0, "weak": 0, "error": 0}
    for row in rows:
        rating = str(row.get("Judge Rating", "error")).lower()
        counts[rating if rating in counts else "error"] += 1
    parts = [f"{label}: {count}" for label, count in counts.items() if count]
    return ", ".join(parts) if parts else "No ratings"


def llm_call_text(layer: str) -> str:
    calls = estimated_llm_calls()
    return f"~{calls[layer]} calls"


def collect_follow_up_answers(ticket: Ticket) -> Dict[str, str]:
    answers: Dict[str, str] = {}
    for index, question in enumerate(filter_follow_up_questions(ticket.suggested_follow_up_questions), start=1):
        answer = st.text_input(question, key=f"follow_up_{ticket.ticket_id}_{index}")
        if answer.strip():
            answers[question] = answer.strip()
    return answers


def submit_tab() -> None:
    if not api_key_configured():
        st.warning("OPENAI_API_KEY is not configured. Ticket analysis requires an OpenAI-compatible API key.")

    st.info(
        "Use this form to report estate or shared-area issues such as faulty lifts, broken lights, "
        "water leaks, pests, obstruction, cleanliness, damaged facilities, or safety hazards. "
        "For personal medical issues or emergencies not caused by an estate defect, contact the "
        "appropriate emergency or healthcare service instead."
    )

    complaint = st.text_area(
        "Resident complaint",
        height=140,
        placeholder="Example: The lift at my block keeps breaking down and my mum in wheelchair cannot go down for appointment.",
    )

    if st.button("Analyse Complaint", type="primary", disabled=not api_key_configured()):
        if not complaint.strip():
            st.warning("Enter a complaint before analysing.")
        else:
            try:
                with st.spinner("Analysing complaint"):
                    extractor = get_extractor()
                    st.session_state.draft_ticket = extractor.extract_ticket(complaint)
                    st.session_state.draft_complaint = complaint
                    st.session_state.last_created_ticket = None
            except Exception as exc:
                st.error(f"Could not analyse complaint: {exc}")

    draft: Ticket | None = st.session_state.get("draft_ticket")
    if not draft:
        last_created: Ticket | None = st.session_state.get("last_created_ticket")
        if last_created:
            st.success(f"Created ticket {last_created.ticket_id}.")
            render_created_ticket_feedback(last_created)
        return

    st.subheader("Parsed ticket draft")
    render_ticket_card(draft)

    col1, col2 = st.columns(2)
    with col1:
        render_list("Missing details", draft.missing_details)
    with col2:
        render_list("Risk flags", draft.risk_flags)

    st.subheader("Location details")
    location_answer = st.text_input(
        LOCATION_QUESTION,
        key=f"location_detail_{draft.ticket_id}",
        placeholder=LOCATION_PLACEHOLDER,
    )

    st.subheader("Quick checks")
    check_col1, check_col2, check_col3 = st.columns(3)
    with check_col1:
        injury_answer = st.selectbox(INJURY_QUESTION, INJURY_OPTIONS, key=f"injury_{draft.ticket_id}")
    with check_col2:
        access_answer = st.selectbox(ACCESS_QUESTION, ACCESS_OPTIONS, key=f"access_{draft.ticket_id}")
    with check_col3:
        timing_answer = st.selectbox(TIMING_QUESTION, TIMING_OPTIONS, key=f"timing_{draft.ticket_id}")

    visible_follow_up_questions = filter_follow_up_questions(draft.suggested_follow_up_questions)
    if visible_follow_up_questions:
        st.subheader("Additional follow-up questions")
        draft_for_questions = draft.model_copy(deep=True)
        draft_for_questions.suggested_follow_up_questions = visible_follow_up_questions
        answers = collect_follow_up_answers(draft_for_questions)
    else:
        answers = {}
        st.caption("No follow-up questions needed for this draft.")

    if st.button("Create Ticket"):
        ticket = draft.model_copy(deep=True)
        if location_answer.strip():
            answers[LOCATION_QUESTION] = location_answer.strip()
        answers[INJURY_QUESTION] = injury_answer
        answers[ACCESS_QUESTION] = access_answer
        answers[TIMING_QUESTION] = timing_answer
        extractor = get_extractor()
        with st.status("Creating ticket", expanded=True) as status:
            st.write("Re-evaluating complaint and answers")
            ticket = extractor.finalize_ticket(st.session_state.draft_complaint, ticket, answers)
            st.write("Applying routing and adding ticket to queue")
            status.update(label=f"Created ticket {ticket.ticket_id}", state="complete", expanded=False)
        st.session_state.tickets.append(ticket)
        st.session_state.last_created_ticket = ticket
        st.session_state.draft_ticket = None
        st.session_state.draft_complaint = ""
        st.success(f"Created ticket {ticket.ticket_id}.")
        render_created_ticket_feedback(ticket)


def ticket_queue_tab() -> None:
    tickets: List[Ticket] = st.session_state.tickets
    if not tickets:
        st.info("No tickets created yet.")
        return

    for ticket in tickets:
        render_queue_signal(ticket)

    st.dataframe([as_table_row(ticket) for ticket in tickets], use_container_width=True, hide_index=True)

    for ticket in tickets:
        with st.expander(f"{ticket.ticket_id} - {ticket.ticket_title}"):
            render_ticket_card(ticket)
            col1, col2 = st.columns(2)
            with col1:
                render_list("Missing details", ticket.missing_details)
                render_list("Risk flags", ticket.risk_flags)
            with col2:
                render_list("Evidence quotes", ticket.evidence_quotes)
                st.markdown("**Confidence**")
                st.json(ticket.confidence.model_dump(mode="json"))
            st.markdown("**Final Pydantic ticket**")
            render_ticket_json(ticket)


def evaluation_tab() -> None:
    if not api_key_configured():
        st.warning("OPENAI_API_KEY is not configured. Evaluation requires the configured live model.")

    draft_results = st.session_state.get("draft_eval_results")
    follow_up_results = st.session_state.get("follow_up_review_results")
    final_results = st.session_state.get("final_eval_results")

    overview, draft_tab, follow_up_tab, final_tab = st.tabs(
        ["Overview", "Draft Extraction", "Follow-up Questions", "Final Tickets"]
    )

    with overview:
        st.markdown(
            "The evaluation mirrors the product workflow: first extract a draft ticket, then review "
            "the follow-up planner, then verify the final ticket after controlled clarifications. "
            f"The full run is intentionally compact at about {estimated_llm_calls()['Total']} live model calls."
        )
        if st.button("Run Full Evaluation", type="primary", disabled=not api_key_configured()):
            run_all_evaluations()
            draft_results = st.session_state.get("draft_eval_results")
            follow_up_results = st.session_state.get("follow_up_review_results")
            final_results = st.session_state.get("final_eval_results")

        st.markdown("**Evaluation summary**")
        st.dataframe(
            [
                {
                    "Layer": "Draft extraction",
                    "Result": evaluation_count(draft_results, "Exact Label Match"),
                    "Runtime": runtime_text("Draft"),
                    "Estimated LLM Calls": llm_call_text("Draft"),
                    "Review method": "Automatic field match",
                    "What to inspect": "Core labels plus optional status and risk-flag checks.",
                },
                {
                    "Layer": "Follow-up questions",
                    "Result": follow_up_rating_summary(follow_up_results),
                    "Runtime": runtime_text("Follow-up"),
                    "Estimated LLM Calls": llm_call_text("Follow-up"),
                    "Review method": "LLM judge: strong, medium, weak",
                    "What to inspect": "Judge rationale and suggested improvements for generated questions.",
                },
                {
                    "Layer": "Final ticket",
                    "Result": evaluation_count(final_results, "All Expected Fields Match"),
                    "Runtime": runtime_text("Final"),
                    "Estimated LLM Calls": llm_call_text("Final"),
                    "Review method": "Automatic field match",
                    "What to inspect": "Core labels plus clarification-sensitive escalation checks.",
                },
            ],
            use_container_width=True,
            hide_index=True,
        )
        st.caption(f"Total runtime: {runtime_text('Total')}")

    with draft_tab:
        st.markdown("Checks the first LLM pass before any fixed fields or follow-up answers are added.")
        if st.button("Run Draft Extraction Eval", disabled=not api_key_configured()):
            run_single_evaluation("Draft", "draft_eval_results", run_draft_extraction_eval)
            draft_results = st.session_state.get("draft_eval_results")
        if draft_results:
            exact, total = count_passes(draft_results, "Exact Label Match")
            category, _ = count_passes(draft_results, "Category Match")
            urgency, _ = count_passes(draft_results, "Urgency Match")
            routing, _ = count_passes(draft_results, "Routing Match")
            st.write(
                f"Exact label match: {exact}/{total}. "
                f"Category: {category}/{total}, urgency: {urgency}/{total}, routing: {routing}/{total}."
            )
            operational, _ = count_passes(draft_results, "Operational Checks Match")
            st.write(f"Optional status/risk checks: {operational}/{total}.")
            st.dataframe(draft_results, use_container_width=True, hide_index=True)
            render_runtime_metric("Runtime", "Draft")

    with follow_up_tab:
        st.markdown(
            "Uses a separate LLM-as-judge pass to rate generated questions as strong, medium, or weak. "
            "The judgement is a review aid, not ground truth."
        )
        if st.button("Run Follow-up Review", disabled=not api_key_configured()):
            run_single_evaluation("Follow-up", "follow_up_review_results", run_follow_up_question_review)
            follow_up_results = st.session_state.get("follow_up_review_results")
        if follow_up_results:
            st.write(f"Follow-up question ratings: {follow_up_rating_summary(follow_up_results)}.")
            st.data_editor(
                follow_up_results,
                use_container_width=True,
                hide_index=True,
                height=420,
                column_config={
                    "Complaint": st.column_config.TextColumn(width="medium"),
                    "Generated Questions": st.column_config.TextColumn(width="large"),
                    "Question Count": st.column_config.NumberColumn(width="small"),
                    "Review Target": st.column_config.TextColumn(width="large"),
                    "Judge Rating": st.column_config.TextColumn(width="small"),
                    "Judge Rationale": st.column_config.TextColumn(width="large"),
                    "Suggested Improvement": st.column_config.TextColumn(width="large"),
                },
                disabled=[
                    "Case",
                    "Complaint",
                    "Generated Questions",
                    "Question Count",
                    "Review Target",
                    "Judge Rating",
                    "Judge Rationale",
                    "Suggested Improvement",
                ],
            )
            render_runtime_metric("Runtime", "Follow-up")

    with final_tab:
        st.markdown(
            "Uses hand-written clarification bundles, then compares the final ticket's extracted "
            "fields against the expected fields."
        )
        if st.button("Run Final Ticket Eval", disabled=not api_key_configured()):
            run_single_evaluation("Final", "final_eval_results", run_final_ticket_eval)
            final_results = st.session_state.get("final_eval_results")
        if final_results:
            passed, total = count_passes(final_results, "All Expected Fields Match")
            operational, _ = count_passes(final_results, "Operational Checks Match")
            st.write(f"Final tickets with core expected labels matching: {passed}/{total}.")
            st.write(f"Optional status/risk checks: {operational}/{total}.")
            st.dataframe(final_results, use_container_width=True, hide_index=True)
            render_runtime_metric("Runtime", "Final")


def main() -> None:
    init_state()
    st.title("FixMyEstate SG")

    submit, queue, evaluation = st.tabs(["Submit Complaint", "Ticket Queue", "Evaluation"])
    with submit:
        submit_tab()
    with queue:
        ticket_queue_tab()
    with evaluation:
        evaluation_tab()


if __name__ == "__main__":
    main()
