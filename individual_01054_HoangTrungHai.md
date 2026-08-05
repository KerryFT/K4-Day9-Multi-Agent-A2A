# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                 |
| --------------- | ---------------------------------------- |
| Họ và tên       | Hoàng Trung Hải                 |
| MSSV            | 2A202601054                   |
| Khóa/Lớp        | K4                                       |
| Vai trò chính   | Data And Analysis Agents        |
| Ngày hoàn thành | 2026-08-05                               |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
|---|---|---|---|---|
| Customer Agent | `src/agents/customer_agent.py` | `order_id` (str) | Dict `customer_context` (`customer_unique_id`, `related_order_ids`) | Hoàn thành |
| Order & Product Agent | `src/agents/order_product_agent.py` | `order_id` (str) | Dict `affected_entities` + `product_context` (`item_ids`, `seller_ids`, `product_ids`, `category_names`) | Hoàn thành |
| Delivery Agent | `src/agents/delivery_agent.py` | `order_id` (str) | Dict `delivery_analysis` (`delivered_at`, `estimated_delivery_at`, `carrier_handoff_at`, `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids`) | Hoàn thành |
| Unit Tests cho Agent | `tests/test_data_loader.py` | `DataLoader` instance | Pytest test suite cho các agent | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
|---|---|---|
| Kiểm thử & debug `DataLoader` | Member A (`data_loader.py`) | Phát hiện và sửa lỗi `KeyError: 'order_id'` khi truy xuất Series indexed trong pytest |

---

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
|---|---|---|---|
| Triển khai CustomerAgent | `src/agents/customer_agent.py` | Trích xuất thành công `customer_unique_id` và lịch sử đơn hàng liên quan | `pytest tests/test_data_loader.py` |
| Triển khai OrderProductAgent | `src/agents/order_product_agent.py` | Ghép item format `order_id:item_id`, lấy seller, product và dịch category sang tiếng Anh | `pytest tests/test_data_loader.py` |
| Triển khai DeliveryAgent | `src/agents/delivery_agent.py` | Tính chính xác `delivery_variance_hours` và `handoff_variance_hours` theo từng seller | `pytest tests/test_data_loader.py` |

---

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xây dựng lớp phân tích dữ liệu chuyên biệt (Data Domains) cho hệ thống multi-agent:
- Xác định xem khách hàng có phải là `repeat_customer` (có lịch sử đơn hàng trước đó) hay không.
- Thu thập tất cả các thực thể bị ảnh hưởng (`order_ids`, `item_ids`, `seller_ids`, `product_ids`, `category_names`) theo đúng định dạng chuẩn.
- Phân tích chi tiết dòng thời gian giao hàng và bàn giao carrier của từng seller để phát hiện bên vi phạm trễ hạn bàn giao (`late_handoff_seller_ids`).

### Cách triển khai
- **Deterministic Python Execution:** Các agent thuộc Role B chạy logic tính toán thuần Python dựa trên `DataLoader` (O(1) index lookups) để đảm bảo tốc độ cực nhanh, chính xác 100%, không bị hallucination.
- **Tính toán thời gian (`delivery_agent.py`):** Sử dụng `pandas.to_datetime` để parse timestamp, quy đổi chênh lệch giây thành giờ (`total_seconds() / 3600.0`), làm tròn đúng 2 chữ số thập phân (`DECIMAL_PLACES = 2`).
- **Xử lý danh mục & dịch thuật (`order_product_agent.py`):** Tra cứu từ `products` sang `product_category_name_translation` để chuẩn hóa tên category từ tiếng Bồ Đào Nha sang tiếng Anh.
- **Giới hạn Output (`LIMITS`):** Áp dụng giới hạn `LIMITS` từ `config.py` cho tất cả danh sách ID trước khi trả về.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input | `order_id` (str) |
| Output | Dict chuẩn chứa `customer_context`, `affected_entities`, `product_context`, `delivery_analysis` |
| Module phụ thuộc | `DataLoader` (`src/data_loader.py`), `src/config.py` |
| Module sử dụng output | `CoordinatorAgent` (`src/agents/coordinator_agent.py`), `PolicyAgent` (`src/agents/policy_agent.py`) |

### Cách xác minh

```bash
.venv\Scripts\pytest tests/test_data_loader.py
```
- **Kết quả mong đợi:** 8/8 test cases pass 100%.
- **Kết quả thực tế:** Tất cả 8 unit test cases đã chạy thành công trong ~3.8s.

---

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn giữa dùng LLM để trích xuất/phân tích dữ liệu đơn hàng hay dùng logic Python deterministic.
- **Các phương án đã cân nhắc:**
  1. Dùng LLM prompt để đọc JSON / CSV và trả ra thông tin giao hàng & seller handoff.
  2. Dùng logic Python thuần query qua pandas DataLoader đã indexed.
- **Phương án đã chọn:** Phương án 2 (Python deterministic logic).
- **Lý do:** Dữ liệu thời gian và số tiền trong khiếu nại yêu cầu độ chính xác tuyệt đối (làm tròn 2 chữ số thập phân, so sánh từng mốc giờ). Dùng Python thuần đảm bảo latency thấp (<5ms/case), 0% hallucination và tiết kiệm token cho LLM.

---

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:**
  ```text
  KeyError: 'order_id' trong tests/test_data_loader.py khi assert order["order_id"] == first_order_id
  ```
- **Nguyên nhân gốc:** `DataLoader` cài đặt `self._order_idx = self.orders.set_index("order_id")`. Khi truy xuất qua `.loc[order_id]`, cột `"order_id"` trở thành tên của Series (`order.name`) chứ không còn là một key trong Series index.
- **Cách xử lý:** Cập nhật lại câu lệnh kiểm tra assertion thành `assert order.name == first_order_id`.
- **Cách xác minh sau khi sửa:** Chạy lại `pytest` thành công 100%.

---

## 7. Hiểu biết về luồng end-to-end

1. Dữ liệu đi từ các file CSV Olist trong `data/` được `DataLoader` load và index vào RAM 1 lần duy nhất.
2. `CoordinatorAgent` tiếp nhận từng case từ `input/EC_xxx.json`, trích xuất `claimed_order_id`.
3. Coordinator gọi song song/lần lượt các Agent: `CustomerAgent`, `OrderProductAgent`, `PaymentAgent`, `DeliveryAgent` để thu thập dữ liệu gốc.
4. Coordinator hợp nhất dữ liệu từ các agent trên và truyền cho `PolicyAgent` để đánh giá theo bộ quy tắc `EC_POLICY_V2`, xác định `primary_issue`, `secondary_issues`, `responsible_parties` và `refund_value`.
5. Kết quả được kiểm tra qua `VerifierAgent` trước khi ghi ra file `output/EC_xxx.json` và lưu trace vào `logging/trace.jsonl`.

---

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Hoàng Trung Hải  
**Ngày xác nhận:** 2026-08-05
