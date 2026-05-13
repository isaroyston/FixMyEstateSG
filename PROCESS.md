# Process

## Framing

I chose estate-complaint triage because it is a practical public-sector workflow where unstructured text creates operational friction. The useful AI step is not writing a polished reply; it is turning messy resident language into a consistent ticket that an operator can inspect, complete, and route.

I scoped the prototype to the smallest workflow that proves the idea: text intake, structured ticket extraction, fixed clarification fields, optional AI follow-up questions, final re-evaluation, a queue view, and an evaluation tab. I deliberately dropped authentication, storage, maps, images, multilingual handling, duplicate-report detection, and real agency integration.

## Build Choices

I used Streamlit for speed and reproducibility, Pydantic for the ticket schema, and an OpenAI-compatible chat API for the LLM calls. The workflow is explicit rather than hidden inside a large orchestration framework:

1. Draft a ticket from the complaint.
2. Plan up to three complaint-specific follow-up questions.
3. Finalize the ticket after fixed fields and follow-up answers.
4. Evaluate follow-up question quality with a separate LLM-as-judge pass.

Python guardrails are limited to deterministic pieces: schema validation, routing by category, status derivation from canonical LLM fields, ticket IDs, per-ticket list cleanup, and filtering questions that duplicate fixed fields. The list cleanup only removes repeated values inside `missing_details`, `suggested_follow_up_questions`, `risk_flags`, and `evidence_quotes`; it does not deduplicate tickets. Classification, actionability, missing-detail judgement, and risk reasoning stay with the LLM.

I considered local or Singapore-oriented models as well, especially for Singlish, multilingual input, and future voice intake. That includes text-first MERaLiON options as well as audio-focused MERaLiON models. I kept the submitted version on an OpenAI-compatible API because the current app is easier to reproduce in Docker and avoids adding local model-serving complexity to the prototype scope.

## Judgement Calls

I added fixed controls for detailed location, injury/trapped status, access impact, and timing because every ticket needs those fields and they are easier to answer in a form than through dynamic questions.

I also added a non-actionable path. Gibberish, test input, and personal incidents not tied to an estate defect should not become operational tickets. Likewise, fixed "yes" answers for injury or access impact are treated as claims to evaluate rather than automatic escalation labels. However, injuries caused by public-area hazards still escalate.

The evaluation set is synthetic. That is acceptable for this prototype because no real resident data is needed to demonstrate the workflow, but I call out the limitation clearly rather than treating the numbers as production accuracy.

## Evaluation

The evaluation has three layers:

- Draft extraction: expected fields vs first-pass ticket fields.
- Follow-up questions: generated questions rated by an LLM judge as strong, medium, or weak.
- Final ticket: expected fields vs final ticket fields after controlled clarifications.

The cases cover common estate categories plus edge cases such as non-actionable input, unsupported self-reported injury/access claims, personal injury without an estate cause, and clarification-driven escalation. The set is intentionally compact because every full run makes about 85 live model calls. I treated it as a targeted workflow check rather than a statistically meaningful benchmark.

I also made the eval reflect the real intake workflow rather than only classification accuracy. The headline checks are still category, urgency, and routing because those drive triage. I added selected status/risk checks for cases where they matter operationally, such as closing non-actionable input or escalating high/critical cases. For follow-up questions, I used an LLM judge because exact wording is too brittle; the important question is whether the planner avoids duplicating fixed fields and asks a useful issue-specific question when one would improve dispatch.

In the latest run, draft extraction was clean on the compact benchmark and finalisation missed only one case: a broken public-area tile that caused injury. The model escalated it, but treated it as `damaged_facility`/`high`/`estate_maintenance` instead of `safety_hazard`/`critical`/`safety_inspection`. That is a useful failure because it shows the taxonomy problem: the same issue can be both a damaged asset and a safety hazard.

The weaker area remains follow-up question coverage. The planner often avoided duplicate questions, which is good, but sometimes interpreted the fixed fields as enough. My manual review agreed with the judge on the weak lift, obstruction, and bad-smell cases, and I would also treat the no-question lighting case as only medium because a lighting-specific hazard check would help.

## Tools Used

I used a coding assistant to scaffold and iterate on the prototype, then reviewed the workflow, simplified the repository. The final app requires a configured LLM and keeps the write-up aligned with the code.

## Next Steps

For a stronger version, I would add anonymised historical complaints, compare multiple models, calibrate guardrails with case-officer feedback, persist tickets, add audit logs, and integrate with a real case-management system. I would also add duplicate-report detection so repeated complaints about the same lift, light, or corridor are grouped instead of creating noisy queues.

Location handling is another clear next step: residents could optionally share phone geolocation, while still allowing manual location text for cases where GPS is unavailable or too imprecise. For accountability, a production version could use Singpass or another verified login path so reports are tied to real residents and abuse is easier to investigate.

Privacy review, consent wording, retention rules, and access controls would come before using real resident data.
