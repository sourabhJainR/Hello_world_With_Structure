from portable.feedback_loop import (
    BoundedLoop,
    LoopAction,
    LoopDefinition,
    VerificationResult,
)


def make_loop(limit: int = 3) -> BoundedLoop:
    return BoundedLoop(
        LoopDefinition(
            name="test-loop",
            objective="make one safe improvement",
            acceptance_check="focused regression passes",
            scope="test workspace",
            pass_limit=limit,
        )
    )


def test_success_receipt_is_digest_bound() -> None:
    applied = []

    result = make_loop().run(
        observe=lambda n: f"state-{n}",
        choose=lambda observation, n: LoopAction(f"change-{n}"),
        act=lambda action, n: applied.append(action.description),
        verify=lambda action, n: VerificationResult(
            passed=True,
            complete=n == 2,
            progress=True,
            evidence=(f"check-{n}",),
        ),
    )

    assert result.result == "success"
    assert len(result.passes) == 2
    assert result.receipt_digest
    assert applied == ["change-1", "change-2"]
    assert result.passes[-1].complete is True


def test_clean_no_op_requires_no_action() -> None:
    result = make_loop().run(
        observe=lambda n: "already complete",
        choose=lambda observation, n: None,
        act=lambda action, n: (_ for _ in ()).throw(AssertionError("must not act")),
        verify=lambda action, n: False,
    )

    assert result.result == "clean_no_op"
    assert result.passes == ()


def test_approval_boundary_stops_before_action() -> None:
    acted = []
    result = make_loop().run(
        observe=lambda n: "unsafe change available",
        choose=lambda observation, n: LoopAction("deploy production", requires_approval=True),
        act=lambda action, n: acted.append(action.description),
        verify=lambda action, n: True,
    )

    assert result.result == "approval_required"
    assert acted == []
    assert result.passes[0].approval_required is True


def test_no_progress_stops_after_verified_but_stalled_pass() -> None:
    result = make_loop().run(
        observe=lambda n: f"state-{n}",
        choose=lambda observation, n: LoopAction(f"change-{n}"),
        act=lambda action, n: None,
        verify=lambda action, n: VerificationResult(
            passed=True,
            complete=False,
            progress=(n == 1),
            evidence=(f"check-{n}",),
        ),
    )

    assert result.result == "no_progress"
    assert len(result.passes) == 2
    assert result.passes[-1].verified is True
    assert result.passes[-1].progress is False


def test_execution_error_never_becomes_success() -> None:
    result = make_loop().run(
        observe=lambda n: "state",
        choose=lambda observation, n: LoopAction("change"),
        act=lambda action, n: (_ for _ in ()).throw(RuntimeError("boom")),
        verify=lambda action, n: True,
    )

    assert result.result == "error"
    assert result.passes[0].error.startswith("RuntimeError: boom")


def test_boundary_exhaustion_is_explicit() -> None:
    result = make_loop(limit=2).run(
        observe=lambda n: f"state-{n}",
        choose=lambda observation, n: LoopAction(f"change-{n}"),
        act=lambda action, n: None,
        verify=lambda action, n: VerificationResult(
            passed=True, complete=False, progress=True, evidence=(f"check-{n}",)
        ),
    )

    assert result.result == "exhausted"
    assert len(result.passes) == 2
    assert result.boundary == "max_passes=2"
