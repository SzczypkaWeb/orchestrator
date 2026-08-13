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
    existing_branch: str
    existing_pr_url: str
    # Number of times security_review has sent this task back to the writer
    # after a "changes_requested" verdict (see route_after_review in nodes.py).
    # Not set by initial_state_for() - defaults to 0 via state.get(...) at
    # every read site, so existing callers don't need to change.
    review_attempts: int