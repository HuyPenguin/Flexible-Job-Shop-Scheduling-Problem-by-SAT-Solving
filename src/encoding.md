# Hướng dẫn mã hóa bài toán FJSP (Flexible Job Shop Scheduling Problem)

Dưới đây là tài liệu giải thích cách mã hóa (encoding) bài toán Flexible Job Shop Scheduling Problem (FJSP) thành các mệnh đề logic (SAT/CNF) dành cho agent viết code.

## 1. Ký hiệu cơ bản (Notations)
Các hằng số và chỉ mục được sử dụng trong bài toán:
*   **$i$**: Một nguyên công (operation). Ví dụ: 1.3 là nguyên công thứ 3 của job 1.
*   **$k$**: Một máy (machine).
*   **$p_{i,k}$**: Thời gian xử lý của nguyên công $i$ trên máy $k$.
*   **$H$**: Thời hạn hoàn thành (deadline).
*   **$t$**: Một mốc thời gian (time point); "slot $t$" nghĩa là khoảng thời gian từ $t$ đến $t + 1$.

## 2. Các biến Boolean (Variables)
Tất cả các biến dưới đây đều nhận giá trị Đúng hoặc Sai (True or False):
*   **$m_{i,k}$**: Nguyên công $i$ được phân công cho máy $k$.
*   **$r_{i,t}$**: Nguyên công $i$ đang chạy trong slot $t$.
*   **$s_{i,t}$**: Nguyên công $i$ đã bắt đầu vào thời điểm $t$ hoặc trước đó.
*   **$f_{i,t}$**: Nguyên công $i$ đã hoàn thành vào thời điểm $t$ hoặc trước đó.
*   **$a_{i,k,t}$**: Nguyên công $i$ đang chạy trên máy $k$ trong slot $t$.
*   **$b_{i,k,t}$**: Nguyên công $i$ đang chờ trong bộ đệm của máy $k$ tại slot $t$.
*   **$busy_{k,t}$**: Máy $k$ đang xử lý một nguyên công trong slot $t$.

## 3. Quy tắc mã hóa thời gian (Order encoding of time)
Phần này định nghĩa mối quan hệ logic của các biến trạng thái thời gian. Quy tắc chung cho phép kéo theo $a \rightarrow b$ là mệnh đề $(\neg a \lor b)$.
*   **Quy tắc 1a (Đã bắt đầu thì vẫn đang bắt đầu)**: $s_{i,t} \rightarrow s_{i,t+1}$.
    *   Mệnh đề (Clause): $(\neg s_{i,t} \lor s_{i,t+1})$.
*   **Quy tắc 1b (Đã hoàn thành thì vẫn đang hoàn thành)**: $f_{i,t} \rightarrow f_{i,t+1}$.
    *   Mệnh đề (Clause): $(\neg f_{i,t} \lor f_{i,t+1})$.
*   **Quy tắc 2 (Hoàn thành tại $t$ khi và chỉ khi bắt đầu tại $t - p$, trên máy $k$)**: $m_{i,k} \rightarrow (f_{i,t} \leftrightarrow s_{i,t-p})$.
    *   Mệnh đề (Clauses): $(\neg m_{i,k} \lor \neg f_{i,t} \lor s_{i,t-p}) \land (\neg m_{i,k} \lor f_{i,t} \lor \neg s_{i,t-p})$.
*   **Quy tắc 3 (Trạng thái đang chạy)**: Bắt đầu và chưa hoàn thành nghĩa là đang chạy: $s_{i,t} \land \neg f_{i,t} \rightarrow r_{i,t}$.
    *   Mệnh đề (Clause): $(\neg s_{i,t} \lor f_{i,t} \lor r_{i,t})$.

## 4. Ràng buộc về Job và Máy (Rules for order and machines)
Các quy tắc này áp dụng để đảm bảo tính đúng đắn của trình tự (order) và phân bổ máy:
*   **Mục tiêu (Goal)**: Mọi nguyên công phải hoàn thành trước thời hạn $H$. 
    *   Ký hiệu: $f_{i,H}$.
    *   Mệnh đề (Clause): $(f_{i,H})$.
*   **Thứ tự nguyên công (Job shop precedence)**: Nếu nguyên công $j$ theo sau nguyên công $i$ trong cùng một job, $j$ không thể bắt đầu trước $t$ trừ khi $i$ đã hoàn thành trước $t$: $s_{j,t} \rightarrow f_{i,t}$.
    *   Mệnh đề (Clause): $(\neg s_{j,t} \lor f_{i,t})$.
*   **Phân công máy (Flexible)**: Chính xác một máy khả dụng được chọn cho nguyên công $i$: $\sum_k m_{i,k} = 1$.
    *   Mệnh đề (Clauses) (Ví dụ với 2 máy M1, M2): $(m_{i,M1} \lor m_{i,M2})$ và $(\neg m_{i,M1} \lor \neg m_{i,M2})$.
*   **Chạy trên máy $k$ (Job shop)**: $m_{i,k} \land r_{i,t} \rightarrow a_{i,k,t}$.
    *   Mệnh đề (Clause): $(\neg m_{i,k} \lor \neg r_{i,t} \lor a_{i,k,t})$.
*   **Công suất máy (Job shop capacity)**: Có nhiều nhất một nguyên công chạy trên máy $k$ trong mỗi khoảng thời gian slot $t$: $\sum_i a_{i,k,t} \le 1$.
    *   Mệnh đề (Clause) cho hai nguyên công $i, j$ bất kỳ trên máy $k$: $(\neg a_{i,k,t} \lor \neg a_{j,k,t})$.