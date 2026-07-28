from langgraph.graph import StateGraph, END
from state import GraphState
from nodes import classify_task, run_writer, run_security_review, route_after_review

graph = StateGraph(GraphState)
graph.add_node("classify_task", classify_task)
graph.add_node("writer", run_writer)
graph.add_node("security_review", run_security_review)
graph.set_entry_point("classify_task")
graph.add_edge("classify_task", "writer")
graph.add_edge("writer", "security_review")
graph.add_conditional_edges("security_review", route_after_review, {"done": END, "blocked": END})
compiled = graph.compile()