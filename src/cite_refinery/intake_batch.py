from __future__ import annotations

from dataclasses import dataclass, field
import csv
from hashlib import sha256
from pathlib import Path
from typing import Any

from .problem_intake import IntakeMode, OwnerConfirmation, OwnerIntake


LIST_FIELDS = {
    "affected_actors",
    "beneficiaries",
    "constraints",
    "available_resources",
    "requested_support",
    "proposed_modes",
    "uncertainties",
    "safeguarding_notes",
    "data_access_notes",
}

REQUIRED_COLUMNS = {
    "title",
    "owner_org",
    "owner_statement",
    "geography",
}


@dataclass(slots=True)
class BatchIntakeRecord:
    row_number: int
    intake: OwnerIntake | None
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    @property
    def valid(self) -> bool:
        return self.intake is not None and not self.errors


def load_owner_intake_csv(path: str | Path) -> list[BatchIntakeRecord]:
    source = Path(path)
    with source.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        fields = set(reader.fieldnames or [])
        missing = sorted(REQUIRED_COLUMNS - fields)
        if missing:
            raise ValueError("batch CSV missing required columns: " + ", ".join(missing))

        records: list[BatchIntakeRecord] = []
        for row_number, raw in enumerate(reader, start=2):
            row = {str(key): (value or "").strip() for key, value in raw.items() if key is not None}
            try:
                intake = _row_to_intake(row, source=source, row_number=row_number)
                report = intake.validation()
                records.append(
                    BatchIntakeRecord(
                        row_number=row_number,
                        intake=intake if report.valid else None,
                        errors=list(report.errors),
                        warnings=list(report.warnings),
                    )
                )
            except (ValueError, TypeError) as exc:
                records.append(BatchIntakeRecord(row_number=row_number, intake=None, errors=[str(exc)]))
        return records


def _row_to_intake(row: dict[str, str], *, source: Path, row_number: int) -> OwnerIntake:
    owner_org = row.get("owner_org", "")
    title = row.get("title", "")
    source_ref = row.get("source_ref") or f"batch:{source.name}#row={row_number}"
    source_system = row.get("source_system") or "institutional-batch"
    intake_id = row.get("intake_id") or _stable_intake_id(owner_org, title, source_ref)
    if not intake_id.startswith("intake:"):
        intake_id = f"intake:{intake_id}"

    intake_mode = row.get("intake_mode") or IntakeMode.INSTITUTIONAL_BATCH.value
    owner_confirmation = row.get("owner_confirmation") or OwnerConfirmation.NOT_CONTACTED.value

    kwargs: dict[str, Any] = {
        "id": intake_id,
        "source_system": source_system,
        "source_ref": source_ref,
        "title": title,
        "owner_org": owner_org,
        "owner_statement": row.get("owner_statement", ""),
        "geography": row.get("geography", ""),
        "intake_mode": intake_mode,
        "owner_confirmation": owner_confirmation,
        "source_observed_at": row.get("source_observed_at") or None,
        "owner_confirmation_ref": row.get("owner_confirmation_ref", ""),
        "owner_confirmed_at": row.get("owner_confirmed_at") or None,
        "schedule": row.get("schedule", ""),
        "notes": row.get("notes", ""),
    }
    for field_name in LIST_FIELDS:
        kwargs[field_name] = _split_list(row.get(field_name, ""))
    return OwnerIntake(**kwargs)


def _stable_intake_id(owner_org: str, title: str, source_ref: str) -> str:
    material = "\n".join([owner_org.strip().casefold(), title.strip().casefold(), source_ref.strip()])
    digest = sha256(material.encode("utf-8")).hexdigest()[:12]
    return f"intake:batch-{digest}"


def _split_list(value: str) -> list[str]:
    return [item.strip() for item in value.split("|") if item.strip()]
