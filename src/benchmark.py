"""Run FJSP solvers on datasets listed in fjsp-instances/instances.json."""

import argparse
import csv
import json
import math
import sys
from importlib import import_module
from pathlib import Path, PurePosixPath
from time import perf_counter

from common.data_parser import parse_fjsp_data
from common.result import SolveConfig


SRC = Path(__file__).resolve().parent
INSTANCES = SRC.parent / 'fjsp-instances'


def run_benchmark(records, solvers, time_limit, output):
    failures = 0
    with output.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.writer(stream)
        writer.writerow(['solver', 'dataset', 'instance', 'best_makespan', 'total_time_s', 'optimal', 'status', 'lower_bound', 'termination_reason'])
        for record in records:
            dataset = str(PurePosixPath(record['path']).parent)
            optimum = record.get('optimum')
            bounds = record.get('bounds')
            config = SolveConfig(
                time_limit_s=time_limit,
                lower_bound=bounds['lower'] if bounds is not None else None,
                upper_bound=bounds['upper'] if bounds is not None else None,
            )
            instance = parse_fjsp_data(str(INSTANCES / record['path']))
            for name, solve in solvers.items():
                started = perf_counter()
                optimal = 'false'
                try:
                    result = solve(instance, config)
                except Exception as exc:
                    elapsed = perf_counter() - started
                    failures += 1
                    value = None
                    print(f"{name} {record['path']}: {exc}", file=sys.stderr)
                else:
                    elapsed = result.total_time_s
                    value = result.objective
                    status = result.status
                    result_lb = result.lower_bound
                    termination = result.termination_reason
                    # Only a proven optimal solver status supports 'true'.
                    optimal = 'true' if status == 'OPTIMAL' else 'false'
                    if value is not None and optimum is not None and value < optimum:
                        print(f"New best compared with catalog: {name} {record['path']} "
                              f"({value} < {optimum})", file=sys.stderr)
                writer.writerow([name, dataset, record['name'],
                                 'null' if value is None else value,
                                 elapsed, optimal, status,
                                 'null' if result_lb is None else result_lb,
                                 termination])
                stream.flush()
    return failures


def main():
    modules = {p.parent.name: f'solvers.{p.parent.name}.solver'
               for p in (SRC / 'solvers').glob('*/solver.py')}
    modules['paper'] = 'test.solver'
    modules['gurobi'] = 'solvers.gurobi.solver'
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--solvers', nargs='+', choices=sorted(modules), default=['sat'])
    parser.add_argument('--datasets', '--dataset', nargs='+', required=True,
                        help='Dataset folders, e.g. kacem or hurink/edata')
    parser.add_argument('--time-limit', type=float, help='Search seconds per solver per instance')
    parser.add_argument('--output', type=Path, default=Path('benchmark.csv'))
    args = parser.parse_args()
    if args.time_limit is not None and not (math.isfinite(args.time_limit) and args.time_limit > 0):
        parser.error('--time-limit must be finite and positive')
    catalog = json.loads((INSTANCES / 'instances.json').read_text(encoding='utf-8'))
    datasets = {name.replace('\\', '/').rstrip('/') for name in args.datasets}
    folders = {str(parent) for r in catalog for parent in PurePosixPath(r['path']).parents
               if parent != PurePosixPath('.')}
    unknown = datasets - folders
    if unknown:
        parser.error(f"unknown dataset: {', '.join(sorted(unknown))}. Choices: {', '.join(sorted(folders))}")
    records = [r for r in catalog if any(str(p) in datasets for p in PurePosixPath(r['path']).parents)]
    solvers = {name: import_module(modules[name]).solve for name in args.solvers}
    return int(run_benchmark(records, solvers, args.time_limit, args.output) > 0)


if __name__ == '__main__':
    sys.exit(main())
