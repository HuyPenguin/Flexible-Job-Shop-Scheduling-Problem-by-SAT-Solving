"""
Bộ điều phối chính (main.py)

Kết nối tất cả module:
  data_parser  →  sat_encoder (incremental)  →  schedule_decoder

Luồng:
  1. Parse instance, tính LB / UB.
  2. Mã hoá toàn bộ ràng buộc cấu trúc cho H_max = UB.
  3. Tìm kiếm nhị phân trên [LB, UB]:
       - solve_for(H) sử dụng assumption literal  →  incremental.
       - SAT  ⇒  lưu schedule, UB = H − 1.
       - UNSAT ⇒  LB = H + 1.
  4. In kết quả tối ưu.
"""

import sys
import time

from data_parser import parse_fjsp_data, calculate_initial_bounds
from sat_wrapper import SATWrapper
from sat_encoder import FJSPEncoder
from schedule_decoder import decode_sat_model, print_schedule, get_makespan


def solve_fjsp(file_path: str, per_call_timeout: float = 60.0):
    """Giải bài toán FJSP và in kết quả.

    Args:
        file_path:        Đường dẫn file instance.
        per_call_timeout: Timeout cho mỗi lần gọi solver (giây). Mặc định 60s.
    """

    # ---- 1. Đọc dữ liệu ----
    instance = parse_fjsp_data(file_path)
    lb, ub = calculate_initial_bounds(instance)

    print(f"Instance : {file_path}")
    print(f"Jobs     : {instance.num_jobs}")
    print(f"Machines : {instance.num_machines}")
    print(f"Ops      : {len(instance.operations)}")
    print(f"Bounds   : LB={lb}  UB={ub}")
    print(f"Timeout  : {per_call_timeout}s / solve call")

    # ---- 2. Mã hoá (một lần cho H_max = UB) ----
    t0 = time.perf_counter()

    wrapper = SATWrapper()
    encoder = FJSPEncoder(instance, H_max=ub, wrapper=wrapper)

    encode_time = time.perf_counter() - t0
    print(f"\nEncoding : {encode_time:.2f}s  ({wrapper.num_vars} vars)")

    # ---- 3. Binary search ----
    best_schedule = None
    best_makespan = None
    iteration = 0

    while lb <= ub:
        H = (lb + ub) // 2
        iteration += 1

        t1 = time.perf_counter()
        sat = encoder.solve_for(H, time_budget=per_call_timeout)
        solve_time = time.perf_counter() - t1

        if sat is None:
            # Solver timeout cho lần gọi này — coi như UNSAT, tiếp tục tìm kiếm
            print(f"  [{iteration}] H={H:>4}  TIMEOUT ({solve_time:.2f}s)")
            lb = H + 1
        elif sat:
            true_vars = encoder.get_model()
            schedule = decode_sat_model(true_vars, instance, H)
            makespan = get_makespan(schedule)
            best_schedule = schedule
            best_makespan = makespan

            print(f"  [{iteration}] H={H:>4}  SAT   makespan={makespan}  ({solve_time:.2f}s)")
            ub = H - 1
        else:
            print(f"  [{iteration}] H={H:>4}  UNSAT  ({solve_time:.2f}s)")
            lb = H + 1

    total_time = time.perf_counter() - t0

    # ---- 4. Kết quả ----
    print(f"\n{'=' * 56}")
    if best_schedule is not None:
        print(f" Optimal Makespan : {best_makespan}")
        print(f" Total time       : {total_time:.2f}s  ({iteration} iterations)")
        print(f"{'=' * 56}")
        print_schedule(best_schedule)
    else:
        print(" Không tìm thấy lịch trình khả thi!")
        print(f"{'=' * 56}")

    # Cleanup
    wrapper.delete()

    return best_makespan, best_schedule


# -----------------------------------------------------------------------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python main.py <instance_file>")
        print("  Ví dụ: python main.py ../fjsp-instances/kacem/k1.txt")
        sys.exit(1)

    solve_fjsp(sys.argv[1])

