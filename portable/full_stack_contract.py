"""Frontend/backend contract alignment for full-stack work."""
from __future__ import annotations
from dataclasses import dataclass
from typing import Sequence

@dataclass(frozen=True)
class ContractEndpoint:
    method: str
    path: str
    request: str
    response: str
    errors: tuple[str,...]=()

@dataclass(frozen=True)
class FullStackContract:
    frontend_states: tuple[str,...]
    endpoints: tuple[ContractEndpoint,...]
    data_invariants: tuple[str,...]
    e2e_scenarios: tuple[str,...]

    @property
    def complete(self)->bool:
        return bool(self.frontend_states and self.endpoints and self.data_invariants and self.e2e_scenarios)

class FullStackContractEngine:
    def build(self, frontend_states:Sequence[str], endpoints:Sequence[ContractEndpoint], data_invariants:Sequence[str], e2e_scenarios:Sequence[str])->FullStackContract:
        fs=tuple(x.strip() for x in frontend_states if x.strip()); ep=tuple(endpoints); di=tuple(x.strip() for x in data_invariants if x.strip()); e2e=tuple(x.strip() for x in e2e_scenarios if x.strip())
        if not fs or not ep or not di or not e2e: raise ValueError("full-stack contract requires UI, API, data and E2E contracts")
        for x in ep:
            if x.method.upper() not in {"GET","POST","PUT","PATCH","DELETE"} or not x.path.startswith("/") or not x.request or not x.response: raise ValueError("invalid endpoint contract")
        return FullStackContract(fs,ep,di,e2e)
    def validate(self,c:FullStackContract)->tuple[str,...]:
        issues=[]
        if not c.complete: issues.append("full-stack contract incomplete")
        paths={(e.method.upper(),e.path) for e in c.endpoints}
        if len(paths)!=len(c.endpoints): issues.append("duplicate API endpoint")
        return tuple(issues)

__all__=["ContractEndpoint","FullStackContract","FullStackContractEngine"]
