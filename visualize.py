"""Print the agent graph or export its Mermaid source."""

from pathlib import Path

from visualization.graph_visualizer import mermaid_graph


if __name__ == "__main__":
    diagram = mermaid_graph()
    target = Path(__file__).resolve().parent / "output" / "workflow.mmd"
    target.parent.mkdir(exist_ok=True)
    target.write_text(diagram, encoding="utf-8")
    print(diagram)
    print(f"\nSaved to {target}")
