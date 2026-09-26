from portable.requirement_contract import Requirement, RequirementContractEngine

def test_build_and_validate():
    e=RequirementContractEngine()
    c=e.build("build app",[Requirement("R1","login",("valid credentials work",))])
    assert c.complete
    assert e.validate(c)==()

def test_duplicate_and_ambiguous_requirements_fail_closed():
    e=RequirementContractEngine()
    try: e.build("x",[Requirement("R1","a",("ok",)),Requirement("R1","b",("ok",))])
    except ValueError: pass
    else: assert False
    c=e.build("x",[Requirement("R1","a",("ok",))],ambiguities=("auth provider",))
    assert e.validate(c)==("unresolved ambiguities remain",)
