"""Run with: deepeval test run tests/evals/test_planner_deepeval.py"""

import asyncio
import json
import os

import pytest

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_LLM_EVALS", "false").lower() != "true",
    reason="LLM judge evaluations are opt-in",
)


def test_planner_safety_and_relevance() -> None:
    from deepeval.metrics import GEval
    from deepeval.test_case import LLMTestCase, LLMTestCaseParams

    from agents import planner_agent
    from models.schemas import PlanRequest, Stop, Vehicle
    from models.state import LogisticsState
    from tests.evals.groq_judge import GroqJudge

    state = LogisticsState(
        request=PlanRequest(
            depot=Stop(name="Hub", address="Berlin"),
            stops=[Stop(name="Customer", address="Mitte", demand_kg=90)],
            vehicles=[Vehicle(id="V1", capacity_kg=100)],
            simulate_traffic=False,
        )
    )
    asyncio.run(planner_agent.run(state))
    test_case = LLMTestCase(
        input="Plan a safe capacity-constrained delivery route.",
        actual_output=json.dumps(state.plan_strategy),
        expected_output=(
            "A strategy that respects vehicle capacity, does not invent distances, "
            "and delegates route calculations to deterministic tools."
        ),
    )
    metric = GEval(
        name="Logistics planning safety",
        criteria=(
            "The strategy must preserve hard capacity constraints, avoid fabricated "
            "route facts, and describe an operational planning approach."
        ),
        evaluation_params=[
            LLMTestCaseParams.ACTUAL_OUTPUT,
            LLMTestCaseParams.EXPECTED_OUTPUT,
        ],
        threshold=0.7,
        model=GroqJudge(),
        async_mode=False,
    )
    metric.measure(test_case)
    assert metric.score is not None
    assert metric.score >= metric.threshold
    from prometheus_client import CollectorRegistry, Gauge, push_to_gateway

    registry = CollectorRegistry()
    score = Gauge(
        "logistics_llm_eval_score",
        "Latest DeepEval score",
        ["metric", "model"],
        registry=registry,
    )
    score.labels(metric=metric.name, model=GroqJudge().get_model_name()).set(
        metric.score
    )
    from config.settings import settings

    try:
        push_to_gateway(
            settings.prometheus_pushgateway,
            job="route_mind_deepeval",
            registry=registry,
        )
    except OSError:
        # Evaluation validity must not depend on the local monitoring stack.
        pass
