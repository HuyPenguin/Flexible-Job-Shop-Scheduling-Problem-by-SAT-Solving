TÀI LIỆU KIẾN TRÚC HỆ THỐNG
Dự án: Giải quyết bài toán Flexible Job Shop Scheduling (FJSP) sử dụng SAT Solver và Tìm kiếm nhị phân.

1. Tổng quan hệ thống (System Overview)
Hệ thống được thiết kế để giải quyết bài toán Điều độ phân xưởng linh hoạt (FJSP) nhằm tối thiểu hóa thời gian hoàn thành (makespan). Kiến trúc hệ thống kết hợp hai phương pháp cốt lõi:

Tìm kiếm nhị phân (Binary Search): Đóng vai trò tìm kiếm giá trị makespan tối ưu trong một không gian giới hạn (cận dưới và cận trên).
Bộ giải SAT (SAT Solver): Đóng vai trò kiểm tra tính khả thi (Decision Problem) của một mốc thời gian cụ thể bằng phương pháp "Order encoding of time".
2. Cấu trúc mã nguồn (Project Structure)
Dự án được phân chia thành các module độc lập theo nguyên tắc Single Responsibility (Đơn trách nhiệm), giúp dễ dàng bảo trì, thay đổi thư viện SAT bên dưới hoặc thay đổi phương pháp mã hóa.

Plaintext
fjsp_sat_project/
├── main.py                  # Điểm khởi chạy (Entry point) và điều phối luồng
├── data_parser.py           # Module xử lý dữ liệu đầu vào
├── sat_wrapper.py           # Lớp trừu tượng (Interface) giao tiếp với SAT Solver
├── sat_encoder.py           # Module mã hóa bài toán FJSP thành CNF clauses
├── schedule_decoder.py      # Module giải mã kết quả từ SAT Solver
└── requirements.txt         # Khai báo các thư viện phụ thuộc


3. Chi tiết các thành phần (Component Details)
3.1. Phân tích dữ liệu (data_parser.py)
Trách nhiệm: Đọc dữ liệu đầu vào (từ file text, csv, hoặc json) và chuyển đổi thành cấu trúc dữ liệu chuẩn (FJSP_Instance) để các module khác dễ dàng truy xuất.


Hàm chính:


parse_fjsp_data(file_path): Phân tích file và tạo cấu trúc dữ liệu bao gồm danh sách Job, Operation (dạng tuple (job_id, op_id)), Machine, và Processing Time.
calculate_initial_bounds(instance): Ước lượng cận dưới (LB - Lower Bound) và cận trên (UB - Upper Bound) của makespan để thu hẹp không gian tìm kiếm nhị phân.
3.2. Trừu tượng hóa SAT Solver (sat_wrapper.py)
Trách nhiệm: Ẩn đi sự phức tạp của các thư viện SAT Solver cụ thể (như PySAT, Z3, MiniSat). Quản lý việc ánh xạ từ tên biến có ý nghĩa (ví dụ: "s_1.3_5") sang ID nguyên dương mà SAT Solver yêu cầu.


Hàm/Phương thức chính:


get_var_id(name): Cấp phát hoặc truy xuất ID số nguyên của biến.
add_clause(literals): Thêm một mệnh đề (clause) vào bộ giải.
add_exactly_one(literals): Sinh tự động các mệnh đề CNF để ép buộc chính xác 1 biến trong danh sách mang giá trị TRUE.
solve(): Kích hoạt engine giải toán.
get_model(): Trả về danh sách các biến mang giá trị TRUE nếu bài toán khả thi (SAT).
3.3. Mã hóa bài toán (sat_encoder.py)
Trách nhiệm: Dịch các quy tắc ràng buộc của bài toán FJSP sang các mệnh đề logic (CNF) dựa trên kỹ thuật Order encoding of time.


Các quy tắc mã hóa chính:
Time & State Constraints: Biểu diễn trạng thái bắt đầu (s), kết thúc (f), đang chạy (r) và tính kế thừa của chúng theo thời gian.
Precedence Constraints: Đảm bảo nguyên công trước phải hoàn thành thì nguyên công sau trong cùng một Job mới được bắt đầu.
Machine Constraints: Đảm bảo mỗi nguyên công chỉ gán cho một máy, và tại mỗi thời điểm một máy chỉ chạy tối đa một nguyên công.
Deadline Constraint: Ép buộc mọi nguyên công phải kết thúc trước thời gian mục tiêu H.
3.4. Giải mã kết quả (schedule_decoder.py)
Trách nhiệm: Dịch ngược output thô từ SAT Solver (danh sách ID biến TRUE) thành một lịch trình (schedule) thực tế có thể đọc hiểu hoặc vẽ biểu đồ.


Hàm chính:
decode_sat_model(true_vars, instance): Lọc các biến s (bắt đầu), f (kết thúc) và m (máy) để xây dựng bảng phân công chi tiết (Job, Operation, Machine, Start Time, End Time).
3.5. Bộ điều phối chính (main.py)
Trách nhiệm: Kết nối tất cả các module trên. Khởi tạo dữ liệu, chạy vòng lặp tìm kiếm nhị phân, và in ra kết quả cuối cùng.


Luồng hoạt động (Data Flow):



Gọi data_parser để lấy FJSP_Instance, LB, UB.
Vòng lặp while LB <= UB:
Tính H=(LB+UB)/2.


Gọi sat_encoder tạo công thức SAT với deadline H.


Gọi sat_wrapper.solve().


Nếu kết quả là SAT: Gọi schedule_decoder lưu lịch trình tốt nhất hiện tại, cập nhật UB=H-1 để tìm lịch trình ngắn hơn.


Nếu kết quả là UNSAT: Cập nhật LB=H+1 vì deadline quá khắt khe.


Trả về lịch trình tối ưu được lưu lại cuối cùng.
4. Đặc điểm thiết kế (Design Decisions)
Sử dụng Tuple cho định danh (ID): Các nguyên công được biểu diễn dưới dạng tuple 2 chiều (job_id, operation_id). Điều này giúp việc sinh các ràng buộc tuần tự trong cùng một Job (job_precedences) diễn ra hoàn toàn tự động mà không làm thay đổi hay phức tạp hóa số chiều của biến SAT (vẫn duy trì cấu trúc 2 chiều si,t).


Decoupling (Giảm phụ thuộc): Bằng cách cô lập logic tạo biến và gọi hàm thư viện vào sat_wrapper.py, hệ thống có thể dễ dàng chuyển đổi qua lại giữa các engine SAT khác nhau (ví dụ từ Glucose sang CaDiCaL của PySAT) mà code ở module sat_encoder.py không cần thay đổi dù chỉ 1 dòng.

