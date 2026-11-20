"""Stable, JSON-serializable result types shared by collectors and frontends."""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from typing import Any


@dataclass(slots=True)
class Finding:
    """A normalized diagnostic finding."""

    code: str
    severity: str
    title: str
    detail: str = ""
    recommendation: str = ""


@dataclass(slots=True)
class DiagnosticResult:
    """Versioned output envelope; collectors must not return UI-specific objects."""

    collector: str
    status: str
    data: dict[str, Any] = field(default_factory=dict)
    interface: str | None = None
    findings: list[Finding] = field(default_factory=list)
    limitations: list[str] = field(default_factory=list)
    schema_version: int = 1
    started_at: str = field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    def to_dict(self) -> dict[str, Any]:
        """Return a JSON-compatible representation."""
        return asdict(self)
