"""Compatible with solvers.sat.solver.solve(instance, config)."""
from __future__ import annotations

import math
import time
from itertools import combinations

from common.data_parser import FJSPInstance
from common.result import SolveConfig, SolveResult
from common.schedule import ScheduleEntry, get_makespan


def solve(instance: FJSPInstance, config: SolveConfig | None = None) -> SolveResult:
    """Minimize makespan with assignment and indicator-based disjunctive MIP.

    Operations are indexed by (job_id, op_id). Each operation may be assigned
    to one of the machines in instance.processing_times[operation].
    """
    try:
        import gurobipy as gp
        from gurobipy import GRB
    except ImportError as exc:
        raise ImportError(
            "Gurobi solver requires 'gurobipy'. Install it with 'pip install gurobipy' "
            "and configure a valid Gurobi license."
        ) from exc

    config = config or SolveConfig()
    if config.time_limit_s is not None and (
        not math.isfinite(config.time_limit_s) or config.time_limit_s <= 0
    ):
        raise ValueError('time_limit_s must be finite and positive')

    started = time.perf_counter()
    ops = list(instance.operations)
    pt = instance.processing_times
    machines = list(instance.machines)
    if not ops:
        raise ValueError('An FJSP instance must contain at least one operation')
    for op in ops:
        if not pt[op]:
            raise ValueError(f'Operation {op} has no eligible machines')
        if any(p <= 0 or int(p) != p for p in pt[op].values()):
            raise ValueError(f'Processing times must be positive integers: {op}')

    # Guaranteed feasible upper bound for a conventional FJSP with acyclic
    # job precedence: running every operation sequentially on an eligible machine.
    safe_horizon = sum(max(pt[op].values()) for op in ops)
    # Do not treat catalog upper bounds as hard constraints: they may be stale.

    model = gp.Model('FJSSP_Gurobi')
    model.Params.OutputFlag = 0
    if config.time_limit_s is not None:
        model.Params.TimeLimit = config.time_limit_s

    start = {op: model.addVar(vtype=GRB.INTEGER, lb=0, ub=safe_horizon, name=f's_{op[0]}_{op[1]}') for op in ops}
    finish = {op: model.addVar(vtype=GRB.INTEGER, lb=0, ub=safe_horizon, name=f'c_{op[0]}_{op[1]}') for op in ops}
    assign = {(op, k): model.addVar(vtype=GRB.BINARY, name=f'x_{op[0]}_{op[1]}_{k}') for op in ops for k in machines if k in pt[op]}
    makespan = model.addVar(vtype=GRB.INTEGER, lb=0, ub=safe_horizon,
                            name='C_max')

    # Exactly one eligible machine, and conditional operation duration.
    for op in ops:
        available = [k for k in machines if k in pt[op]]
        model.addConstr(gp.quicksum(assign[op, k] for k in available) == 1,
                        name=f'assign_{op[0]}_{op[1]}')
        for k in available:
            model.addGenConstrIndicator(
                assign[op, k], True, finish[op] == start[op] + pt[op][k],
                name=f'duration_{op[0]}_{op[1]}_{k}'
            )
        model.addConstr(makespan >= finish[op], name=f'makespan_{op[0]}_{op[1]}')

    # Enforce precedence among operations in the same job.
    for predecessor, successor in instance.job_precedences:
        model.addConstr(start[successor] >= finish[predecessor],
                        name=f'precedence_{predecessor[0]}_{predecessor[1]}_'f'{successor[0]}_{successor[1]}')

    # No overlap on any machine. For each pair eligible for machine k, if
    # both use k, select exactly one processing order via directional binaries.
    pair_count = 0
    for k in machines:
        eligible = [op for op in ops if k in pt[op]]
        for a, b in combinations(eligible, 2):
            pair_count += 1
            ab = model.addVar(vtype=GRB.BINARY,name=f'order_{a[0]}_{a[1]}_{b[0]}_{b[1]}_{k}')
            ba = model.addVar(vtype=GRB.BINARY,name=f'order_{b[0]}_{b[1]}_{a[0]}_{a[1]}_{k}')
            model.addConstr(ab + ba >= assign[a, k] + assign[b, k] - 1)
            model.addConstr(ab + ba <= assign[a, k])
            model.addConstr(ab + ba <= assign[b, k])
            model.addGenConstrIndicator(ab, True, start[b] >= finish[a])
            model.addGenConstrIndicator(ba, True, start[a] >= finish[b])

    model.setObjective(makespan, GRB.MINIMIZE)
    model.update()
    built = time.perf_counter()
    model.optimize()
    finished = time.perf_counter()

    # Gurobi supplies a proven dual bound even when the search is interrupted.
    raw_bound = float(model.ObjBound) if model.Status not in (GRB.INFEASIBLE, GRB.INF_OR_UNBD) else None
    proven_lb = (max(0, math.ceil(raw_bound - 1e-6))if raw_bound is not None and math.isfinite(raw_bound) else None)

    has_solution = model.SolCount > 0
    schedule = None
    objective = None
    if has_solution:
        schedule = []
        for op in ops:
            chosen = [k for k in machines if (op, k) in assign and assign[op, k].X > 0.5]
            if len(chosen) != 1:
                raise RuntimeError(f'Unexpected machine assignment for {op}: {chosen}')
            k = chosen[0]
            s = int(round(start[op].X))
            e = s + int(pt[op][k])
            if abs(start[op].X - s) > 1e-4 or abs(finish[op].X - e) > 1e-4:
                raise RuntimeError(f'Non-integral/invalid timings for {op}')
            schedule.append(ScheduleEntry(op[0], op[1], k, s, e))
        objective = get_makespan(schedule)

    if model.Status == GRB.OPTIMAL:
        status, reason = 'OPTIMAL', 'completed'
    elif model.Status == GRB.INFEASIBLE:
        status, reason = 'INFEASIBLE', 'completed'
    elif model.Status == GRB.TIME_LIMIT:
        status, reason = ('FEASIBLE' if has_solution else 'UNKNOWN'), 'time_limit'
    elif model.Status == GRB.INTERRUPTED:
        status, reason = ('FEASIBLE' if has_solution else 'UNKNOWN'), 'interrupted'
    else:
        status, reason = ('FEASIBLE' if has_solution else 'UNKNOWN'), f'gurobi_status_{model.Status}'

    return SolveResult(
        status=status,
        termination_reason=reason,
        objective=objective,
        lower_bound=proven_lb,
        schedule=schedule,
        build_time_s=built - started,
        search_time_s=finished - built,
        total_time_s=finished - started,
        stats={
            'num_vars': model.NumVars,
            'num_constraints': model.NumConstrs,
            'num_general_constraints': model.NumGenConstrs,
            'machine_pairs': pair_count,
            'nodes': model.NodeCount,
            'mip_gap': float(model.MIPGap) if has_solution else None,
            'gurobi_status': int(model.Status),
        },
    )
