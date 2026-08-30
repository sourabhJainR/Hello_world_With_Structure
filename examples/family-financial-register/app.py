from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class FinancialRecord:
    kind: str
    name: str
    institution: str
    reference: str
    document_location: str
    responsible_role: str
    last_reviewed: date
    notes: str = ""

    def is_stale(self, today: date, max_age_days: int = 180) -> bool:
        return (today - self.last_reviewed).days > max_age_days


class FinancialRegister:
    def __init__(self) -> None:
        self._records: list[FinancialRecord] = []

    def add(self, record: FinancialRecord) -> None:
        if not record.name.strip() or not record.institution.strip():
            raise ValueError("name and institution are required")
        if not record.reference.strip():
            raise ValueError("reference is required")
        self._records.append(record)

    def all(self) -> list[FinancialRecord]:
        return sorted(self._records, key=lambda item: (item.kind.lower(), item.name.lower()))

    def stale(self, today: date, max_age_days: int = 180) -> list[FinancialRecord]:
        if max_age_days < 0:
            raise ValueError("max_age_days must be non-negative")
        return [record for record in self.all() if record.is_stale(today, max_age_days)]


if __name__ == "__main__":
    register = FinancialRegister()
    register.add(FinancialRecord(
        kind="investment",
        name="Example Mutual Fund",
        institution="Example Bank",
        reference="FUND-001",
        document_location="secure-documents/investments/",
        responsible_role="family-contact",
        last_reviewed=date(2026, 8, 1),
    ))
    print(f"Records: {len(register.all())}; stale: {len(register.stale(date(2026, 8, 31)))}")
