Giải bài toán Flexible Job Shop Scheduling bằng phương pháp Incremental SAT.
Đây là bài tập lớn môn Các vấn đề hiện đại trong KHMT.

Nhóm sinh viên:
- Nguyễn Quốc Huy
- Nguyễn Tuấn Thảo
- Nguyễn Trung Kiên

## Chạy solver SAT

Cài thư viện: `python -m pip install python-sat`.

Từ thư mục gốc dự án:

```powershell
python src/main.py fjsp-instances\kacem\k1.json
python src/main.py fjsp-instances\kacem\k1.json --time-limit 60 --output result.json
```

Mặc định solver chạy không giới hạn thời gian. Truyền `--time-limit` để giới hạn tổng thời gian các lần gọi SAT cho một instance.
Thời gian mã hóa và giải mã nằm ngoài giới hạn này.

## Chạy solver CP và MIP

Các solver đối chứng nằm trong `src/solvers/cp` và `src/solvers/mip`, dùng chung
đầu vào FJSP và định dạng kết quả với SAT:

```powershell
python src/main.py fjsp-instances\kacem\k1.json --solver cp --time-limit 60
python src/main.py fjsp-instances\kacem\k1.json --solver mip --time-limit 60
```

CP dùng IBM ILOG CP Optimizer qua DOcplex CP; MIP dùng CPLEX qua DOcplex MP.
Cần cài `docplex`, các API/binary solver tương ứng và license hợp lệ; cài
`docplex` một mình không cung cấp CP Optimizer hoặc CPLEX.

## Chạy solver CP-SAT

CP-SAT dùng OR-Tools, không yêu cầu license thương mại:

```powershell
python -m pip install ortools
python src/main.py fjsp-instances\kacem\k1.json --solver cp-sat --time-limit 60
```
