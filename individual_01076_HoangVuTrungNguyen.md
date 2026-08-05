# Báo cáo cá nhân — Member A / Lead & Coordinator

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Hoàng Vũ Trung Nguyên |
| MSSV | 01076 |
| Khóa/Lớp | K4 |
| Vai trò chính | Team Lead, Core Infrastructure và Integration |
| Ngày hoàn thành | 2026-08-05 |

> Repo không chứa họ tên/MSSV đầy đủ của Member A. Phần kỹ thuật của báo cáo đã hoàn tất; cần thay hai trường định danh và đổi tên file theo `individual_5SoCuoiMHV_HoVaTen.md` trước khi nộp.

## 2. Vai trò và phạm vi công việc

| Deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Project configuration | `src/config.py` | Paths, policy constants, model assignment | Centralized config | Hoàn thành |
| Data access layer | `src/data_loader.py` | 9 Olist CSV | Cached/indexed query API | Hoàn thành |
| Shared schemas | `src/models.py` | Input/output contract | Pydantic models | Hoàn thành |
| LLM abstraction | `src/llm/*` | Agent/provider config | Injectable LLM clients | Hoàn thành |
| Agent foundation | `src/agents/base_agent.py` | Shared dependencies | Base processing contract | Hoàn thành |
| Orchestration | `src/agents/coordinator_agent.py` | Case + domain agents | Verified `CaseOutput` | Hoàn thành |
| Batch runner | `src/main.py` | 50 input JSON | 50 output JSON | Hoàn thành |
| Observability | `src/tracer.py` | Agent call metadata | Trace + runtime metadata | Hoàn thành |
| Integration A10 | Coordinator adapter, payment stability, integration tests | Module B/C | 50/50 valid outputs | Hoàn thành |
| Architecture A11 | `architecture.md` | Kiến trúc thực tế | Diagram, roles, access, handoff | Hoàn thành |

## 3. Kết quả bàn giao

- Tích hợp bốn data agent, Policy và Verifier bằng handoff có structured payload.
- Chạy Phase 1 song song nhưng giữ Policy/Verifier theo đúng dependency.
- Chuẩn hóa contract nested/flat tại boundary, không buộc B/C rewrite module.
- Dùng raw CSV row count/sequence cho secondary issues và evidence, tránh sai do output limit.
- Fail-fast khi agent lỗi; không phát hành case được lấp dữ liệu rỗng.
- Thêm Pydantic hard gate trước khi trả kết quả cho batch writer.
- Sinh lại 50 output, 301 trace entries và metadata của lượt chạy mới nhất.
- Thực hiện một Groq API batch review thật bằng model 8B; output nghiệp vụ vẫn deterministic.

Kết quả đo được:

| Metric | Giá trị |
|---|---:|
| Pytest | 21 passed |
| Pipeline | 50 OK, 0 FAIL |
| Schema + business validation | 50/50 pass |
| Trace | 301 entries, 0 error |
| API LLM | 1 call, 1 thành công |
| Runtime xử lý và LLM review sau khởi tạo | 7.67 giây |

## 4. Giải thích kỹ thuật

### Vấn đề cần giải quyết

Trước A10, module B trả payload nested (`customer_context`, `affected_entities`, `product_context`, `delivery_analysis`), Payment trả payload flat, Policy nhận payload nested nhưng trả kết quả nested. Coordinator lại đọc tất cả như flat. Hệ quả là 50 output có `primary_issue` rỗng, context rỗng và trace ghi 50 lỗi Payment từ việc đánh giá truth value của Pandas DataFrame.

### Cách triển khai

Coordinator dùng `_section(payload, key)` làm anti-corruption layer: nếu section nested tồn tại thì lấy section đó, nếu không thì coi payload là flat. Bốn domain agent được gọi qua `ThreadPoolExecutor`; kết quả chỉ được chuyển sang Policy sau khi tất cả future hoàn tất.

Raw item/payment rows được đọc tại boundary để dựng payment IDs và truyền count/sequence thật cho Policy. Đây là điểm quan trọng vì output chỉ giữ tối đa 5 item/payment và 3 seller, trong khi quyết định `multi_*`, split payment và evidence phải dựa trên dữ liệu nguồn đầy đủ.

