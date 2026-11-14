# Báo cáo cá nhân — Day 6

**Học viên:** Bùi Thu Phương · 2A202604080 · L3B
**Ngày chạy:** 2026-11-14 (lần chạy cuối: 11:14, giờ máy)

## Dữ liệu và pipeline

- **Chủ đề, nguồn/quyền, số trang và quy tắc tính trang:**
  OpenStax _Psychology 2e_, chương 1 (Introduction to Psychology), chương 2 (Psychological Research), chương 3 (Biopsychology). Nguồn: https://openstax.org/details/books/psychology-2e, giấy phép CC BY 4.0 (OpenStax, Rice University), truy cập 2026-11-14. File `starter/data/Psychology2e.pdf` là bản web của 3 chương, lưu bằng chức năng "Save as PDF" của trình duyệt (PDFium): **101 trang vật lý, cả 101 trang đều trích được text**. Quy tắc tính: chỉ tính trang bài học (gồm trang mở chương có phần Introduction), bỏ Key Terms, Summary, Review / Critical Thinking / Personal Application Questions. Kết quả: **80 trang nội dung** (Ch1: tr. 1–23; Ch2: tr. 29–56; Ch3: tr. 65–93), tổng 236.082 ký tự sau chuẩn hóa. Số trang là số trang PDF (1-based), không phải số in trên header. Chi tiết trong [`starter/data/manifest.json`](../../starter/data/manifest.json); số ký tự từng trang ở [`starter/results/corpus_stats.json`](../../starter/results/corpus_stats.json). File PDF không commit (xem `.gitignore`); tải lại theo URL trong manifest.

