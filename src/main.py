"""Command-line entry point for solving one FJSP instance."""
import argparse
import json
from dataclasses import asdict
from math import isfinite
from pathlib import Path
from common.data_parser import parse_fjsp_data
from common.reporting import print_schedule
from common.result import SolveConfig
from importlib import import_module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('instance_file')
    parser.add_argument(
        '--solver', choices=['sat', 'cp', 'mip', 'cp-sat', 'gurobi', 'paper'], default='sat'
    )

    parser.add_argument('--time-limit', type=float,
                        help='Solver search budget in seconds (default: unlimited)')
    parser.add_argument('--output', type=Path, help='Write structured JSON result')
    args = parser.parse_args()
    if args.time_limit is not None and (
        not isfinite(args.time_limit) or args.time_limit <= 0
    ):
        parser.error('--time-limit must be finite and positive')
    instance = parse_fjsp_data(args.instance_file)
    solver_modules = {
        'sat': 'solvers.sat.solver',
        'cp': 'solvers.cp.solver',
        'mip': 'solvers.mip.solver',
        'cp-sat': 'solvers.cp_sat.solver',
        'gurobi': 'solvers.gurobi.solver',
        'paper': 'test.solver',
    }
    solve = import_module(solver_modules[args.solver]).solve

    result = solve(instance, SolveConfig(time_limit_s=args.time_limit))
    print(f'Instance: {args.instance_file}')
    print(f'Status: {result.status} ({result.termination_reason})')
    print(f'Makespan: {result.objective}')
    print(f'Total time: {result.total_time_s:.3f}s')
    print(f'Search time: {result.search_time_s:.3f}s')
    if result.schedule is not None:
        print_schedule(result.schedule)
    if args.output:
        payload = {'instance': args.instance_file, 'solver': args.solver,
                   'config': asdict(SolveConfig(args.time_limit)), **asdict(result)}
        args.output.write_text(json.dumps(payload, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
