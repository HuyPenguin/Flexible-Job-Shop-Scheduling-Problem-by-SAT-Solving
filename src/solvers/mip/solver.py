"""FJSP solver using CPLEX MIP through DOcplex MP."""

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
    """Solve an FJSP with assignment and pairwise disjunctive constraints.

    Requires ``docplex``, the CPLEX Python API, and a valid CPLEX license.
    """
    config = config or SolveConfig()
    validate_instance(instance, config)
    if not instance.operations:
        return empty_result("cplex_mip")

    try:
        from docplex.mp.model import Model
    except ImportError as exc:
        raise ImportError(
            "The MIP solver requires DOcplex and CPLEX; install the CPLEX Python API "
            "and `python -m pip install docplex`."
        ) from exc

    started = perf_counter()
    horizon = config.horizon(instance)
    model = Model(name="fjssp-cplex-mip")
    model.log_output = False

    starts = {
        operation: model.integer_var(
            lb=0,
            ub=horizon,
            name=f"start_{operation[0]}_{operation[1]}",
        )
        for operation in instance.operations
    }
    completions = {
        operation: model.integer_var(
            lb=0,
            ub=horizon,
            name=f"end_{operation[0]}_{operation[1]}",
        )
        for operation in instance.operations
    }
    makespan = model.integer_var(lb=config.lower_bound or 0, ub=horizon, name="makespan")
    assignments = {}

    for operation in instance.operations:
        durations = instance.processing_times[operation]
        for machine in durations:
            assignments[operation, machine] = model.binary_var(
                name=f"assign_{operation[0]}_{operation[1]}_{machine}"
            )

        model.add_constraint(
            model.sum(assignments[operation, machine] for machine in durations) == 1
        )
        model.add_constraint(
            completions[operation]
            == starts[operation]
            + model.sum(
                duration * assignments[operation, machine]
                for machine, duration in durations.items()
            )
        )
        model.add_constraint(completions[operation] <= makespan)

    for before, after in instance.job_precedences:
        model.add_constraint(completions[before] <= starts[after])

    operations_by_machine = {
        machine: [
            operation
            for operation in instance.operations
            if machine in instance.processing_times[operation]
        ]
        for machine in instance.machines
    }
    for machine, operations in operations_by_machine.items():
        for index, first in enumerate(operations):
            for second in operations[index + 1:]:
                first_before_second = model.binary_var(
                    name=(
                        f"before_{first[0]}_{first[1]}_"
                        f"{second[0]}_{second[1]}_m_{machine}"
                    )
                )
                first_assignment = assignments[first, machine]
                second_assignment = assignments[second, machine]

                model.add_constraint(
                    completions[first]
                    <= starts[second]
                    + horizon * (1 - first_before_second)
                    + horizon * (2 - first_assignment - second_assignment)
                )
                model.add_constraint(
                    completions[second]
                    <= starts[first]
                    + horizon * first_before_second
                    + horizon * (2 - first_assignment - second_assignment)
                )

    model.minimize(makespan)
    if config.time_limit_s is not None:
        model.parameters.timelimit = config.time_limit_s

    build_time = perf_counter() - started
    search_started = perf_counter()
    solution = model.solve()
    finished = perf_counter()
    search_time = finished - search_started
    details = model.solve_details
    solver_status = details.status if details is not None else "unknown"
    status_text = str(solver_status).lower()

    if solution is None:
        if "infeasible" in status_text:
            status = "INFEASIBLE"
        elif any(token in status_text for token in ("time limit", "limit", "abort", "unknown")):
            status = "UNKNOWN"
        else:
            raise RuntimeError(f"CPLEX returned no solution (status: {solver_status})")
        objective = None
        lower_bound = None
        schedule = None
    else:
        objective = int(round(solution.get_value(makespan)))
        schedule = []
        for operation in instance.operations:
            selected_machine = next(
                machine
                for machine in instance.processing_times[operation]
                if solution.get_value(assignments[operation, machine]) > 0.5
            )
            start = int(round(solution.get_value(starts[operation])))
            duration = instance.processing_times[operation][selected_machine]
            schedule.append(
                ScheduleEntry(
                    job=operation[0],
                    operation=operation[1],
                    machine=selected_machine,
                    start=start,
                    end=start + duration,
                )
            )

        status = "OPTIMAL" if "optimal" in status_text else "FEASIBLE"
        best_bound = details.best_bound if details is not None else None
        lower_bound = float(best_bound) if best_bound is not None and isfinite(best_bound) else None
        if status == "OPTIMAL":
            lower_bound = float(objective)

    return SolveResult(
        status=status,
        termination_reason=f"cplex:{solver_status}",
        objective=objective,
        lower_bound=lower_bound,
        schedule=schedule,
        build_time_s=build_time,
        search_time_s=search_time,
        total_time_s=finished - started,
        stats={
            "solver": "cplex_mip",
            "num_operations": len(instance.operations),
            "num_machines": len(instance.machines),
            "num_variables": model.number_of_variables,
            "num_constraints": model.number_of_constraints,
        },
    )
