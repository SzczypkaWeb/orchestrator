# Schematy JSON, ktore SDK wymusza na koncu przebiegu agenta.
# Zadna z tych wartosci juz nigdy nie przechodzi przez regex/string-matching.
CLASSIFY_SCHEMA = {
    "type": "object",
    "properties": {
        "complexity": {"type": "string", "enum": ["simple_crud", "novel"]},
    },
    "required": ["complexity"]
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