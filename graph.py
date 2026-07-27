import asyncio
from pathlib import Path
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from claude_agent_sdk import query, ClaudeAgentOptions

BACKEND_PATH = str(Path("../backend").resolve())
class GraphState(TypedDict):
  task: str
  branch: str
  pr_url: str
  review_verdict: str
  review_notes: str

def extract_field(text: str, label: str) -> str:
    """Szuka linii 'LABEL: wartość' (ignorując np. markdown '## ' czy '**') i zwraca 'wartość'."""
    for line in text.splitlines():
        cleaned = line.strip().lstrip("#").lstrip("*").strip()
        if cleaned.upper().startswith(label.upper() + ":"):
            return cleaned.split(":", 1)[1].strip()
    return ""

async def run_writer(state: GraphState) -> GraphState:
    prompt = f"""
Pracujesz w repo backend (Nest.js + Prisma). Zadanie: {state['task']}

Wykonaj po kolei:
1. git checkout main && git pull, potem stwórz nowy branch o sensownej nazwie (feat/<coś>).
2. Zaimplementuj zadanie.
3. Dodaj/zaktualizuj testy.
4. Uruchom `pnpm test`, popraw jeśli coś nie przechodzi.
5. Zrób commit (conventional commits).
6. Wypchnij branch i otwórz PR: gh pr create --base main --head <branch> --fill
7. Na końcu wypisz DOKŁADNIE dwie linie:
   BRANCH: <nazwa brancha>
   PR_URL: <url PR>
"""
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            cwd=BACKEND_PATH,
            allowed_tools=["Read", "Edit", "Write", "Bash", "Glob", "Grep"],
            model="claude-sonnet-5",
        ),
    ):
        if hasattr(message, "result"):
            result_text = message.result

    return {
        **state,
        "branch": extract_field(result_text, "BRANCH"),
        "pr_url": extract_field(result_text, "PR_URL"),
    }



async def run_security_review(state: GraphState) -> GraphState:
    prompt = f"""
Przejrzyj zmiany na branchu {state['branch']} w repo backend
(np. `git diff main...{state['branch']}`).

Sprawdź pod kątem: sekretów w kodzie, braku walidacji wejścia, SQL injection,
zbyt szerokiego CORS, brakujących testów dla nowej logiki.

Na końcu wypisz DOKŁADNIE jedną z tych linii:
VERDICT: APPROVED
albo
VERDICT: CHANGES_REQUESTED
a pod nią krótkie uzasadnienie.
"""
    result_text = ""
    async for message in query(
        prompt=prompt,
        options=ClaudeAgentOptions(
            cwd=BACKEND_PATH,
            allowed_tools=["Read", "Bash", "Glob", "Grep"],  # bez Edit/Write — to reviewer, nie writer
            model="claude-haiku-4-5",  # sprawdzenie, nie pisanie kodu — tańszy model wystarczy
        ),
    ):
        if hasattr(message, "result"):
            result_text = message.result

    verdict_raw = extract_field(result_text, "VERDICT")
    verdict = "approved" if verdict_raw.upper() == "APPROVED" else "changes_requested"
    return {**state, "review_verdict": verdict, "review_notes": result_text}


def route_after_review(state: GraphState) -> Literal["done", "blocked"]:
  return "done" if state["review_verdict"] == "approved" else "blocked"


graph = StateGraph(GraphState)
graph.add_node("writer", run_writer)
graph.add_node("security_review", run_security_review)
graph.set_entry_point("writer")
graph.add_edge("writer", "security_review")
graph.add_conditional_edges("security_review", route_after_review, {"done": END, "blocked": END })
compiled = graph.compile()


async def main():
  result = await compiled.ainvoke({
    "task": "Dodaj endpoint GET /users/:id zwracający użytkownika po id, z testem. Jeśli user nie istnieje, zwróć 404.",
    "branch": "", "pr_url": "", "review_verdict": "", "review_notes": "",
  })
  print("Branch:", result["branch"])
  print("PR:", result["pr_url"])
  print("Verdict:", result["review_verdict"])
  print("Notes:", result["review_notes"])

asyncio.run(main())