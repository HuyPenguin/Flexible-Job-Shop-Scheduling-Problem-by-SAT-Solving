"""Shared validation helpers for exact FJSP solvers."""

from math import isfinite

from common.data_parser import FJSPInstance
from common.result import SolveConfig, SolveResult


def validate_instance(instance: FJSPInstance, config: SolveConfig) -> int:
    """Validate solver inputs and return a feasible serial-schedule horizon."""
    if config.time_limit_s is not None and (
        not isfinite(config.time_limit_s) or config.time_limit_s <= 0
    ):
        raise ValueError("time_limit_s must be finite and positive")

    operations = instance.operations
    if len(set(operations)) != len(operations):
        raise ValueError("instance.operations contains duplicate operations")

    known_operations = set(operations)
    horizon = 0
    for operation in operations:
        alternatives = instance.processing_times.get(operation)
        if not alternatives:
            raise ValueError(f"operation {operation} has no eligible machine")
        for machine, duration in alternatives.items():
            if machine not in instance.machines:
                raise ValueError(
                    f"operation {operation} refers to unknown machine {machine}"
                )
            if isinstance(duration, bool) or not isinstance(duration, int) or duration <= 0:
                raise ValueError(
                    f"operation {operation} has invalid processing time {duration!r}"
                )
        horizon += max(alternatives.values())

    successors = {operation: [] for operation in operations}
    indegree = dict.fromkeys(operations, 0)
    for before, after in instance.job_precedences:
        if before not in known_operations or after not in known_operations:
            raise ValueError(f"precedence ({before}, {after}) references an unknown operation")
        successors[before].append(after)
        indegree[after] += 1

    ready = [operation for operation in operations if indegree[operation] == 0]
    visited = 0
    while ready:
        operation = ready.pop()
        visited += 1
        for successor in successors[operation]:
            indegree[successor] -= 1
            if indegree[successor] == 0:
                ready.append(successor)
    if visited != len(operations):
        raise ValueError("job_precedences contains a cycle")

    return horizon


def empty_result(solver_name: str) -> SolveResult:
    """Return the exact result for an instance without operations."""
    return SolveResult(
        status="OPTIMAL",
        termination_reason="empty_instance",
        objective=0,
        lower_bound=0,
        schedule=[],
        build_time_s=0.0,
        search_time_s=0.0,
        total_time_s=0.0,
        stats={"solver": solver_name, "num_operations": 0},
    )
