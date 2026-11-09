"""
Module giải mã kết quả từ SAT Solver (schedule_decoder.py)

Dịch ngược tập biến TRUE thành lịch trình thực tế:
  (Job, Operation, Machine, Start, End)
"""

from __future__ import annotations
from dataclasses import dataclass
from data_parser import FJSPInstance


@dataclass
class ScheduleEntry:
    """Một dòng trong bảng lịch trình."""
    job: int
    operation: int
    machine: int
    start: int
    end: int

    @property
    def duration(self) -> int:
        return self.end - self.start


def decode_sat_model(
    true_vars: set[str],
    instance: FJSPInstance,
    H: int,
) -> list[ScheduleEntry]:
    """Giải mã tập biến TRUE thành danh sách ScheduleEntry.

    Lọc các biến:
      • m_{j}_{o}_{k}  →  máy được phân công
      • s_{j}_{o}_{t}  →  thời gian bắt đầu (t nhỏ nhất s = TRUE)
      • f_{j}_{o}_{t}  →  thời gian kết thúc (t nhỏ nhất f = TRUE)
    """
    schedule: list[ScheduleEntry] = []

    for (job_id, op_id) in instance.operations:
        # --- Tìm máy ---
        machine = -1
        for k in instance.processing_times[(job_id, op_id)]:
            if f"m_{job_id}_{op_id}_{k}" in true_vars:
                machine = k
                break

        # --- Thời gian bắt đầu: t nhỏ nhất mà s_{j}_{o}_{t} = TRUE ---
        start = H  # fallback
        for t in range(H + 1):
            if f"s_{job_id}_{op_id}_{t}" in true_vars:
                start = t
                break

        # --- Thời gian kết thúc: t nhỏ nhất mà f_{j}_{o}_{t} = TRUE ---
        end = H
        for t in range(H + 1):
            if f"f_{job_id}_{op_id}_{t}" in true_vars:
                end = t
                break

        schedule.append(ScheduleEntry(job_id, op_id, machine, start, end))

    return schedule


# ---------------------------------------------------------------------------
#  Hiển thị
# ---------------------------------------------------------------------------

def print_schedule(schedule: list[ScheduleEntry]):
    """In bảng lịch trình ra console."""
    schedule_sorted = sorted(schedule, key=lambda e: (e.job, e.operation))

    print(f"\n{'Job':<6}{'Op':<6}{'Machine':<10}{'Start':<8}{'End':<8}{'Duration':<10}")
    print("-" * 48)
    for e in schedule_sorted:
        print(f"{e.job:<6}{e.operation:<6}M{e.machine:<9}{e.start:<8}{e.end:<8}{e.duration:<10}")

    # Gantt theo máy
    machine_map: dict[int, list[ScheduleEntry]] = {}
    for e in schedule:
        machine_map.setdefault(e.machine, []).append(e)

    print("\n--- Gantt theo máy ---")
    for k in sorted(machine_map):
        entries = sorted(machine_map[k], key=lambda e: e.start)
        parts = [f"J{e.job}.{e.operation}[{e.start}-{e.end}]" for e in entries]
        print(f"  M{k}: {', '.join(parts)}")


def get_makespan(schedule: list[ScheduleEntry]) -> int:
    """Trả về makespan (thời gian hoàn thành muộn nhất)."""
    return max(e.end for e in schedule) if schedule else 0

