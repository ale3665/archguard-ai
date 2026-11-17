
"""
ArchGuard AI — Step 22 Architecture Detection Evaluation.

Creates five controlled Python projects, analyzes them with
ArchGuard's FastAPI backend, and compares detected finding
categories against an explicit expected-label manifest.

Metrics:
    - True positives
    - False positives
    - False negatives
    - True negatives
    - Precision
    - Recall
    - F1-score
    - Exact-match accuracy by scenario

This is a controlled rule-category evaluation, not a
real-world benchmark or a per-finding accuracy assessment.

Run from the project root:
    python scripts/evaluate_architecture.py

Requires FastAPI running at:
    http://127.0.0.1:8000
"""

from __future__ import annotations

import json
import sys

from datetime import datetime, timezone
from pathlib import Path
from urllib import error, request


ROOT = Path(__file__).resolve().parents[1]

DATASET_DIR = ROOT / "demo_projects" / "evaluation_cases"
OUTPUT_DIR = ROOT / "evaluation_results"

API_URL = "http://127.0.0.1:8000/analyze"

RULES = (
    "CIRCULAR_DEPENDENCY",
    "HIGH_COUPLING",
    "LAYER_BOUNDARY_VIOLATION",
)

EXPECTED = {
    "clean_architecture": set(),
    "circular_dependency": {
        "CIRCULAR_DEPENDENCY",
    },
    "high_coupling": {
        "HIGH_COUPLING",
    },
    "layer_boundary_violation": {
        "LAYER_BOUNDARY_VIOLATION",
    },
    "multiple_violations": set(RULES),
}


# ============================================================
# Dataset Construction
# ============================================================

def write_python(
    project: Path,
    relative_path: str,
    content: str = "",
) -> None:
    """Write UTF-8 Python source without a BOM."""

    destination = project / relative_path
    destination.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    destination.write_text(
        content,
        encoding="utf-8",
    )


def build_clean_project(project: Path) -> None:
    """Two independent modules with no dependencies."""

    write_python(
        project,
        "alpha.py",
        "def alpha():\n    return 1\n",
    )

    write_python(
        project,
        "beta.py",
        "def beta():\n    return 2\n",
    )


def build_cycle_project(project: Path) -> None:
    """A known two-module dependency cycle."""

    write_python(project, "a.py", "import b\n")
    write_python(project, "b.py", "import a\n")


def build_high_coupling_project(project: Path) -> None:
    """
    One module imports 12 sibling modules.

    The number 12 is an intentionally large fixture
    value, not a claim about ArchGuard's configured
    coupling threshold.
    """

    imports = []

    for index in range(12):
        name = f"dependency_{index:02d}"

        write_python(
            project,
            f"{name}.py",
            f"VALUE = {index}\n",
        )

        imports.append(f"import {name}")

    write_python(
        project,
        "highly_coupled.py",
        "\n".join(imports) + "\n",
    )


def build_layer_violation_project(
    project: Path,
) -> None:
    """Domain code imports an infrastructure adapter."""

    write_python(project, "archguard/__init__.py")
    write_python(project, "archguard/domain/__init__.py")
    write_python(project, "archguard/adapters/__init__.py")

    write_python(
        project,
        "archguard/domain/service.py",
        "import archguard.adapters.gateway\n",
    )

    write_python(
        project,
        "archguard/adapters/gateway.py",
        "def connect():\n    return None\n",
    )


def build_multiple_violation_project(
    project: Path,
) -> None:
    """
    Combine a cycle, a layer violation, and
    a highly coupled module.
    """

    write_python(project, "archguard/__init__.py")
    write_python(project, "archguard/domain/__init__.py")
    write_python(project, "archguard/adapters/__init__.py")

    # Circular dependency within the domain package.
    write_python(
        project,
        "archguard/domain/a.py",
        "import archguard.domain.b\n",
    )

    write_python(
        project,
        "archguard/domain/b.py",
        "import archguard.domain.a\n",
    )

    # Invalid dependency direction:
    # domain -> adapters.
    write_python(
        project,
        "archguard/domain/service.py",
        "import archguard.adapters.gateway\n",
    )

    write_python(
        project,
        "archguard/adapters/gateway.py",
        "VALUE = 1\n",
    )

    # High coupling in a separate module.
    imports = []

    for index in range(12):
        name = f"module_{index:02d}"

        write_python(
            project,
            f"archguard/domain/{name}.py",
            f"VALUE = {index}\n",
        )

        imports.append(
            f"import archguard.domain.{name}"
        )

    write_python(
        project,
        "archguard/domain/hub.py",
        "\n".join(imports) + "\n",
    )


