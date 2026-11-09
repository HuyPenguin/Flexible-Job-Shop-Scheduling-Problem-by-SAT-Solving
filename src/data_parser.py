"""
Module xử lý dữ liệu đầu vào (data_parser.py)

Đọc file FJSP (format .txt hoặc .json) và trả về FJSPInstance chuẩn.
"""

import json
from dataclasses import dataclass
from typing import Dict, List, Tuple


@dataclass
class FJSPInstance:
    """Cấu trúc dữ liệu chuẩn cho bài toán FJSP.

    Attributes:
        num_jobs:         Số lượng job.
        num_machines:     Số lượng máy.
        operations:       Danh sách mọi nguyên công, dạng (job_id, op_id).
        machines:         [0, 1, …, num_machines-1].
        processing_times: (job_id, op_id) -> {machine_id: thời gian}.
        job_precedences:  Danh sách (op_trước, op_sau) trong cùng job.
    """
    num_jobs: int
    num_machines: int
    operations: List[Tuple[int, int]]
    machines: List[int]
    processing_times: Dict[Tuple[int, int], Dict[int, int]]
    job_precedences: List[Tuple[Tuple[int, int], Tuple[int, int]]]


# ---------------------------------------------------------------------------
#  Parsers
# ---------------------------------------------------------------------------

def parse_fjsp_txt(file_path: str) -> FJSPInstance:
    """Parse file .txt theo format chuẩn Brandimarte / Kacem.

    Dòng 1 : <num_jobs> <num_machines>
    Dòng i+1: <num_ops> rồi với mỗi op: <num_alt> <m1> <p1> <m2> <p2> …
    Machine index bắt đầu từ 0.
    """
    with open(file_path, "r", encoding="utf-8") as fh:
        lines = fh.readlines()

    header = lines[0].split()
    num_jobs, num_machines = int(header[0]), int(header[1])
    machines = list(range(num_machines))

    operations: List[Tuple[int, int]] = []
    processing_times: Dict[Tuple[int, int], Dict[int, int]] = {}
    job_precedences: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []

    for job_id in range(num_jobs):
        tokens = list(map(int, lines[job_id + 1].split()))
        idx = 0
        num_ops = tokens[idx]; idx += 1

        for op_id in range(num_ops):
            key = (job_id, op_id)
            operations.append(key)
            processing_times[key] = {}

            num_alt = tokens[idx]; idx += 1
            for _ in range(num_alt):
                m = tokens[idx]; idx += 1
                p = tokens[idx]; idx += 1
                processing_times[key][m] = p

            if op_id > 0:
                job_precedences.append(((job_id, op_id - 1), key))

    return FJSPInstance(num_jobs, num_machines, operations, machines,
                        processing_times, job_precedences)


def parse_fjsp_json(file_path: str) -> FJSPInstance:
    """Parse file .json (format dùng trong fjsp-instances/)."""
    with open(file_path, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    num_machines = data["machines"]
    machines = list(range(num_machines))
    jobs_data = data["jobs"]
    num_jobs = len(jobs_data)

    operations: List[Tuple[int, int]] = []
    processing_times: Dict[Tuple[int, int], Dict[int, int]] = {}
    job_precedences: List[Tuple[Tuple[int, int], Tuple[int, int]]] = []

    for job_id, job in enumerate(jobs_data):
        for op_id, alts in enumerate(job):
            key = (job_id, op_id)
            operations.append(key)
            processing_times[key] = {a["machine"]: a["processing"] for a in alts}
            if op_id > 0:
                job_precedences.append(((job_id, op_id - 1), key))

    return FJSPInstance(num_jobs, num_machines, operations, machines,
                        processing_times, job_precedences)


def parse_fjsp_data(file_path: str) -> FJSPInstance:
    """Tự động chọn parser dựa trên phần mở rộng file."""
    if file_path.endswith(".json"):
        return parse_fjsp_json(file_path)
    return parse_fjsp_txt(file_path)


# ---------------------------------------------------------------------------
#  Bounds
# ---------------------------------------------------------------------------

def calculate_initial_bounds(instance: FJSPInstance) -> Tuple[int, int]:
    """Trả về (LB, UB) cho makespan.

    LB = max(longest_job, ceil(total_work / num_machines))
    UB = tổng thời gian xử lý tối đa của tất cả nguyên công
    """
    pt = instance.processing_times

    # Nhóm nguyên công theo job_id
    jobs_ops: Dict[int, List[Tuple[int, int]]] = {}
    for op in instance.operations:
        jobs_ops.setdefault(op[0], []).append(op)

    # LB1 — critical-path job: tổng min p cho mỗi job
    lb_job = max(
        sum(min(pt[op].values()) for op in ops)
        for ops in jobs_ops.values()
    )

    # LB2 — machine workload: ceil(total_min_work / num_machines)
    total_min_work = sum(min(pt[op].values()) for op in instance.operations)
    lb_machine = -(-total_min_work // instance.num_machines)

    lb = max(lb_job, lb_machine)

    # UB — tất cả tuần tự, trên máy chậm nhất
    ub = sum(max(pt[op].values()) for op in instance.operations)

    return lb, ub
