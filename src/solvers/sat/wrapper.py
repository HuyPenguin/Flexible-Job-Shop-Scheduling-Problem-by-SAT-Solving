"""
Lớp trừu tượng giao tiếp với SAT Solver (sat_wrapper.py)

Quản lý ánh xạ tên biến có ý nghĩa (vd: "s_0_1_3") sang ID nguyên dương,
và cung cấp API thống nhất bất kể engine bên dưới (Glucose4, CaDiCaL, …).

Hỗ trợ chế độ *incremental*: solver được giữ nguyên giữa các lần gọi
solve() liên tiếp, chỉ thêm/thay đổi ràng buộc qua assumptions.
"""

import threading
import time
from itertools import combinations
from math import isqrt
from pysat.solvers import Glucose4


class SATWrapper:
    """Wrapper trừu tượng cho PySAT solver."""

    def __init__(self, engine=Glucose4):
        self._engine = engine
        self._solver = engine()
        self._var_map: dict[str, int] = {}      # name  -> id
        self._rev_map: dict[int, str] = {}       # id    -> name
        self._next_id = 1
        self.search_time_s = 0.0

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
        • At-most-one  : product encoding theo hàng và cột.
        """
        if not lits:
            return
        # at-least-one
        self._solver.add_clause(lits)
        # AMO pairwise cũ:
        # for i in range(len(lits)):
        #     for j in range(i + 1, len(lits)):
        #         self._solver.add_clause([-lits[i], -lits[j]])
        self.add_at_most_one(lits)

    def add_at_most_one(self, lits: list[int]):
        """Gán mỗi literal vào một ô, cho phép chọn tối đa một hàng và một cột."""
        n = len(lits)
        if n < 2:
            return
        if n == 2:
            self.add_clause([-lits[0], -lits[1]])
            return

        width = isqrt(n - 1) + 1
        height = (n + width - 1) // width
        # Dùng ID mới cho biến phụ, kể cả khi caller truyền literal số trực tiếp.
        first = max(self._next_id, self._solver.nof_vars() + 1, max(map(abs, lits)) + 1)
        rows = range(first, first + height)
        cols = range(rows.stop, rows.stop + width)
        self._next_id = cols.stop

        for i, lit in enumerate(lits):
            row, col = divmod(i, width)
            self.add_clause([-lit, rows[row]])
            self.add_clause([-lit, cols[col]])
        for selectors in (rows, cols):
            for a, b in combinations(selectors, 2):
                self.add_clause([-a, -b])

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
                started = time.perf_counter()
                result = self._solver.solve_limited(
                    assumptions=assumptions or [],
                    expect_interrupt=True,
                )
            finally:
                self.search_time_s += time.perf_counter() - started
                timer.cancel()
            if result is None:
                self._solver.clear_interrupt()
            return result
        else:
            started = time.perf_counter()
            try:
                return self._solver.solve(assumptions=assumptions or [])
            finally:
                self.search_time_s += time.perf_counter() - started

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
        self._solver = self._engine()
        self._var_map.clear()
        self._rev_map.clear()
        self._next_id = 1
        self.search_time_s = 0.0

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

