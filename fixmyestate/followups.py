from __future__ import annotations

import re


FIXED_FIELD_QUESTION_PATTERNS = [
    r"\b(block|specific location|exact location|location|where|address|street|estate|town|postal|postcode)\b",
    r"\b(floor|level|corridor|lobby|unit|area|staircase|void deck|lift lobby)\b",
    r"\b(when|how long|duration|first noticed|started|start|recurring|repeatedly|one[- ]?off|today|yesterday)\b",
    r"\b(injured|trapped|vulnerable|elderly|disabled|wheelchair|children)\b",
    r"\b(access|accessibility)\b",
    r"\b(safety issue|safety issues|safety concern|safety concerns|causing any safety)\b",
]

SPECIFIC_HAZARD_TERMS = [
    "broken glass",
    "glass shards",
    "sharp debris",
    "exposed wiring",
    "electrical",
    "sparks",
    "smoke",
    "fire",
    "slip",
    "slippery",
    "flood",
]


def overlaps_fixed_field(question: str) -> bool:
    lower = question.lower()
    if any(term in lower for term in SPECIFIC_HAZARD_TERMS):
        return False
    return any(re.search(pattern, lower) for pattern in FIXED_FIELD_QUESTION_PATTERNS)


def filter_follow_up_questions(questions: list[str]) -> list[str]:
    result: list[str] = []
    for question in questions:
        cleaned = question.strip()
        if cleaned and not overlaps_fixed_field(cleaned):
            result.append(cleaned)
    return result[:3]
