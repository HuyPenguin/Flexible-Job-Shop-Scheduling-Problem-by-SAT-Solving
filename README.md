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
python src/main.py fjsp-instances/kacem/k1.json
python src/main.py fjsp-instances/kacem/k1.json --time-limit 60 --output result.json
```

Mặc định solver chạy không giới hạn thời gian. Truyền `--time-limit` để giới hạn tổng thời gian các lần gọi SAT cho một instance.
Thời gian mã hóa và giải mã nằm ngoài giới hạn này.
