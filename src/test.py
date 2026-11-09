from pysat.solvers import Glucose3

def SATSolver():
    return Glucose3()

def s(i, t):

def encode_fjsp_order_encoding(operations, machines, processing_times, job_precedences, H):
    """
    operations: Danh sách các nguyên công i.
    machines: Danh sách các máy k.
    processing_times: Dictionary p[i][k] lưu thời gian xử lý của nguyên công i trên máy k.
    job_precedences: Danh sách các cặp (i, j) trong đó nguyên công j chạy sau nguyên công i trong cùng một job.
    H: Thời hạn (deadline) của toàn bộ lịch trình.
    """
    sat_solver = SATSolver() # Khởi tạo bộ giải SAT giả định

    # --- ĐỊNH NGHĨA BIẾN (Tương ứng với ảnh 4) ---
    # s[i, t]: nguyên công i đã bắt đầu tính đến thời điểm t
    # f[i, t]: nguyên công i đã kết thúc tính đến thời điểm t
    # m[i, k]: nguyên công i được phân công cho máy k
    # r[i, t]: nguyên công i đang chạy (running) tại khe thời gian t
    # a[i, k, t]: nguyên công i đang chạy trên máy k tại khe thời gian t
    
    # --- RÀNG BUỘC THỜI GIAN VÀ TRẠNG THÁI (Order encoding of time - Ảnh 1) ---
    for i in operations:
        for t in range(H):
            # 1a. Trạng thái bắt đầu kế thừa: s_{i,t} -> s_{i,t+1}
            # Mệnh đề: (-s_{i,t} V s_{i,t+1})
            sat_solver.add_clause([-s(i, t), s(i, t+1)])
            
            # 1b. Trạng thái kết thúc kế thừa: f_{i,t} -> f_{i,t+1}
            # Mệnh đề: (-f_{i,t} V f_{i,t+1})
            sat_solver.add_clause([-f(i, t), f(i, t+1)])
            
            # 3. Trạng thái đang chạy: s_{i,t} ^ -f_{i,t} -> r_{i,t}
            # Mệnh đề: (-s_{i,t} V f_{i,t} V r_{i,t})
            sat_solver.add_clause([-s(i, t), f(i, t), r(i, t)])

        for k in machines:
            if k in processing_times[i]:
                p = processing_times[i][k]
                for t in range(p, H + 1):
                    # 2. Quy tắc thời gian xử lý trên máy k: m_{i,k} -> (f_{i,t} <-> s_{i,t-p})
                    # Mệnh đề: (-m_{i,k} V -f_{i,t} V s_{i,t-p}) ^ (-m_{i,k} V f_{i,t} V -s_{i,t-p})
                    sat_solver.add_clause([-m(i, k), -f(i, t), s(i, t-p)])
                    sat_solver.add_clause([-m(i, k), f(i, t), -s(i, t-p)])

    # --- RÀNG BUỘC THỨ TỰ VÀ MÁY (Rules for order and machines - Ảnh 2) ---
    
    # Ràng buộc mục tiêu (Goal): Mọi nguyên công phải hoàn thành trước H
    for i in operations:
        sat_solver.add_clause([f(i, H)])
        
    # Ràng buộc thứ tự Job (Job shop precedence): s_{j,t} -> f_{i,t}
    for (i, j) in job_precedences:
        for t in range(H + 1):
            # Mệnh đề: (-s_{j,t} V f_{i,t})
            sat_solver.add_clause([-s(j, t), f(i, t)])

    # Ràng buộc chọn máy (Flexible): Mỗi nguyên công chọn đúng 1 máy trong các máy khả dụng
    # Sum(m_{i,k}) = 1
    for i in operations:
        available_machines = [k for k in machines if k in processing_times[i]]
        # Hàm add_exactly_one sẽ tạo ra các mệnh đề (m_{i,M1} V m_{i,M2}) và (-m_{i,M1} V -m_{i,M2})
        sat_solver.add_exactly_one([m(i, k) for k in available_machines])

    # Ràng buộc máy đang chạy: m_{i,k} ^ r_{i,t} -> a_{i,k,t}
    for i in operations:
        for k in machines:
            for t in range(H + 1):
                # Mệnh đề: (-m_{i,k} V -r_{i,t} V a_{i,k,t})
                sat_solver.add_clause([-m(i, k), -r(i, t), a(i, k, t)])

    # Ràng buộc năng lực máy (Job shop capacity): Tối đa 1 nguyên công trên máy k tại mỗi slot
    # Sum(a_{i,k,t}) <= 1
    for k in machines:
        for t in range(H + 1):
            for i in operations:
                for j in operations:
                    if i < j:
                        # Mệnh đề cho 2 nguyên công: (-a_{i,k,t} V -a_{j,k,t})
                        sat_solver.add_clause([-a(i, k, t), -a(j, k, t)])

    return sat_solver.solve()