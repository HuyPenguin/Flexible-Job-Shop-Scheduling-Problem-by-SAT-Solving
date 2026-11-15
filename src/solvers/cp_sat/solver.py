"""FJSP solver using optional intervals and no-overlap constraints in CP-SAT."""

from __future__ import annotations

from math import isfinite
from time import perf_counter

from common.data_parser import FJSPInstance
from common.result import SolveConfig, SolveResult
from common.schedule import ScheduleEntry
from solvers._utils import empty_result, validate_instance


def solve(
    instance: FJSPInstance,
    config: SolveConfig | None = None,
) -> SolveResult:
    """Solve an FJSP instance with OR-Tools CP-SAT.

    Requires the ``ortools`` package. The model uses an optional interval for
    each eligible operation-machine pair and exactly one selected alternative.
    """
    config = config or SolveConfig()
    horizon = validate_instance(instance, config)
    if not instance.operations:
        return empty_result("cp_sat")

    try:
        from ortools.sat.python import cp_model
    except ImportError as exc:
        raise ImportError(
            "The CP-SAT solver requires OR-Tools; install it with "
            "`python -m pip install ortools`."
        ) from exc

    started = perf_counter()
    model = cp_model.CpModel()
    starts = {}
    ends = {}
    assignments = {}
    machine_intervals = {machine: [] for machine in instance.machines}

    for operation in instance.operations:
        job_id, operation_id = operation
        start = model.NewIntVar(0, horizon, f"start_{job_id}_{operation_id}")
        end = model.NewIntVar(0, horizon, f"end_{job_id}_{operation_id}")
        starts[operation] = start
        ends[operation] = end

        choices = []
        for machine, duration in instance.processing_times[operation].items():
            selected = model.NewBoolVar(
                f"assign_{job_id}_{operation_id}_{machine}"
            )
            interval = model.NewOptionalIntervalVar(
                start,
                duration,
                end,
                selected,
                f"interval_{job_id}_{operation_id}_{machine}",
            )
            assignments[operation, machine] = selected
            machine_intervals[machine].append(interval)
            choices.append(selected)

        model.AddExactlyOne(choices)

    for before, after in instance.job_precedences:
        model.Add(ends[before] <= starts[after])

    for intervals in machine_intervals.values():
        if len(intervals) > 1:
            model.AddNoOverlap(intervals)

    makespan = model.NewIntVar(0, horizon, "makespan")
    for operation in instance.operations:
        model.Add(ends[operation] <= makespan)
    model.Minimize(makespan)

    build_time = perf_counter() - started
    solver = cp_model.CpSolver()
    solver.parameters.num_search_workers = 1
    if config.time_limit_s is not None:
        solver.parameters.max_time_in_seconds = config.time_limit_s

    search_started = perf_counter()
    solver_status = solver.Solve(model)
    finished = perf_counter()
    search_time = finished - search_started
    status_name = solver.StatusName(solver_status)

    if solver_status == cp_model.OPTIMAL:
        status = "OPTIMAL"
    elif solver_status == cp_model.FEASIBLE:
        status = "FEASIBLE"
    elif solver_status == cp_model.INFEASIBLE:
        status = "INFEASIBLE"
    elif solver_status == cp_model.UNKNOWN:
        status = "UNKNOWN"
    elif solver_status == cp_model.MODEL_INVALID:
        raise RuntimeError(f"CP-SAT rejected the model: {solver.ResponseStats()}")
    else:
        raise RuntimeError(f"CP-SAT returned an unexpected status: {status_name}")

    objective = None
    lower_bound = None
    schedule = None
    if status in ("OPTIMAL", "FEASIBLE"):
        objective = int(round(solver.ObjectiveValue()))
        bound = solver.BestObjectiveBound()
        if isfinite(bound):
            lower_bound = float(bound)
        if status == "OPTIMAL":
            lower_bound = float(objective)

        schedule = []
        for operation in instance.operations:
            selected_machine = next(
                machine
                for machine in instance.processing_times[operation]
                if solver.Value(assignments[operation, machine])
            )
            schedule.append(
                ScheduleEntry(
                    job=operation[0],
                    operation=operation[1],
                    machine=selected_machine,
                    start=solver.Value(starts[operation]),
                    end=solver.Value(ends[operation]),
                )
            )

    return SolveResult(
        status=status,
        termination_reason=f"cp_sat:{status_name}",
        objective=objective,
        lower_bound=lower_bound,
        schedule=schedule,
        build_time_s=build_time,
        search_time_s=search_time,
        total_time_s=finished - started,
        stats={
            "solver": "cp_sat",
            "num_operations": len(instance.operations),
            "num_machines": len(instance.machines),
            "num_conflicts": solver.NumConflicts(),
            "num_branches": solver.NumBranches(),
            "num_search_workers": solver.parameters.num_search_workers,
        },
    )
