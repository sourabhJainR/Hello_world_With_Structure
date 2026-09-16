"""Small deterministic example of evidence-backed improvement gating."""
from portable.empirical_improvement import EmpiricalImprovement, ImprovementObservation


CASES = ("context", "verification", "repair")


def evaluate(case: str, strategy: str) -> ImprovementObservation:
    if strategy == "baseline":
        values = {
            "context": (0.82, 2, 0.80),
            "verification": (0.84, 3, 0.82),
            "repair": (0.78, 2, 0.76),
        }
    else:
        values = {
            "context": (0.94, 1, 0.92),
            "verification": (0.93, 2, 0.91),
            "repair": (0.90, 1, 0.89),
        }
    score, iterations, confidence = values[case]
    return ImprovementObservation(case, strategy, score, iterations, confidence, (f"{case}:{strategy}",))


def main() -> None:
    report = EmpiricalImprovement.run(CASES, "baseline", "candidate", evaluate)
    print({
        "accepted": report.accepted,
        "score_delta": report.score_delta,
        "iteration_delta": report.iteration_delta,
        "calibration_delta": report.calibration_delta,
        "digest": report.digest,
        "reason": report.reason,
    })


if __name__ == "__main__":
    main()
