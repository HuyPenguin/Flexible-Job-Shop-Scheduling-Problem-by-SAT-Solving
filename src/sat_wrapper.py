"""
Lớp trừu tượng giao tiếp với SAT Solver (sat_wrapper.py)

Quản lý ánh xạ tên biến có ý nghĩa (vd: "s_0_1_3") sang ID nguyên dương,
và cung cấp API thống nhất bất kể engine bên dưới (Glucose4, CaDiCaL, …).

Hỗ trợ chế độ *incremental*: solver được giữ nguyên giữa các lần gọi
solve() liên tiếp, chỉ thêm/thay đổi ràng buộc qua assumptions.
"""

import threading
from pysat.solvers import Glucose4


class SATWrapper:
    """Wrapper trừu tượng cho PySAT solver."""

    def __init__(self):
        self._solver = Glucose4()
        self._var_map: dict[str, int] = {}      # name  -> id
        self._rev_map: dict[int, str] = {}       # id    -> name
        self._next_id = 1

    # ----- Quản lý biến -----

    def get_var_id(self, name: str) -> int:
        """Cấp phát hoặc truy xuất ID cho biến *name*."""
        vid = self._var_map.get(name)
        if vid is None:
            vid = self._next_id
            self._var_map[name] = vid
            self._rev_map[vid] = name
            self._next_id += 1
        return vid

    def get_var_name(self, vid: int) -> str | None:
        """Trả tên biến từ ID (hoặc None)."""
        return self._rev_map.get(abs(vid))

    @property
    def num_vars(self) -> int:
        return self._next_id - 1

    # ----- Thêm ràng buộc -----

    def add_clause(self, lits: list[int]):
        """Thêm một mệnh đề CNF (danh sách literal)."""
        self._solver.add_clause(lits)

    def add_exactly_one(self, lits: list[int]):
        """Ép buộc đúng 1 literal trong *lits* là TRUE.

        • At-least-one : (l₁ ∨ l₂ ∨ … ∨ lₙ)
        • At-most-one  : pairwise  (¬lᵢ ∨ ¬lⱼ)  ∀ i < j
        """
        if not lits:
            return
        # at-least-one
        self._solver.add_clause(lits)
        # at-most-one (pairwise)
        for i in range(len(lits)):
            for j in range(i + 1, len(lits)):
                self._solver.add_clause([-lits[i], -lits[j]])

    # ----- Giải & truy xuất -----

    def solve(self, assumptions: list[int] | None = None,
              time_budget: float = 0) -> bool | None:
        """Giải SAT. *assumptions* là danh sách literal giả định (incremental).

        Args:
            assumptions: Danh sách literal giả định.
            time_budget: Timeout cho lần gọi này (giây). 0 = không giới hạn.

        Returns:
            True nếu SAT, False nếu UNSAT, None nếu hết thời gian.
        """
        if time_budget > 0:
            timer = threading.Timer(time_budget, self._solver.interrupt)
            timer.start()
            try:
                result = self._solver.solve_limited(
                    assumptions=assumptions or [],
                    expect_interrupt=True,
                )
            finally:
                timer.cancel()
            if result is None:
                self._solver.clear_interrupt()
            return result
        else:
            return self._solver.solve(assumptions=assumptions or [])

    def get_model(self) -> set[str]:
        """Trả về tập tên biến mang giá trị TRUE trong nghiệm cuối."""
        model = self._solver.get_model()
        if model is None:
            return set()
        return {
            self._rev_map[lit]
            for lit in model
            if lit > 0 and lit in self._rev_map
        }

    def get_raw_model(self) -> list[int] | None:
        """Trả về model thô (list literal) — dùng cho debug."""
        return self._solver.get_model()

    # ----- Lifecycle -----

    def reset(self):
        """Xoá toàn bộ solver, bắt đầu lại từ đầu."""
        self._solver.delete()
        self._solver = Glucose4()
        self._var_map.clear()
        self._rev_map.clear()
        self._next_id = 1

    def delete(self):
        """Giải phóng tài nguyên C++ của solver."""
        if self._solver is not None:
            self._solver.delete()
            self._solver = None

    def __del__(self):
        try:
            self.delete()
        except Exception:
            pass

