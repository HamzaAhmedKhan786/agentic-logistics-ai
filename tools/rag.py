from __future__ import annotations


POLICIES = [
    "Never exceed the declared vehicle capacity.",
    "Return each vehicle to the depot after its final delivery.",
    "Flag stops that cannot be assigned instead of silently dropping them.",
    "Escalate routes that exceed the vehicle maximum distance.",
]


def retrieve_policies(query: str, limit: int = 3) -> list[str]:
    """Tiny local RAG placeholder; swap for a vector store in production."""
    terms = set(query.lower().split())
    ranked = sorted(
        POLICIES,
        key=lambda policy: len(terms.intersection(policy.lower().split())),
        reverse=True,
    )
    return ranked[:limit]