def build_dataset() -> None:
    """
    Rebuild controlled source files.

    Existing scenario directories are reused.
    Files not managed by this script are not deleted.
    """

    builders = {
        "clean_architecture": build_clean_project,
        "circular_dependency": build_cycle_project,
        "high_coupling": build_high_coupling_project,
        "layer_boundary_violation":
            build_layer_violation_project,
        "multiple_violations":
            build_multiple_violation_project,
    }

    for name, builder in builders.items():
        project = DATASET_DIR / name
        project.mkdir(parents=True, exist_ok=True)
        builder(project)


# ============================================================
# API Analysis
# ============================================================

def analyze_project(project: Path) -> dict:
    """Analyze one project through ArchGuard FastAPI."""

    relative_path = project.relative_to(ROOT).as_posix()

    payload = json.dumps({
        "project_path": relative_path,
    }).encode("utf-8")

    http_request = request.Request(
        API_URL,
        data=payload,
        headers={
            "Content-Type": "application/json",
        },
        method="POST",
    )

    try:
        with request.urlopen(
            http_request,
            timeout=60,
        ) as response:
            result = json.loads(
                response.read().decode("utf-8")
            )

    except error.HTTPError as exc:
        details = exc.read().decode(
            "utf-8",
            errors="replace",
        )
        raise RuntimeError(
            f"API HTTP {exc.code}: {details}"
        ) from exc

    except (error.URLError, TimeoutError) as exc:
        raise RuntimeError(
            "Cannot contact FastAPI. Start the "
            "ArchGuard backend before evaluating."
        ) from exc

    if not isinstance(result, dict):
        raise ValueError(
            "API returned a non-object response."
        )

    if not isinstance(result.get("findings"), list):
        raise ValueError(
            "API response is missing a findings list."
        )

    return result


# ============================================================
# Metric Calculations
# ============================================================

def safe_ratio(
    numerator: int,
    denominator: int,
) -> float:
    """Return zero for an undefined denominator."""

    if denominator == 0:
        return 0.0

    return numerator / denominator


def calculate_metrics(
    true_positives: int,
    false_positives: int,
    false_negatives: int,
    true_negatives: int,
) -> dict:
    """Calculate binary classification statistics."""

    precision = safe_ratio(
        true_positives,
        true_positives + false_positives,
    )

    recall = safe_ratio(
        true_positives,
        true_positives + false_negatives,
    )

    f1 = safe_ratio(
        2 * precision * recall,
        precision + recall,
    )

    return {
        "tp": true_positives,
        "fp": false_positives,
        "fn": false_negatives,
        "tn": true_negatives,
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }


def evaluate_case(
    expected: set[str],
    detected: set[str],
) -> dict:
    """Compare expected and detected rule categories."""

    return {
        "expected": sorted(expected),
        "detected": sorted(detected),
        "true_positives": sorted(expected & detected),
        "false_positives": sorted(detected - expected),
        "false_negatives": sorted(expected - detected),
        "exact_match": expected == detected,
    }


