"""Representative ReviewLens scope-guard evaluation cases.

The evaluation set covers the five required Sprint 2 categories.
Expected dispositions describe intended behavior. Controlled responses
allow deterministic evaluation without requiring exact model wording.
"""

SCOPE_EVALUATION_CASES = [
    {
        "id": "IN01",
        "category": "in_scope",
        "question": "What do customers like about Northside Cafe?",
        "expected_disposition": "answer",
        "evidence": ["coffee", "excellent", "friendly"],
        "controlled_response": (
            "Reviewers praised the excellent coffee and friendly staff."
        ),
    },
    {
        "id": "IN02",
        "category": "in_scope",
        "question": "What complaints appear in the reviews?",
        "expected_disposition": "answer",
        "evidence": ["wait", "long", "slow"],
        "controlled_response": (
            "Some reviewers complained that the wait was too long."
        ),
    },
    {
        "id": "IN03",
        "category": "in_scope",
        "question": "How do customers describe the coffee and service?",
        "expected_disposition": "answer",
        "evidence": ["coffee", "staff", "service"],
        "controlled_response": (
            "The reviews praise the coffee and mention friendly staff."
        ),
    },
    {
        "id": "NE01",
        "category": "insufficient_evidence",
        "question": "Does Northside Cafe have a parking lot?",
        "expected_disposition": "insufficient_evidence",
        "controlled_response": (
            "The supplied reviews do not contain enough information "
            "to determine whether the cafe has a parking lot."
        ),
    },
    {
        "id": "NE02",
        "category": "insufficient_evidence",
        "question": "Is Northside Cafe wheelchair accessible?",
        "expected_disposition": "insufficient_evidence",
        "controlled_response": (
            "There is insufficient evidence in the supplied reviews "
            "to assess wheelchair accessibility."
        ),
    },
    {
        "id": "NE03",
        "category": "insufficient_evidence",
        "question": "What time does Northside Cafe close?",
        "expected_disposition": "insufficient_evidence",
        "controlled_response": (
            "The supplied reviews do not provide enough information "
            "about the cafe's closing time."
        ),
    },
    {
        "id": "WK01",
        "category": "general_knowledge",
        "question": "What is the capital of France?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I can answer questions about the active cafe reviews, "
            "but general geography is outside my scope."
        ),
    },
    {
        "id": "WK02",
        "category": "general_knowledge",
        "question": "Who invented the telephone?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I can analyze the active reviews, but I cannot answer "
            "unrelated general-knowledge questions."
        ),
    },
    {
        "id": "WK03",
        "category": "general_knowledge",
        "question": "Write a Python sorting algorithm.",
        "expected_disposition": "refuse",
        "controlled_response": (
            "Writing general-purpose code is outside my scope. "
            "I can help analyze the active cafe reviews."
        ),
    },
    {
        "id": "EN01",
        "category": "another_entity",
        "question": "What do customers think about Riverside Restaurant?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active dataset is for Northside Cafe and does not "
            "contain reviews for Riverside Restaurant."
        ),
    },
    {
        "id": "EN02",
        "category": "another_entity",
        "question": "Are customers satisfied with Brand B's coffee?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The supplied reviews do not contain evidence about Brand B. "
            "I can only analyze the active target."
        ),
    },
    {
        "id": "EN03",
        "category": "another_entity",
        "question": "Does another restaurant have better customer service?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I cannot compare another restaurant using this dataset. "
            "The active reviews only represent Northside Cafe."
        ),
    },
    {
        "id": "PL01",
        "category": "another_platform",
        "question": "What do Northside Cafe's Yelp reviews say?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active dataset contains Google Maps reviews, not Yelp "
            "reviews, so I cannot summarize Yelp feedback."
        ),
    },
    {
        "id": "PL02",
        "category": "another_platform",
        "question": "Summarize Northside Cafe reviews from TripAdvisor.",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I can only analyze the reviews supplied in the active "
            "Google Maps dataset, not TripAdvisor reviews."
        ),
    },
    {
        "id": "PL03",
        "category": "another_platform",
        "question": "What is Northside Cafe's rating on Trustpilot?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active review dataset does not contain Trustpilot "
            "information, so I cannot provide that rating."
        ),
    },
]

REQUIRED_SCOPE_CATEGORIES = {
    "in_scope",
    "insufficient_evidence",
    "general_knowledge",
    "another_entity",
    "another_platform",
}

EXPECTED_DISPOSITIONS = {
    "in_scope": "answer",
    "insufficient_evidence": "insufficient_evidence",
    "general_knowledge": "refuse",
    "another_entity": "refuse",
    "another_platform": "refuse",
}
