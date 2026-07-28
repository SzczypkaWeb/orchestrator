from typing import TypedDict

class GraphState(TypedDict):
    task: str
    repo_path: str
    stack_description: str
    review_focus: str
    writer_model: str
    branch: str
    pr_url: str
    review_verdict: str
    review_notes: str