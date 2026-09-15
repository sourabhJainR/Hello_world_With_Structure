from portable.context_engine import ContextEngine, ContextItem, ContextPolicy, handoff_from_output


def test_context_deduplicates_and_prefers_verified_relevant_items():
    engine = ContextEngine(ContextPolicy(max_chars=180, max_items=3, max_item_chars=80))
    items = [
        ContextItem("output", "same finding", source="a", priority=10),
        ContextItem("evidence", "same finding", source="b", priority=10, verified=True),
        ContextItem("handoff", "next step", source="planner", priority=20),
        ContextItem("output", "irrelevant long context " * 20, source="old"),
    ]
    selected = engine.select(items)
    assert len(selected) <= 3
    assert any(item.kind == "evidence" and item.verified for item in selected)
    assert len(engine.pack(items)) <= 180


def test_handoff_is_bounded_and_has_explicit_sections():
    handoff = handoff_from_output(
        task_id="t1", sender="builder", receiver="verifier", objective="verify the change",
        output="FACTS\n" + ("x" * 10000), files=["src/a.py"], max_chars=500,
    )
    rendered = handoff.render(700)
    assert len(rendered) <= 700
    assert "OBJECTIVE" in rendered
    assert "NEXT" in rendered
    assert "src/a.py" in rendered


def test_context_never_requires_a_model():
    engine = ContextEngine()
    assert engine.pack([ContextItem("contract", "do the task")]) == "### contract\ndo the task"
