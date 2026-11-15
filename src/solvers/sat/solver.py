"""Incremental SAT with a shared per-instance time budget."""
import time
from common.data_parser import FJSPInstance, calculate_initial_bounds
from common.result import SolveConfig, SolveResult
from common.schedule import get_makespan
from .decoder import decode_sat_model
from .encoder import FJSPEncoder
from .wrapper import SATWrapper


def solve(instance: FJSPInstance, config: SolveConfig | None = None) -> SolveResult:
    config = config or SolveConfig()
    if config.time_limit_s is not None and config.time_limit_s <= 0:
        raise ValueError('time_limit_s must be positive')
    started = time.perf_counter()
    lb, ub = calculate_initial_bounds(instance)
    best_schedule = None
    best_makespan = None
    iterations = 0
    reason = 'completed'
    sequential = False
    wrapper = SATWrapper()
    try:
        encoder = FJSPEncoder(instance, H_max=ub, wrapper=wrapper)
        built = time.perf_counter()
        while lb <= ub:
            remaining = 0.0  # SATWrapper uses zero for an unlimited call.
            if config.time_limit_s is not None:
                remaining = config.time_limit_s - wrapper.search_time_s
                if remaining <= 0:
                    reason = 'time_limit'
                    break
            horizon = ub if sequential else (lb + ub) // 2
            iterations += 1
            # Reserve half the remaining SAT time for fallback if this probe stalls.
            budget = remaining if sequential else remaining / 5
            print(f"Probing horizon {horizon} with {budget:.3f}s remaining", flush=True)
            sat = encoder.solve_for(horizon, time_budget=budget)
            if sat is None:
                # An interrupted call proves nothing about this horizon.
                if not sequential:
                    sequential = True
                    continue
                reason = 'time_limit'
                
                break
            if sat:
                print("SAT at horizon", horizon, flush=True)
                best_schedule = decode_sat_model(encoder.get_model(), instance, horizon)
                best_makespan = get_makespan(best_schedule)
                ub = best_makespan - 1
            else:
                lb = horizon + 1
                print("UNSAT at horizon", horizon, flush=True)
        finished = time.perf_counter()
        if best_makespan is not None:
            status = 'OPTIMAL' if lb >= best_makespan else 'FEASIBLE'
        else:
            status = 'INFEASIBLE' if reason == 'completed' else 'UNKNOWN'
        return SolveResult(
            status=status, termination_reason=reason,
            objective=best_makespan, lower_bound=lb, schedule=best_schedule,
            build_time_s=built-started, search_time_s=wrapper.search_time_s,
            total_time_s=finished-started,
            stats={'iterations': iterations, 'num_vars': wrapper.num_vars},
        )
    finally:
        wrapper.delete()
