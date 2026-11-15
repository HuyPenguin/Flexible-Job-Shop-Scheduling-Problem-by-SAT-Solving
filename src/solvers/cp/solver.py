"""FJSP solver using IBM ILOG CP Optimizer through DOcplex CP."""

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
    """Solve an FJSP instance with optional intervals and machine no-overlap.

    Requires ``docplex`` and an accessible IBM ILOG CP Optimizer executable.
    """
    config = config or SolveConfig()
    validate_instance(instance, config)
    if not instance.operations:
        return empty_result("cpoptimizer")

    try:
        from docplex.cp.model import CpoModel
    except ImportError as exc:
        raise ImportError(
            "The CP solver requires DOcplex; install it with `python -m pip install docplex`."
        ) from exc

    started = perf_counter()
    horizon = config.horizon(instance)
    model = CpoModel(name="fjssp-cp")
    masters = {}
    alternatives = {}
    machine_intervals = {machine: [] for machine in instance.machines}

    for operation in instance.operations:
        durations = instance.processing_times[operation]
        master = model.interval_var(
            name=f"op_{operation[0]}_{operation[1]}",
            size=(min(durations.values()), max(durations.values())),
        )
        masters[operation] = master

        operation_alternatives = {}
        for machine, duration in durations.items():
            interval = model.interval_var(
                name=f"op_{operation[0]}_{operation[1]}_m_{machine}",
                optional=True,
                size=duration,
            )
            operation_alternatives[machine] = interval
            machine_intervals[machine].append(interval)

        alternatives[operation] = operation_alternatives
        model.add(model.alternative(master, list(operation_alternatives.values())))
        model.add(model.end_of(master) <= horizon)

    for before, after in instance.job_precedences:
        model.add(model.end_before_start(masters[before], masters[after]))

    for intervals in machine_intervals.values():
        if len(intervals) > 1:
            model.add(model.no_overlap(intervals))

    makespan = model.max([model.end_of(masters[op]) for op in instance.operations])
    if config.lower_bound is not None:
        model.add(makespan >= config.lower_bound)
    model.minimize(makespan)
    if config.time_limit_s is not None:
        model.set_parameters(TimeLimit=config.time_limit_s)

    build_time = perf_counter() - started
    search_started = perf_counter()
    solution = model.solve(LogVerbosity="Quiet")
    finished = perf_counter()
    search_time = finished - search_started

    solve_status = solution.get_solve_status() if solution is not None else "Unknown"
    status_text = str(solve_status).lower()
    objective_value = solution.get_objective_value() if solution is not None else None
    objective = int(round(objective_value)) if objective_value is not None else None

    if "optimal" in status_text and objective is not None:
        status = "OPTIMAL"
    elif objective is not None:
        status = "FEASIBLE"
    elif "infeasible" in status_text:
        status = "INFEASIBLE"
    elif any(token in status_text for token in ("unknown", "stopped", "limit", "fail")):
        status = "UNKNOWN"
    else:
        raise RuntimeError(f"CP Optimizer returned no solution (status: {solve_status})")

    schedule = None
    if objective is not None:
        schedule = []
        for operation in instance.operations:
            master_solution = solution.get_var_solution(masters[operation])
            selected_machine = next(
                machine
                for machine, interval in alternatives[operation].items()
                if solution.get_var_solution(interval).is_present()
            )
            schedule.append(
                ScheduleEntry(
                    job=operation[0],
                    operation=operation[1],
                    machine=selected_machine,
                    start=master_solution.get_start(),
                    end=master_solution.get_end(),
                )
            )

    lower_bound = None
    if solution is not None:
        bound = solution.get_objective_bound()
        if bound is not None and isfinite(bound):
            lower_bound = float(bound)
    if status == "OPTIMAL":
        lower_bound = float(objective)

    return SolveResult(
        status=status,
        termination_reason=f"cpoptimizer:{solve_status}",
        objective=objective,
        lower_bound=lower_bound,
        schedule=schedule,
        build_time_s=build_time,
        search_time_s=search_time,
        total_time_s=finished - started,
        stats={
            "solver": "cpoptimizer",
            "num_operations": len(instance.operations),
            "num_machines": len(instance.machines),
        },
    )
