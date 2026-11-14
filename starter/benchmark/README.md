# Benchmark — Psychology 2e (OpenStax), chương 1–3

File câu hỏi: [`questions.jsonl`](questions.jsonl) — 20 câu, mỗi dòng một JSON.
Corpus và quy tắc tính trang: [`../data/manifest.json`](../data/manifest.json).

> Bộ câu hỏi, cách chia dev/test và tiêu chí chọn chiến lược dưới đây được **chốt ngày 2026-11-14, trước lần chạy retrieval đầu tiên**. Không sửa câu hỏi, nhãn gold hoặc split sau khi đã xem kết quả.

## 1. Định dạng mỗi câu

| Trường | Ý nghĩa |
|---|---|
| `id` | `q01`–`q20` |
| `split` | `dev` hoặc `test` |
| `type` | `direct` (hỏi trực tiếp), `paraphrase` (diễn đạt lại bằng từ khác nguồn), `conditional` (điều kiện/ngoại lệ), `metadata` (cần filter) |
| `question` | Câu hỏi tiếng Anh; không chứa đáp án hay gold source |
| `expected_answer` | Đáp án ngắn, rút từ evidence |
| `gold_source_id` | `source_id` trong manifest (`psych2e-ch01/02/03`) |
| `gold_page` | Danh sách số trang **PDF** (1-based), không phải số in trên header |
| `evidence_quote` | Trích nguyên văn từ trang gold, đủ để trả lời câu hỏi |
| `filter` | `null` hoặc `{"chapter": "<số chương>"}` |

## 2. Phân chia dev / test

Chia **theo câu hỏi, cố định trước khi chạy**, cân bằng giữa 3 chương:

| | Ch1 | Ch2 | Ch3 | Tổng |
|---|---|---|---|---|
| dev | q01–q05 | q06–q10 | q11–q15 | 15 |
| test | q16, q17 | q18 | q19, q20 | 5 |

Phân bố loại câu:

| Loại | dev | test | Tổng |
|---|---|---|---|
| direct | q01, q03, q06, q08, q11, q14 | q17 | 7 |
| paraphrase | q02, q05, q09, q13 | q16, q19 | 6 |
| conditional | q10, q15 | q20 | 3 |
| metadata (filter) | q04, q07, q12 | q18 | 4 |

**Nguy cơ rò rỉ:** dev và test lấy từ cùng 3 chương (không chia theo tài liệu vì corpus chỉ có 3 chương). Vì vậy test đo khả năng tổng quát trên câu hỏi mới, không đo trên tài liệu mới. Một số trang dùng chung cho cả dev và test: trang 54 (q10 dev, q18 test). Tham số chunking/filter chỉ được chọn dựa trên dev.

## 3. Câu hỏi kiểm tra metadata filter

Filter `chapter` mô phỏng ngữ cảnh người dùng cung cấp **trước khi truy xuất** (ví dụ: sinh viên đang học chương X). Mỗi câu filter hỏi về khái niệm **xuất hiện ở nhiều chương**, nên nếu không lọc thì retrieval có thể lấy nhầm chương:

| ID | Split | Filter | Khái niệm cũng xuất hiện ở |
|---|---|---|---|
| q04 | dev | `chapter = 1` | evolutionary / natural selection — Ch3 (tr. 65–68) |
| q07 | dev | `chapter = 2` | Freud — Ch1 (tr. 3, 5, 6, 8, 15, 16) |
| q12 | dev | `chapter = 3` | natural selection — Ch1 (tr. 4, 13) |
| q18 | test | `chapter = 2` | informed consent / ethics — Ch1 (tr. 17) |

Giá trị `chapter` lấy từ khoảng trang của từng chương trong manifest (kiểm chứng bằng header trang PDF), không tự đoán. Cấu hình A và B chạy **không filter** cho mọi câu; cấu hình C chỉ áp dụng filter cho 4 câu trên, 16 câu còn lại chạy như B.

## 4. Cách kiểm chứng evidence

1. Evidence được copy nguyên văn từ PDF, rồi đối chiếu với text **sau chuẩn hóa** của pipeline (NFKC, quy dấu nháy/gạch cong về ASCII, gộp khoảng trắng, so sánh không phân biệt hoa thường).
2. Lệnh `python -m src.run --check-only` kiểm tra tự động: mỗi `evidence_quote` phải nằm trong text của `gold_page` thuộc `gold_source_id`; đồng thời kiểm tra ≥20 câu, ≥15 dev, ≥5 test, ≥3 câu filter, ≥1 câu filter trong test. Kết quả lần chạy ngày 2026-11-14: `Benchmark OK: all evidence verified.`
3. Tác giả đọc lại từng câu để xác nhận evidence đủ trả lời câu hỏi, kể cả điều kiện (q10, q15, q20).

Ghi chú:
- Evidence của q16 và q20 nằm trong chú thích hình (figure caption), vẫn là nội dung của trang gold.
- Mỗi câu hiện có một nguồn gold. Nếu khi chấm phát hiện một trang khác cũng chứa bằng chứng hợp lệ, sẽ bổ sung vào `alt_gold` và ghi rõ trong báo cáo.
- Bộ câu hỏi được soạn với sự hỗ trợ của Claude (AI) từ nội dung PDF; tác giả đã đọc lại và xác nhận đáp án, evidence.

## 5. Tiêu chí chọn chiến lược (chốt trước khi xem test)

Chiến lược được chọn **chỉ dựa trên kết quả dev**, theo thứ tự ưu tiên:

1. **Evidence Hit@3 trên dev** cao nhất.
2. Nếu hòa: **Hit@1 trên dev** cao hơn.
3. Nếu vẫn hòa: **ít chunk hơn** (chi phí lưu trữ/embedding thấp hơn).

Sau khi chọn, ghi quyết định vào báo cáo rồi mới đọc kết quả test. Kết quả test chỉ để báo cáo, không dùng để chỉnh tham số. Vì test chỉ có 5 câu, chênh lệch 1 câu (20 điểm %) không đủ để kết luận chiến lược tốt hơn một cách tổng quát.
