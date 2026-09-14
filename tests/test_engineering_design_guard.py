from portable.engineering_design_guard import (
    DesignDimension,
    EngineeringDesignGuard,
    FindingSeverity,
)


def test_high_risk_external_change_requires_resilience_contract():
    receipt = EngineeringDesignGuard.review(
        intent="Add retry handling to outbound payment API",
        changed_paths=["portable/payment_client.py"],
        risk="high",
        design={"architecture": "client stays behind an outbound adapter"},
    )

    assert receipt.status == "blocked"
    assert any(
        f.dimension == DesignDimension.RESILIENCE and f.severity == FindingSeverity.BLOCKING
        for f in receipt.findings
    )


def test_complete_domain_data_and_refactoring_contract_is_ready():
    receipt = EngineeringDesignGuard.review(
        intent="Refactor the billing aggregate and preserve API behavior",
        changed_paths=["domain/billing.py", "tests/test_billing.py"],
        risk="medium",
        design={
            "domain": "Billing bounded context owns invoice lifecycle invariants",
            "data": "Postgres is the source of truth; events are derived and replayable",
            "refactoring": "behavior delta is none; characterization and contract tests protect behavior",
            "behavior_delta": "none",
            "safety_net": "billing contract tests plus focused unit tests",
            "architecture": "domain stays independent of persistence and transport",
            "construction": "validate boundary inputs and preserve diagnostic errors",
            "compatibility": "existing API remains backward compatible",
            "complexity": "reduce caller knowledge by hiding invoice state transitions",
        },
    )

    assert receipt.status == "ready"
    assert not receipt.blocking
    assert receipt.receipt_digest


def test_not_applicable_requires_a_reason():
    receipt = EngineeringDesignGuard.review(
        intent="Rename a local pure function",
        changed_paths=["portable/naming.py"],
        design={"resilience": "not_applicable"},
    )

    assert any(
        f.dimension == DesignDimension.RESILIENCE and f.severity == FindingSeverity.WARNING
        for f in receipt.findings
    )
