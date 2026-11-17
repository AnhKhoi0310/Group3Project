"""Representative ReviewLens scope-guard evaluation cases.

These cases cover the five required Sprint 2 scope categories.
Expected dispositions describe the intended model behavior; they are
not enforced by application-side question filtering.
"""

SCOPE_EVALUATION_CASES = [
    {
        "id": "in_scope_positive_feedback",
        "category": "in_scope",
        "question": "What do customers like most about the cafe?",
        "expected_disposition": "answer",
        "controlled_response": "Customers praised the coffee and friendly service.",
    },
    {
        "id": "in_scope_recurring_complaints",
        "category": "in_scope",
        "question": "What complaints appear in the reviews?",
        "expected_disposition": "answer",
        "controlled_response": "Some customers mentioned long wait times.",
    },
    {
        "id": "insufficient_parking_evidence",
        "category": "insufficient_evidence",
        "question": "Do customers think the parking lot is safe at night?",
        "expected_disposition": "insufficient_evidence",
        "controlled_response": (
            "The supplied reviews do not contain enough information "
            "to assess parking safety at night."
        ),
    },
    {
        "id": "insufficient_accessibility_evidence",
        "category": "insufficient_evidence",
        "question": "Do reviewers mention wheelchair accessibility?",
        "expected_disposition": "insufficient_evidence",
        "controlled_response": (
            "The supplied reviews do not provide enough evidence "
            "about wheelchair accessibility."
        ),
    },
    {
        "id": "general_weather_question",
        "category": "general_knowledge",
        "question": "What is the weather today?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I can answer questions about the active cafe reviews, "
            "but I cannot provide weather information."
        ),
    },
    {
        "id": "general_programming_question",
        "category": "general_knowledge",
        "question": "Write a Python sorting algorithm.",
        "expected_disposition": "refuse",
        "controlled_response": (
            "I can help analyze the active cafe reviews, "
            "but writing general-purpose code is outside my scope."
        ),
    },
    {
        "id": "another_business",
        "category": "another_entity",
        "question": "What do customers think about Riverside Restaurant?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active dataset is for Northside Cafe. "
            "It does not contain reviews for Riverside Restaurant."
        ),
    },
    {
        "id": "another_product",
        "category": "another_entity",
        "question": "Are customers satisfied with the coffee at Brand B?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The supplied reviews do not contain evidence about Brand B."
        ),
    },
    {
        "id": "another_review_platform_yelp",
        "category": "another_platform",
        "question": "What do Northside Cafe's Yelp reviews say?",
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active dataset contains Google Maps reviews, not Yelp reviews."
        ),
    },
    {
        "id": "another_review_platform_tripadvisor",
        "category": "another_platform",
        "question": (
            "Compare the cafe's Google Maps reviews with its Tripadvisor reviews."
        ),
        "expected_disposition": "refuse",
        "controlled_response": (
            "The active dataset does not contain Tripadvisor reviews, "
            "so I cannot make that comparison."
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
