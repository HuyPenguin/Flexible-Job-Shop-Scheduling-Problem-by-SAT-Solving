"""Shared solver configuration and results; times are in seconds."""
from dataclasses import dataclass, field
from typing import Literal
from .data_parser import FJSPInstance, calculate_upper_bound
from .schedule import ScheduleEntry

@dataclass
class SolveConfig:
    time_limit_s: float | None = None
    lower_bound: int | None = None
    upper_bound: int | None = None

    def horizon(self, instance: FJSPInstance) -> int:
        if self.upper_bound is not None:
            return self.upper_bound
        return calculate_upper_bound(instance)

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