Sau khi Policy trả quyết định, Coordinator assembly draft, giao cho Verifier và cuối cùng gọi `CaseOutput.model_validate()`. Nếu một agent exception, `_run()` vẫn ghi trace nhưng propagate `RuntimeError`; `main.py` đánh dấu case fail thay vì ghi kết quả không đáng tin cậy.

### Contract

| Thành phần | Mô tả |
|---|---|
| Input | `order_id`, `case_id`; dữ liệu nguồn qua shared `DataLoader` |
| Phase 1 output | Customer, entities/product, payment reconciliation, delivery analysis |
| Phase 2 output | Assessment, root cause, evidence, refund, actions |
| Final output | Pydantic-validated `CaseOutput` dict |
| Error policy | Trace rồi fail case; không silently fallback sang `{}` |

## 5. Quyết định kỹ thuật quan trọng

**Bối cảnh:** Có thể sửa từng agent B/C để dùng một shape duy nhất, hoặc chuẩn hóa tại Coordinator.

**Phương án chọn:** Chuẩn hóa tại integration boundary, đồng thời giữ Pydantic hard gate.

**Lý do:** Giảm coupling và regression trên file do thành viên khác sở hữu, tương thích cả contract cũ/mới, tập trung logic chuyển đổi tại một nơi có test end-to-end. Việc dùng raw row metadata tại boundary cũng phân tách rõ “dữ liệu dùng quyết định” khỏi “dữ liệu đã truncate để xuất bản”.

**Bằng chứng:** 21/21 test pass; 50/50 case pass hai lớp validator; 301/301 trace entries không lỗi; 1/1 API LLM call thành công; ZIP có đúng 50 root-level JSON.

## 6. Lỗi đã xử lý

**Triệu chứng:** Cả 50 output có `case_assessment.primary_issue = ""`; `trace.jsonl` có 50 lỗi.

**Nguyên nhân gốc:** Contract mismatch nested/flat giữa Coordinator và agent B/C. Payment còn dùng DataFrame như boolean/iterable record, gây exception và không dựng payment IDs.

**Cách xử lý:**

- Chuyển DataFrame sang records rõ ràng trong Payment.
- Dedupe `payment_types` theo thứ tự nguồn bằng `dict.fromkeys`.
- Dựng payment IDs từ `payment_sequential` thật.
- Normalize mọi agent payload trong Coordinator.
- Đọc raw counts/sequences cho Policy.
- Parse output Policy theo nested section.
- Thêm integration test 50 case và test failure propagation.

**Xác minh:**

```bash
python -m pytest tests -q -p no:cacheprovider
# 21 passed

python -m src.main
# DONE 50 OK | 0 FAIL | 50 total
```

## 7. Hiểu biết về luồng end-to-end

1. `main.py` validate từng input bằng `CaseInput`, lấy claimed order ID và gọi Coordinator.
2. Coordinator giao cùng order ID cho bốn domain agent độc lập. Mỗi agent query đúng bảng/index của mình qua shared DataLoader.
3. Coordinator normalize kết quả và handoff toàn bộ evidence-derived context cho Policy.
4. Policy áp rule priority, sau đó secondary issue order, responsibility, refund và action order.
5. Coordinator assembly output; Verifier kiểm tra format/limit; Pydantic thực hiện schema hard gate.
6. Formatter persist JSON. Tracer ghi sáu agent call mỗi case và metadata runtime của đúng lượt chạy hiện tại.

Đối với quality, output được kiểm tra cả cấu trúc lẫn invariant nghiệp vụ. Trace/metadata phục vụ reproducibility và chứng minh handoff thật, không thay thế kiểm tra correctness của output.

## 8. Cam kết

- [x] Nội dung phản ánh đúng phần việc A1–A12 đã thực hiện và xác minh.
- [x] Có thể giải thích luồng end-to-end và contract giữa các agent.
- [x] Không tuyên bố thành công cho bước chưa chạy.
- [x] Không ghi API key, token hoặc nội dung `.env`.
- [x] Báo cáo không sao chép báo cáo của thành viên B/C.

**Họ và tên:** KerryFT (cần thay bằng họ tên đầy đủ trước khi nộp)
**Ngày xác nhận:** 2026-08-05
