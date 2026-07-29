def mermaid_architecture() -> str:
    return """flowchart TB
    UI[Web Dashboard] --> API[FastAPI API]
    API --> WF[Agent Workflow]
    WF --> LLM[LLM Provider]
    WF --> TOOLS[Geocoding / Routing / RAG / Fleet Tools]
    WF --> VALIDATORS[Deterministic Validators]
    API --> STORE[JSON Checkpoints]
"""
