def mermaid_graph() -> str:
    from graph.workflow import workflow_graph

    return workflow_graph.get_graph().draw_mermaid()
