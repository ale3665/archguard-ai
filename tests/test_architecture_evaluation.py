
"""
ArchGuard AI — Architecture Detection Evaluation Tests.

Step 22: Controlled evaluation of deterministic
architectural rule detection.

This test suite reuses the synthetic project builders and
evaluation metric functions from:

    scripts/evaluate_architecture.py

Coverage:
    1. Clean architecture
    2. Circular dependency
    3. High coupling
    4. Layer-boundary violation
    5. Multiple architectural violations
    6. Perfect precision, recall, and F1 calculation
    7. False-positive and false-negative handling
    8. Rule-category comparison
    9. Aggregate evaluation metrics

The tests use temporary project directories and invoke
the FastAPI application using TestClient.

No running FastAPI server, Streamlit dashboard, or Ollama
service is required.

Run:
    python -m pytest tests/test_architecture_evaluation.py -v
"""

from __future__ import annotations

import pytest

from fastapi.testclient import TestClient

from archguard.adapters.api import create_app

from scripts.evaluate_architecture import (
    EXPECTED,
    RULES,
    build_clean_project,
    build_cycle_project,
    build_high_coupling_project,
    build_layer_violation_project,
    build_multiple_violation_project,
    calculate_metrics,
    evaluate_case,
    build_metrics,
)


# ============================================================
# Evaluation Scenarios
# ============================================================

SCENARIOS = {
    "clean_architecture": build_clean_project,
    "circular_dependency": build_cycle_project,
    "high_coupling": build_high_coupling_project,
    "layer_boundary_violation": build_layer_violation_project,
    "multiple_violations": build_multiple_violation_project,
}


# ============================================================
# Tests 1–5: Controlled Architecture Scenarios
# ============================================================

@pytest.mark.parametrize(
    "scenario_name",
    list(SCENARIOS),
)
def test_architecture_scenario_matches_ground_truth(
    tmp_path,
    scenario_name,
):
    """
    Analyze a controlled Python project and compare
    its detected rule categories with the expected ones.

    This validates rule-category detection rather than
    the exact number of individual violations.
    """

    # Identify the builder for the selected scenario.
    builder = SCENARIOS[scenario_name]

    # Create an isolated temporary project.
    project = tmp_path / scenario_name

    project.mkdir()

    # Generate the synthetic Python source files.
    builder(project)

    # Restrict the API to the temporary workspace.
    app = create_app(
        allowed_root=tmp_path,
    )

    # Invoke ArchGuard's actual analysis endpoint.
    with TestClient(app) as client:

        response = client.post(
            "/analyze",
            json={
                "project_path": scenario_name,
            },
        )

    # The analysis must complete successfully.
    assert response.status_code == 200, (
        f"{scenario_name}: {response.text}"
    )

    report = response.json()

    # Verify the response includes findings.
    assert isinstance(
        report.get("findings"),
        list,
    )

    # Extract the architectural rule categories
    # identified by ArchGuard.
    detected = {
        finding["rule_id"]
        for finding in report["findings"]
    }

    # Retrieve manually specified expected categories.
    expected = EXPECTED[scenario_name]

    # Compare actual and expected results.
    comparison = evaluate_case(
        expected,
        detected,
    )

    assert comparison["exact_match"], (
        f"\nScenario: {scenario_name}"
        f"\nExpected: {sorted(expected)}"
        f"\nDetected: {sorted(detected)}"
        f"\nFalse positives: "
        f"{comparison['false_positives']}"
        f"\nFalse negatives: "
        f"{comparison['false_negatives']}"
    )

    # Confirm that the summary accurately reports
    # the number of architectural findings.
    assert (
        report["summary"]["finding_count"]
        == len(report["findings"])
    )


# ============================================================
# Test 6: Perfect Classification Metrics
# ============================================================

def test_perfect_evaluation_metrics():
    """
    Verify the metric formulas for a hypothetical
    classification result with no mistakes.

    Example:
        True positives: 7
        False positives: 0
        False negatives: 0
        True negatives: 8

    This is an independent mathematical test,
    not the observed evaluation dataset.
    """

    metrics = calculate_metrics(
        true_positives=7,
        false_positives=0,
        false_negatives=0,
        true_negatives=8,
    )

    assert metrics["tp"] == 7
    assert metrics["fp"] == 0
    assert metrics["fn"] == 0
    assert metrics["tn"] == 8

    assert metrics["precision"] == 1.0
    assert metrics["recall"] == 1.0
    assert metrics["f1"] == 1.0


# ============================================================
# Test 7: False Positives and False Negatives
# ============================================================

