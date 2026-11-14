"""
Module mã hoá bài toán FJSP thành CNF (sat_encoder.py)

Sử dụng kỹ thuật **Order encoding of time** theo encoding.md.
Hỗ trợ **incremental SAT**: mã hoá một lần cho H_max, rồi dùng
assumption literal để thử các deadline H nhỏ hơn mà không cần
tạo lại solver.

Ý tưởng incremental:
  • Mã hoá toàn bộ ràng buộc cấu trúc (monotonicity, rule 2, precedence,
    machine assignment, capacity) cho H_max.
  • Ràng buộc deadline (goal): thay vì unit clause  (f_{i,H}), ta dùng
        act_H  →  f_{i,H}     tức     (¬act_H ∨ f_{i,H})
    với act_H là một *activation literal* duy nhất cho mỗi giá trị H.
  • Khi gọi solve, truyền assumptions=[act_H] để kích hoạt đúng deadline.
  • Khi chuyển sang H' < H (UNSAT ⇒ tăng LB) hoặc H' > H (SAT ⇒ giảm UB),
    ta chỉ cần tạo act_H' mới (nếu chưa có), thêm clause liên kết, rồi
    solve(assumptions=[act_H']).  Các clause cũ vẫn giữ nguyên.
"""

from __future__ import annotations
from common.data_parser import FJSPInstance
from .wrapper import SATWrapper


class FJSPEncoder:
    """Bộ mã hoá FJSP → CNF với hỗ trợ incremental deadline."""

    def __init__(self, instance: FJSPInstance, H_max: int, wrapper: SATWrapper):
        self.inst = instance
        self.H_max = H_max
        self.w = wrapper

        # Cache act literals đã tạo cho từng giá trị H
        self._act_cache: dict[int, int] = {}

        # Pre-compute danh sách op khả dụng cho mỗi máy
        self._ops_per_machine: dict[int, list[tuple[int, int]]] = {}
        for op in instance.operations:
            for k in instance.processing_times[op]:
                self._ops_per_machine.setdefault(k, []).append(op)

        # Mã hoá toàn bộ ràng buộc cấu trúc
        self._encode_structural()

    # ==================================================================
    #  Tên biến  →  var_id   (helper)
    # ==================================================================

    def _s(self, i: tuple, t: int) -> int:
        return self.w.get_var_id(f"s_{i[0]}_{i[1]}_{t}")

    def _f(self, i: tuple, t: int) -> int:
        return self.w.get_var_id(f"f_{i[0]}_{i[1]}_{t}")

    def _m(self, i: tuple, k: int) -> int:
        return self.w.get_var_id(f"m_{i[0]}_{i[1]}_{k}")

    def _r(self, i: tuple, t: int) -> int:
        return self.w.get_var_id(f"r_{i[0]}_{i[1]}_{t}")

    def _a(self, i: tuple, k: int, t: int) -> int:
        return self.w.get_var_id(f"a_{i[0]}_{i[1]}_{k}_{t}")

    # ==================================================================
    #  Mã hoá cấu trúc (gọi 1 lần cho H_max)
    # ==================================================================

    def _encode_structural(self):
        H = self.H_max
        ops = self.inst.operations
        pt = self.inst.processing_times
        # --- 3. Order encoding of time ---
        for i in ops:
            for t in range(H):
                # 1a  s_{i,t} → s_{i,t+1}
                self.w.add_clause([-self._s(i, t), self._s(i, t + 1)])
                # 1b  f_{i,t} → f_{i,t+1}
                self.w.add_clause([-self._f(i, t), self._f(i, t + 1)])
                # 3   s_{i,t} ∧ ¬f_{i,t} → r_{i,t}
                self.w.add_clause([-self._s(i, t), self._f(i, t), self._r(i, t)])

            # Rule 2 — cho mỗi máy khả dụng
            available = [k for k in self.inst.machines if k in pt[i]]
            for k in available:
                p = pt[i][k]
                # Boundary: t < p  ⇒  s_{i,t-p} xem như FALSE
                #   m_{i,k} → ¬f_{i,t}
                for t in range(min(p, H + 1)):
                    self.w.add_clause([-self._m(i, k), -self._f(i, t)])
                # t ≥ p
                for t in range(p, H + 1):
                    # m_{i,k} → (f_{i,t} ↔ s_{i,t-p})
                    self.w.add_clause([-self._m(i, k), -self._f(i, t),
                                       self._s(i, t - p)])
                    self.w.add_clause([-self._m(i, k),  self._f(i, t),
                                      -self._s(i, t - p)])
        
        # --- 4. Ràng buộc Job & Máy ---

        # Precedence
        for (op_i, op_j) in self.inst.job_precedences:
            for t in range(H + 1):
                # s_{j,t} → f_{i,t}
                self.w.add_clause([-self._s(op_j, t), self._f(op_i, t)])
        
        # Exactly-one machine
        for i in ops:
            available = [k for k in self.inst.machines if k in pt[i]]
            self.w.add_exactly_one([self._m(i, k) for k in available])
        
        # Machine assignment → activity
        for i in ops:
            available = [k for k in self.inst.machines if k in pt[i]]
            for k in available:
                for t in range(H):
                    # m_{i,k} ∧ r_{i,t} → a_{i,k,t}
                    self.w.add_clause([-self._m(i, k), -self._r(i, t),
                                       self._a(i, k, t)])
        
        # Capacity: tối đa 1 op trên mỗi máy mỗi slot
        # Mỗi máy có thể rảnh hoặc chạy một nguyên công trong slot t.
        for k in self.inst.machines:
            ops_k = self._ops_per_machine.get(k, [])
            if len(ops_k) < 2:
                continue

            for t in range(H):
                activity_lits = [self._a(op, k, t) for op in ops_k]
                self.w.add_at_most_one(activity_lits)
        
    # ==================================================================
    #  Incremental deadline
    # ==================================================================

    def _get_act(self, H: int) -> int:
        """Trả về activation literal cho deadline H (tạo mới nếu cần)."""
        if H in self._act_cache:
            return self._act_cache[H]

        act = self.w.get_var_id(f"__act_{H}")
        self._act_cache[H] = act

        # act_H  →  f_{i,H}   cho mọi op i
        for i in self.inst.operations:
            self.w.add_clause([-act, self._f(i, H)])

        return act

    def solve_for(self, H: int, time_budget: float = 0) -> bool | None:
        """Kiểm tra tính khả thi với deadline H (incremental).

        Returns: True (SAT), False (UNSAT), None (timeout).
        """
        if H < 0 or H > self.H_max:
            return False
        act = self._get_act(H)
        return self.w.solve(assumptions=[act], time_budget=time_budget)

    def get_model(self) -> set[str]:
        """Trả về tập tên biến TRUE của nghiệm vừa tìm."""
        return self.w.get_model()

