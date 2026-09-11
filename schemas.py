# Schematy JSON, ktore SDK wymusza na koncu przebiegu agenta.
# Zadna z tych wartosci juz nigdy nie przechodzi przez regex/string-matching.
CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "complexity": {"type": "string", "enum": ["simple_crud", "novel"]},
    },
    "required": ["complexity"],
    # Groq's strict (OpenAI-compatible) structured output mode requires
    # additionalProperties:false on every object in the schema, including
    # the root - without it, Groq rejects the request outright (this only
    # surfaced once GROQ_API_KEY was actually set; the path was silently
    # skipped before that).
    "additionalProperties": False,
}

WRITER_SCHEMA = {
    "type": "object",
    "properties": {
        "branch": {"type": "string", "description": "Name of the git branch that was pushed"},
        "pr_url": {"type": "string", "description": "URL of the opened pull request"},
    },
    "required": ["branch", "pr_url"],
}

REVIEW_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["approved", "changes_requested"]},
        "notes": {"type": "string", "description": "Explanation for the verdict"},
    },
    "required": ["verdict", "notes"],
}