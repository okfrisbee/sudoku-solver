from dataclasses import dataclass
from typing import Literal


SolverStatus = Literal["solved", "failed", "error", "timeout"]


@dataclass
class SolverResult:
    solution: str | None
    status: SolverStatus
    runtime_seconds: float
    setup_seconds: float | None = None
    solve_seconds: float | None = None
    backtracks: int | None = None
    assignments: int | None = None
    recursive_calls: int | None = None
    error: str | None = None

    @property
    def solved(self) -> bool:
        return self.status == "solved" and self.solution is not None
