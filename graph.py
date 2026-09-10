from langgraph.graph import StateGraph, END
from state import GraphState
from nodes import (
    classify_task,
    run_writer,
    run_verification,
    run_security_review,
    route_after_verify,
    route_after_review,
)

graph = StateGraph(GraphState)
graph.add_node("classify_task", classify_task)
graph.add_node("writer", run_writer)
graph.add_node("verify", run_verification)
graph.add_node("security_review", run_security_review)
graph.set_entry_point("classify_task")
graph.add_edge("classify_task", "writer")
# Real `pnpm lint`/`pnpm test` gate before the LLM review - see
# run_verification in nodes.py. A verify failure loops straight back to
# writer without ever reaching security_review (no point spending a review
# call on a diff that doesn't even pass its own lint/test suite).
graph.add_edge("writer", "verify")
graph.add_conditional_edges("verify", route_after_verify, {"proceed": "security_review", "retry": "writer", "blocked": END})
graph.add_conditional_edges("security_review", route_after_review, {"done": END, "retry": "writer", "blocked": END})
compiled = graph.compile()
