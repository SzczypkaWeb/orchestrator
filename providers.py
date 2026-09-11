import json
import os
from groq import Groq
from google import genai

# Mirrors ai-service/providers.py's pattern (same two providers, same idea:
# cheap/fast structured JSON completion, no agentic tool use). Kept as a
# separate copy rather than importing across repos - each Python service
# here is independently deployable with its own venv/deps, same as every
# other repo in this project.
#
# Explicit `os.environ[...]` (not relying on the SDKs' own default env var
# names) on purpose: ai-service's .env has GROG_API_KEY/DEFAULT_GEMINI_API_KEY,
# neither of which matches what the groq/google-genai SDKs read by default
# (GROQ_API_KEY / GOOGLE_API_KEY or GEMINI_API_KEY) - meaning those calls may
# have been silently authenticating as anonymous/failing and falling back
# every time, without ever raising a visible error. Reading an explicit,
# correctly-named var here means a missing/wrong key fails loudly (KeyError)
# instead of silently degrading to the next fallback.


def complete_with_groq(prompt: str, schema: dict, model: str = "openai/gpt-oss-20b") -> tuple[dict, dict]:
    """Structured JSON completion via Groq. Raises on any failure - callers
    are expected to catch and fall back (see classify_task/run_security_review
    in nodes.py).

    Returns (parsed_json, usage) rather than just the parsed dict - `usage`
    carries token counts for telemetry.py (see nodes.py's call sites), kept
    as a plain dict rather than baking a "_usage" key into the response body
    itself, which would leak into the schema-validated JSON."""
    client = Groq(api_key=os.environ["GROQ_API_KEY"])
    response = client.chat.completions.create(
        model=model,
        messages=[{"role": "user", "content": prompt}],
        response_format={
            "type": "json_schema",
            "json_schema": {"name": "response", "strict": True, "schema": schema},
        },
    )
    data = json.loads(response.choices[0].message.content or "{}")
    usage = {
        "input_tokens": response.usage.prompt_tokens if response.usage else None,
        "output_tokens": response.usage.completion_tokens if response.usage else None,
    }
    return data, usage


def complete_with_gemini(prompt: str, schema: dict, model: str = "gemini-3.8-flash") -> tuple[dict, dict]:
    """Structured JSON completion via Gemini. Raises on any failure - see
    complete_with_groq. Returns (parsed_json, usage), same shape/reasoning as
    complete_with_groq."""
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    response = client.models.generate_content(
        model=model,
        contents=prompt,
        # `response_format` isn't a real field on the current SDK's
        # GenerateContentConfig (this was silently never exercised before -
        # GEMINI_API_KEY was unset in every prior run). `response_json_schema`
        # is the correct field for a raw JSON Schema dict like ours (as
        # opposed to `response_schema`, which expects a Pydantic/TypedDict
        # class) - `response_mime_type` is required alongside it.
        config={"response_mime_type": "application/json", "response_json_schema": schema},
    )
    data = json.loads(response.text)
    usage = {
        "input_tokens": getattr(response.usage_metadata, "prompt_token_count", None),
        "output_tokens": getattr(response.usage_metadata, "candidates_token_count", None),
    }
    return data, usage
