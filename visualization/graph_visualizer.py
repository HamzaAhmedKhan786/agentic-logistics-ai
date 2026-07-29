def mermaid_graph() -> str:
    return """flowchart LR
    A[Planner Agent] --> B[Executor Agent]
    B --> C[Reflection Agent]
    C -->|invalid and retries remain| D[Replanner Agent]
    D --> B
    C -->|valid or retry limit| E[Finalizer Agent]
"""