def build_metrics(cases: list[dict]) -> dict:
    """
    Compute micro-average and per-rule metrics.

    Each (project, rule category) is one binary example.
    """

    tp = fp = fn = tn = 0
    by_rule = {}

    for rule in RULES:
        rule_tp = rule_fp = rule_fn = rule_tn = 0

        for case in cases:
            expected = set(case["expected"])
            detected = set(case["detected"])

            if rule in expected and rule in detected:
                rule_tp += 1

            elif rule not in expected and rule in detected:
                rule_fp += 1

            elif rule in expected and rule not in detected:
                rule_fn += 1

            else:
                rule_tn += 1

        by_rule[rule] = calculate_metrics(
            rule_tp,
            rule_fp,
            rule_fn,
            rule_tn,
        )

        tp += rule_tp
        fp += rule_fp
        fn += rule_fn
        tn += rule_tn

    # An unexpected rule outside the evaluated
    # vocabulary counts as an additional false positive.
    unexpected = sum(
        len(set(case["detected"]) - set(RULES))
        for case in cases
    )
    fp += unexpected

    exact = sum(
        case["exact_match"]
        for case in cases
    )

    return {
        "micro": calculate_metrics(tp, fp, fn, tn),
        "by_rule": by_rule,
        "exact_match_count": exact,
        "scenario_count": len(cases),
        "exact_match_accuracy": round(
            safe_ratio(exact, len(cases)),
            4,
        ),
        "unexpected_rule_predictions": unexpected,
    }


# ============================================================
# Evaluation Runner
# ============================================================

def main() -> int:
    """Generate fixtures, evaluate, and save results."""

    print("\nArchGuard AI — Step 22 Evaluation")
    print("=" * 54)

    build_dataset()

    print(
        f"Created {len(EXPECTED)} evaluation scenarios."
    )

    evaluated_cases = []

    for project_name, expected in EXPECTED.items():

        project = DATASET_DIR / project_name

        try:
            response = analyze_project(project)

        except (RuntimeError, ValueError) as exc:
            print(
                f"\nERROR analyzing {project_name}: {exc}"
            )
            return 1

        findings = response["findings"]

        detected = {
            str(item["rule_id"])
            for item in findings
            if isinstance(item, dict)
            and isinstance(item.get("rule_id"), str)
        }

        comparison = evaluate_case(
            expected,
            detected,
        )

        case = {
            "project": project_name,
            "project_path": project.relative_to(
                ROOT
            ).as_posix(),
            **comparison,
            "finding_count": len(findings),
            "findings": findings,
        }

        evaluated_cases.append(case)

        status = (
            "PASS"
            if comparison["exact_match"]
            else "MISMATCH"
        )

        print(f"\n[{status}] {project_name}")
        print(f"  Expected: {sorted(expected)}")
        print(f"  Detected: {sorted(detected)}")
        print(f"  Findings: {len(findings)}")

    metrics = build_metrics(evaluated_cases)

    report = {
        "evaluation": "ArchGuard AI Step 22",
        "timestamp_utc": datetime.now(
            timezone.utc
        ).isoformat(),
        "evaluation_level": "project_rule_category",
        "rule_vocabulary": list(RULES),
        "ground_truth_type":
            "manually constructed synthetic scenarios",
        "limitations": [
            "Synthetic projects only",
            "Not a benchmark of real-world repositories",
            "Metrics are based on rule categories, "
            "not individual finding instances",
            "Ground truth is based on the intended "
            "fixture design",
            "This does not measure the accuracy "
            "of AI-generated explanations",
        ],
        "cases": evaluated_cases,
        "metrics": metrics,
    }

    OUTPUT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    output_file = (
        OUTPUT_DIR / "step22_results.json"
    )

    output_file.write_text(
        json.dumps(
            report,
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    overall = metrics["micro"]

    print("\n" + "=" * 54)
    print("Evaluation Results")
    print("=" * 54)

    print(
        f"Exact matches: "
        f"{metrics['exact_match_count']}/"
        f"{metrics['scenario_count']}"
    )

    print(
        f"Precision: {overall['precision']:.4f}"
    )
    print(
        f"Recall:    {overall['recall']:.4f}"
    )
    print(
        f"F1-score:  {overall['f1']:.4f}"
    )

    print(
        f"\nResults saved to: {output_file}"
    )

    if metrics["exact_match_count"] != len(EXPECTED):
        print(
            "\nSome results differ from the fixture "
            "expectations. Review the finding details "
            "and configured detection rules before "
            "changing the expected labels."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
