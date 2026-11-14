"""Shared solver configuration and results; times are in seconds."""
from dataclasses import dataclass, field
from typing import Literal
from .schedule import ScheduleEntry

@dataclass
class SolveConfig:
    time_limit_s: float | None = None

@dataclass
class SolveResult:
    status: Literal['OPTIMAL', 'FEASIBLE', 'INFEASIBLE', 'UNKNOWN', 'ERROR']
    termination_reason: str
    objective: int | None
    lower_bound: float | None
    schedule: list[ScheduleEntry] | None
    build_time_s: float
    search_time_s: float
    total_time_s: float
    stats: dict = field(default_factory=dict)