def test_metrics_with_classification_errors():
    """
    Verify that incorrect predictions reduce
    precision, recall, and F1.

    Example:
        TP = 2
        FP = 1
        FN = 1
        TN = 5

    Expected:
        Precision = 2 / 3
        Recall = 2 / 3
        F1 = 2 / 3
    """

    metrics = calculate_metrics(
        true_positives=2,
        false_positives=1,
        false_negatives=1,
        true_negatives=5,
    )

    assert metrics["tp"] == 2
    assert metrics["fp"] == 1
    assert metrics["fn"] == 1
    assert metrics["tn"] == 5

    assert metrics["precision"] == 0.6667
    assert metrics["recall"] == 0.6667
    assert metrics["f1"] == 0.6667


# ============================================================
# Test 8: Detect Missing and Extra Rule Categories
# ============================================================

def test_evaluation_identifies_missing_and_extra_rules():
    """
    Verify that the evaluation detects both:
        - False positives (unexpected rule categories)
        - False negatives (missing expected categories)
    """

    expected = {
        "CIRCULAR_DEPENDENCY",
        "HIGH_COUPLING",
    }

    detected = {
        "CIRCULAR_DEPENDENCY",
        "LAYER_BOUNDARY_VIOLATION",
    }

    comparison = evaluate_case(
        expected,
        detected,
    )

    assert comparison["exact_match"] is False

    # Correctly identified rule category.
    assert comparison["true_positives"] == [
        "CIRCULAR_DEPENDENCY",
    ]

    # Unexpectedly detected category.
    assert comparison["false_positives"] == [
        "LAYER_BOUNDARY_VIOLATION",
    ]

    # Expected category that was not detected.
    assert comparison["false_negatives"] == [
        "HIGH_COUPLING",
    ]


# ============================================================
# Test 9: Aggregate Evaluation Metrics
# ============================================================

def test_aggregate_evaluation_metrics():
    """
    Verify micro-averaged and per-rule metrics
    across all five synthetic evaluation scenarios.

    Evaluation design:
        Number of scenarios: 5
        Rule categories: 3

    Total classification opportunities:
        5 * 3 = 15

    Expected-positive category instances:
        Clean architecture:       0
        Circular dependency:      1
        High coupling:            1
        Layer-boundary violation: 1
        Multiple violations:      3
                                  ---
        Total positives:          6

    Expected-negative category instances:
        15 - 6 = 9

    For perfect predictions:
        TP = 6
        FP = 0
        FN = 0
        TN = 9

    This test validates metric aggregation using
    ideal predictions.

    The live analyzer is independently exercised
    by the five parametrized scenario tests.
    """

    cases = []

    # Build hypothetical perfect predictions
    # for every expected evaluation scenario.
    for scenario_name, expected in EXPECTED.items():

        comparison = evaluate_case(
            expected,
            expected.copy(),
        )

        cases.append({
            "project": scenario_name,
            **comparison,
        })

    # Calculate aggregated evaluation statistics.
    metrics = build_metrics(cases)

    # --------------------------------------------------------
    # Scenario-Level Evaluation
    # --------------------------------------------------------

    assert metrics["scenario_count"] == 5

    assert metrics["exact_match_count"] == 5

    assert metrics["exact_match_accuracy"] == 1.0

    # --------------------------------------------------------
    # Micro-Averaged Evaluation Metrics
    # --------------------------------------------------------

    micro = metrics["micro"]

    # Five scenarios x three rule categories = 15
    # binary classification opportunities.
    #
    # Six expected-positive instances and
    # nine expected-negative instances.
    assert micro["tp"] == 6
    assert micro["fp"] == 0
    assert micro["fn"] == 0
    assert micro["tn"] == 9

    # Confirm the complete classification count.
    assert (
        micro["tp"]
        + micro["fp"]
        + micro["fn"]
        + micro["tn"]
    ) == 15

    # Verify perfect prediction metrics.
    assert micro["precision"] == 1.0
    assert micro["recall"] == 1.0
    assert micro["f1"] == 1.0

    # --------------------------------------------------------
    # Per-Rule Evaluation Metrics
    # --------------------------------------------------------

    # All expected architecture rules must be present.
    assert set(
        metrics["by_rule"]
    ) == set(RULES)

    for rule in RULES:

        rule_metrics = metrics["by_rule"][rule]

        # Each architectural rule is expected in
        # two of the five scenarios:
        #
        # 1. Its individual scenario.
        # 2. The multiple-violations scenario.
        assert rule_metrics["tp"] == 2
        assert rule_metrics["fp"] == 0
        assert rule_metrics["fn"] == 0
        assert rule_metrics["tn"] == 3

        assert rule_metrics["precision"] == 1.0
        assert rule_metrics["recall"] == 1.0
        assert rule_metrics["f1"] == 1.0

    # --------------------------------------------------------
    # Unknown Rule Categories
    # --------------------------------------------------------

    # The ideal predictions contain no unexpected rules.
    assert metrics["unexpected_rule_predictions"] == 0
