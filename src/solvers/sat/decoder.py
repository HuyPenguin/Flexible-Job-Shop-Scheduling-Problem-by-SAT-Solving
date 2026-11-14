from common.data_parser import FJSPInstance
from common.schedule import ScheduleEntry


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