- **Chuẩn hóa, lỗi và giới hạn:**
  Đọc bằng PyMuPDF theo khối văn bản (`get_text("blocks", sort=True)`), bỏ khối ảnh. Mỗi khối: Unicode NFKC, bỏ soft hyphen, quy dấu nháy/gạch cong về ASCII (’ “ ” – — → ' " -), nối từ bị gạch nối khi xuống dòng, gộp khoảng trắng. Loại các dòng lặp lại: footer `Access for free at openstax.org`, số trang đứng riêng, header `1.2 • History of Psychology 9` và `10 1 • Introduction to Psychology` (đã kiểm tra: không còn header sót). Các khối của một trang nối bằng `\n\n` để giữ ranh giới đoạn. Log lỗi: [`ingestion_errors.json`](../../starter/results/ingestion_errors.json) — **0 trang rỗng/lỗi**. Giới hạn: (1) đoạn văn vắt qua hai trang bị tách vì xử lý theo trang; (2) dòng credit ảnh và link "LINK TO LEARNING" vẫn nằm trong text; (3) nối gạch nối có thể dính một số từ ghép xuống dòng đúng chỗ gạch nối.

- **Embedding model/provider/version/số chiều, vector store/version, metric, lệnh chạy và chi phí:**
  `sentence-transformers/all-MiniLM-L6-v2`, chạy local trên CPU qua `sentence-transformers 6.3.0` (torch 2.15.0, transformers 5.23.0), **384 chiều**, `normalize_embeddings=True`; query và document được encode như nhau (model không cần tiền tố). Model chỉ đọc khoảng 256 token đầu, nên chunk B giới hạn 900 ký tự. Vector store: **PostgreSQL 16.16 + pgvector 0.8.7** (Docker image `pgvector/pgvector:0.8.7-pg16`), bảng `chunks` với cột `embedding vector(384)`, metric **cosine** (`<=>`), **exact search** (không tạo index ANN). Python 3.13.1, psycopg 3.3.8, pymupdf 2.1. **Chi phí: 0** (không dùng API trả phí). Lệnh chạy (trong `starter/`):

  ```powershell
  docker compose -p day6_student_starter up -d --wait
  python scripts/check_setup.py
  python -m src.run --check-only   # đọc corpus + kiểm chứng benchmark
  python -m src.run                # chunk, embed, upsert, chạy benchmark, xuất results/
  ```

  **Nạp lại không trùng:** chạy pipeline hai lần; lần hai `rows_before = rows_after = {A: 557, B: 367}` ([`stats.json`](../../starter/results/stats.json)). Khóa chính `(strategy, chunk_id)`, `chunk_id` ổn định dạng `<document_id>:p<page>:<f|p><idx>`; upsert dùng `ON CONFLICT DO UPDATE` và xóa các chunk cũ của tài liệu không còn trong lần nạp mới (xử lý khi tài liệu thay đổi). Hạn chế: nếu một tài liệu bị bỏ khỏi manifest, chunk của nó không tự bị xóa.

- **Metadata bắt buộc, trường lọc bổ sung, nguồn giá trị và lý do chọn:**
  Mỗi chunk có `document_id` (text, = `source_id` trong manifest), `source` (text, đường dẫn PDF), `page` (int, số trang PDF) và trường lọc **`chapter`** (text, `"1"`/`"2"`/`"3"`). Giá trị `chapter` lấy từ khoảng trang của từng chương trong manifest, kiểm chứng bằng header trang PDF (và tiêu đề chương ở trang mở chương). Lý do chọn: corpus có 3 chương phân biệt rõ, và nhiều khái niệm xuất hiện ở hơn một chương (Freud, natural selection, informed consent…), nên lọc theo chương có ý nghĩa khi người dùng biết mình đang học chương nào.

## Cấu hình và benchmark

- **A / B / C (tham số cụ thể, khác biệt duy nhất B–C):**

  |     | Chunking                                                                                                                        | Filter                                                                              |
  | --- | ------------------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------- |
  | A   | Cửa sổ ký tự cố định **500, overlap 50**, cắt trong từng trang                                                                  | Không                                                                               |
  | B   | Theo đoạn (khối văn bản PyMuPDF), gom các đoạn liền nhau tới **tối đa 900 ký tự**; đoạn quá dài tách theo câu; trong từng trang | Không                                                                               |
  | C   | **Dùng đúng chunk và vector của B** (cùng các dòng `strategy='B'` trong DB)                                                     | `WHERE chapter = <giá trị filter>` chỉ cho câu có `filter`; các câu khác chạy như B |

  A–B chỉ khác cách chunk; **B–C chỉ khác bước lọc metadata**. Cả ba dùng cùng corpus, model, store, metric, top-k = 3 và cùng bộ câu hỏi.

- **≥20 câu: phân chia ≥15 dev / ≥5 test, câu metadata filter và cách kiểm chứng evidence:**
  20 câu tiếng Anh ([`starter/benchmark/questions.jsonl`](../../starter/benchmark/questions.jsonl)), chia cố định trước khi chạy: **15 dev (q01–q15, 5 câu/chương) và 5 test (q16–q20)**. Gồm 7 direct, 6 paraphrase, 3 conditional, **4 câu có filter `chapter`** (q04, q07, q12 thuộc dev; **q18 thuộc test**), mỗi câu filter hỏi về khái niệm xuất hiện ở nhiều chương. Giá trị filter đóng vai trò ngữ cảnh người dùng cung cấp trước khi truy xuất; không đưa đáp án hay gold source vào query/filter. Evidence là trích nguyên văn từ PDF; `python -m src.run --check-only` kiểm tra tự động mọi `evidence_quote` nằm trong text sau chuẩn hóa của `gold_page` → `Benchmark OK: all evidence verified.` Mô tả đầy đủ và nguy cơ rò rỉ (dev/test cùng 3 chương, trang 54 dùng cho cả q10 dev và q18 test) ở [`starter/benchmark/README.md`](../../starter/benchmark/README.md). Bộ câu hỏi do Claude hỗ trợ soạn từ nội dung PDF; tác giả đọc lại và xác nhận.

- **Tiêu chí chọn chiến lược đã chốt trước khi xem test:**
  Chỉ dựa trên dev: (1) Evidence Hit@3 dev cao nhất → (2) nếu hòa, Hit@1 dev → (3) nếu vẫn hòa, ít chunk hơn. Kết quả test chỉ để báo cáo, không dùng chỉnh tham số.

## Kết quả

Định nghĩa hit: chunk thuộc đúng `gold_source_id` + `gold_page` **và** chứa trọn `evidence_quote` (so sánh sau chuẩn hóa, không phân biệt hoa thường).

| Strategy | Split | Hit@1 (n/N) | Evidence Hit@3 (n/N) | Chunk count        | Thời gian                    | Chi phí |
| -------- | ----- | ----------- | -------------------- | ------------------ | ---------------------------- | ------- |
| A        | dev   | 6/15        | 9/15                 | 557                | embed 14,92 s; upsert 0,46 s | 0       |
| A        | test  | 3/5         | 3/5                  | 557                | (như trên)                   | 0       |
| B        | dev   | 8/15        | 12/15                | 367                | embed 14,92 s; upsert 0,28 s | 0       |
| B        | test  | 3/5         | 4/5                  | 367                | (như trên)                   | 0       |
| C        | dev   | 8/15        | 12/15                | 367 (dùng chung B) | không embed thêm             | 0       |
| C        | test  | 3/5         | 4/5                  | 367 (dùng chung B) | không embed thêm             | 0       |

Thời gian đo một lần trên CPU máy cá nhân (`time.perf_counter`), chưa gồm thời gian tải model; không đo riêng thời gian truy vấn.

| Strategy | Coherence trung bình /2 (n) | Metadata đủ và đúng (n/N) | Filter tuân thủ (n/N hoặc N/A) | Grounding 0/1/2 (số câu) và trung bình /2 |
| -------- | --------------------------- | ------------------------- | ------------------------------ | ----------------------------------------- |
| A        | 0,9 (n = 10)                | 15/15                     | N/A (không lọc)                | 0 / 1 / 4 — 1,8                           |
| B        | 1,7 (n = 10)                | 15/15                     | N/A (không lọc)                | 0 / 1 / 4 — 1,8                           |
| C        | 1,7 (n = 10, cùng chunk B)  | 15/15                     | test 1/1 (q18); dev 3/3        | 0 / 1 / 4 — 1,8                           |

Tỉ lệ "top-3 nằm trọn trong chương được yêu cầu" ở các câu có filter (tính từ trace): dev — A 0/3, B 0/3, C 3/3; test — A 1/1, B 1/1, C 1/1.

**Đường dẫn trace, nhãn thủ công và cách chọn mẫu:**

- Trace top-3 đầy đủ (câu hỏi, filter dùng, chunk ID, text, score, metadata, hit): [`starter/results/traces.jsonl`](../../starter/results/traces.jsonl); tổng hợp: [`summary.json`](../../starter/results/summary.json); thống kê: [`stats.json`](../../starter/results/stats.json).
- Metadata / filter / grounding: [`starter/results/audit_test.csv`](../../starter/results/audit_test.csv) — 5 câu test × 3 chiến lược × top-3 = 45 bản ghi. Grounding chấm một lần cho mỗi câu × chiến lược (ở dòng rank 1) sau khi đọc cả 3 chunk.
- Coherence: [`starter/results/coherence_sample.csv`](../../starter/results/coherence_sample.csv) — 10 vị trí chọn theo quy tắc cố định trước khi xem điểm: sắp các trang nội dung theo (document_id, page), lấy mỗi trang thứ ⌊80/10⌋ = 8 (tr. 1, 9, 17, 30, 38, 46, 54, 70, 78, 86); vị trí = đầu đoạn thứ hai của trang; chấm chunk A và B chứa vị trí đó (C dùng chunk B).
- **Phương pháp gán nhãn:** metadata được kiểm tra tự động bằng text trích lại độc lập từ PDF (mọi đoạn của chunk phải nằm đúng trang ghi trong `page`, header trang phải ghi đúng chương); grounding và coherence do Claude (LLM) đọc chunk và đề xuất điểm theo thang 0–2 của GUIDE.md, kèm lý do trong cột `notes`/`reason`; **tác giả duyệt lại nhãn**. Có nguy cơ thiên lệch vì người chấm không độc lập với người thiết kế pipeline.

## Phân tích và kết luận

- **So sánh A–B và B–C; 2 ví dụ sai có ID câu và nguồn:**
  - **A–B (chunking):** B tăng Evidence Hit@3 dev từ 9/15 lên 12/15 và Hit@1 dev từ 6/15 lên 8/15, coherence từ 0,9 lên 1,7, đồng thời giảm số chunk 557 → 367. Nguyên nhân chính: A cắt cố định 500 ký tự nên thường cắt giữa câu, thậm chí giữa từ; ở 8 câu (q06, q07, q10, q12, q13, q14, q18, q20) top-3 của A có chunk thuộc trang gold nhưng không chunk nào chứa trọn evidence; B đạt Hit@3 ở 7 câu trong số đó (trừ q13). B không thắng mọi câu: A đạt Hit@3 mà B trượt ở q01, q09 (dev) và q17 (test); ở q11 A đạt Hit@1 còn B chỉ đạt Hit@3 — chunk B dài hơn nên "loãng" hơn, chunk chứa evidence bị xếp sau các chunk khác cùng trang hoặc cùng chủ đề. Trên test, grounding bằng nhau (1,8): A mất điểm ở q18, B mất điểm ở q17.
  - **B–C (metadata filter):** Hit@1/Hit@3 giống hệt nhau ở cả dev và test, vì với cả 4 câu filter B đã đặt chunk đúng ở hạng 1. Filter chỉ thay đổi hạng 2–3: tỉ lệ top-3 nằm trọn trong chương được yêu cầu trên dev tăng từ 0/3 (B) lên 3/3 (C). Ví dụ q07: B trả về 2 chunk chương 1 (tr. 5, phần giới thiệu Freud) ở hạng 2–3; C thay bằng chunk chương 2. Trên test (q18) B vốn đã trả về toàn chương 2, nên test không cho thấy lợi ích của filter.
  - **Ví dụ sai 1 — q07, cấu hình A (gold: `psych2e-ch02`, tr. 35):** ranh giới chunk rơi giữa chữ "Freu|d's": chunk `psych2e-ch02:p35:f001` (hạng 1, score 0,701) bắt đầu bằng "d's theories is that many of his ideas are not falsifiable…", phần đầu evidence "a major criticism of Freu-" nằm ở chunk trước. Kết quả: đúng trang nhưng không hit; hạng 2–3 là chunk chương 1 (tr. 5). B giữ trọn câu trong `psych2e-ch02:p35:p001` → hit@1.
  - **Ví dụ sai 2 — q13, cả A/B/C (gold: `psych2e-ch03`, tr. 76):** câu hỏi paraphrase "Why can a neuron's electrical signal not be partially fired?" trong khi nguồn viết "The action potential is an all-or-none phenomenon…". Cả ba cấu hình chỉ trả về chunk cùng chủ đề ở tr. 74–76 (membrane potential, neuronal communication), score thấp (B hạng 1: 0,583), không chunk nào chứa định nghĩa all-or-none. Đây là lỗi của embedding/so khớp ngữ nghĩa với cách diễn đạt khác hẳn, không phải lỗi chunking hay metadata.
  - Thêm một trường hợp máy và người chấm khác nhau: **q20, A** — `is_hit_auto = False` ở cả 3 chunk vì không chunk nào chứa nguyên văn evidence, nhưng chunk hạng 2 (tr. 69) nêu "only display the smooth chin phenotype if they are homozygous for that recessive allele (bb)" → grounding 2. Hit@3 tự động là proxy chặt, không thay được nhãn thủ công.

- **Chiến lược chọn, đánh đổi, điều kiện áp dụng:**
  Theo tiêu chí chốt trước, **B và C hòa ở cả ba bậc** (Hit@3 dev 12/15, Hit@1 dev 8/15, 367 chunk). Chọn **C**, với lý do bổ sung **không nằm trong tiêu chí gốc** nhưng chỉ dùng dữ liệu dev: tỉ lệ top-3 đúng chương ở câu có filter dev 3/3 so với 0/3, không tốn thêm embedding hay lưu trữ. Lưu ý: `summary.json` in chung dev và test nên số test hiển thị cùng lúc; quyết định chỉ dựa trên các dòng dev và test không được dùng để chỉnh tham số. Đánh đổi: B/C có chunk dài hơn (trung bình 642 so với 466 ký tự) nên ngữ cảnh đầy đủ hơn nhưng đôi khi làm chunk chứa evidence bị xếp thấp hơn; C chỉ hữu ích khi người dùng thật sự cung cấp phạm vi chương, và sẽ hại nếu filter sai (loại mất chương đúng). Điều kiện áp dụng: corpus giáo trình có cấu trúc đoạn rõ, câu hỏi tiếng Anh, người dùng có ngữ cảnh chương.

- **Hạn chế của dữ liệu, nhãn, test nhỏ, đo thời gian/chi phí:**
  Test chỉ 5 câu (1 câu = 20 điểm %), chỉ 1 câu filter trong test → không đủ để kết luận tổng quát; dev và test cùng 3 chương nên không đo khả năng trên tài liệu mới. Chỉ 3 chương của một cuốn sách, một model nhỏ chỉ hiểu tiếng Anh, cắt ở ~256 token. Mỗi câu chỉ có một nguồn gold (chưa khai báo `alt_gold`), nên có thể bỏ sót bằng chứng tương đương ở trang khác. Chunk theo trang làm đứt các đoạn vắt trang (3/10 vị trí coherence của B bị trừ điểm vì lý do này). Nhãn coherence/grounding do LLM đề xuất và tác giả duyệt, không có người chấm độc lập. Thời gian đo một lần trên một máy, không lặp lại, không gồm thời gian tải model hay truy vấn. Exact search phù hợp với 924 dòng nhưng không phản ánh hiệu năng ANN ở quy mô lớn.

- **Nếu làm lại hoặc mở rộng, cải tiến gì?**
  (1) Cho chunk B nối qua ranh giới trang và lưu khoảng trang (`page_start`, `page_end`) để không đứt đoạn văn. (2) Lọc dòng credit ảnh và "LINK TO LEARNING" khỏi text. (3) Thử hybrid dense + BM25 để xử lý câu paraphrase/thuật ngữ như q13, chọn tham số trên dev. (4) Thêm metadata `section` (1.1, 1.2…) để lọc mịn hơn. (5) Mở rộng test (≥15 câu, nhiều câu filter hơn) và tách test theo chương chưa dùng cho dev. (6) Thử model lớn hơn hoặc đa ngữ để so sánh.

## Sử dụng AI

Dùng Claude (Claude Code) để giải thích đề, hỗ trợ viết code pipeline trong `starter/src/`, soạn bản nháp 20 câu benchmark từ PDF, đề xuất nhãn coherence/grounding và soạn bản nháp báo cáo này. Cách kiểm tra: chạy `--check-only` để xác minh mọi evidence nằm đúng trang gold; chạy pipeline hai lần để xác minh không nhân đôi; mọi số liệu trong báo cáo lấy từ `results/` của lần chạy 2026-11-14; tác giả đọc lại câu hỏi, nhãn thủ công và nội dung báo cáo.
