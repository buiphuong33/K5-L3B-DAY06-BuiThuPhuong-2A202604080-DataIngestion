# Day 06 · Data Ingestion Engineering

> ## Bài làm — Bùi Thu Phương (2A202604080, L3B)
>
> Corpus: OpenStax *Psychology 2e*, chương 1–3 (80 trang nội dung, CC BY 4.0). Embedding `sentence-transformers/all-MiniLM-L6-v2` (local, 384 chiều) + PostgreSQL 16 / pgvector 0.8.7, cosine, exact search. Ba cấu hình: **A** fixed 500/50 · **B** theo đoạn ≤ 900 ký tự · **C** = B + filter `chapter`. Báo cáo: [report/individual/2A202604080_BuiThuPhuong.md](report/individual/2A202604080_BuiThuPhuong.md). Hướng dẫn chạy: [Cách chạy bài làm](#cách-chạy-bài-làm) ở cuối file.

**Lab cá nhân** · **4 giờ** · **Dữ liệu tự chọn**

Biến tài liệu thành kho tri thức có thể truy xuất cho AI agent, rồi đo xem cách chuẩn bị dữ liệu nào hiệu quả nhất.

| 📄 Dữ liệu | 🧩 Chiến lược | 🎯 Benchmark |
|---|---|---|
| Tối thiểu **30 trang nội dung** | Tối thiểu **3 cấu hình** | Tối thiểu **20 câu hỏi** |

## Bắt đầu nhanh

Dùng [starter PostgreSQL + pgvector](starter/README.md) để dựng database và hoàn thiện các hàm TODO, hoặc tự chọn vector store tương đương. Starter chỉ là khung: **bạn tự hiện thực pipeline và benchmark**.

## 1. Xây pipeline

![Đọc tài liệu, chuẩn hóa, chia chunk, tạo vector, lưu và kiểm tra](assets/ingestion-pipeline.svg)

Chọn tài liệu được phép sử dụng; giữ **ID tài liệu, nguồn, trang/vị trí** và metadata phù hợp. Dùng embedding model thật qua API hoặc chạy local; lưu và truy xuất bằng pgvector, Qdrant, Chroma hoặc một store tương đương.

## 2. So sánh và đánh giá

![Ba chiến lược được đánh giá trên cùng corpus và benchmark dev/test](assets/benchmark-workflow.svg)

Dùng cùng dữ liệu, model và câu hỏi cho cả ba cấu hình. Tách **15 câu dev / 5 câu test** trước khi chạy; chọn cấu hình trên dev, rồi đánh giá test sau khi cố định. Mỗi câu hỏi cần có đoạn bằng chứng và trang nguồn; thiết kế bộ câu hỏi và đánh giá theo [BENCHMARK.md](BENCHMARK.md).

Đánh giá theo năm khía cạnh: **độ chính xác truy xuất**, **tính mạch lạc của chunk**, **tính hữu dụng của metadata**, **chất lượng grounding** và **tác động của chiến lược dữ liệu**. Giải thích lựa chọn bằng kết quả, ví dụ lỗi và các đánh đổi.

## 3. Chuẩn bị bài nộp

1. Chạy pipeline và lưu cấu hình, kết quả top-3, trace cùng nhãn đánh giá thủ công.
2. Điền [thông tin học viên](STUDENT.md), [nhật ký thí nghiệm](artifacts/experiment_log.csv) và bản sao [mẫu báo cáo cá nhân](report/individual/MSSV_HoTen.md).
3. Kiểm tra mã nguồn, cách chạy, manifest dữ liệu và checklist trong [SUBMISSION.md](SUBMISSION.md).

## Tài liệu hướng dẫn

| Bạn cần tìm | Tài liệu |
|---|---|
| Setup baseline PostgreSQL + pgvector | [starter/README.md](starter/README.md) |
| Các bước làm và cách tính chỉ số | [GUIDE.md](GUIDE.md) |
| Tiến độ trong 4 giờ | [CHECKPOINTS.md](CHECKPOINTS.md) |
| Năm tiêu chí benchmark và bộ câu hỏi | [BENCHMARK.md](BENCHMARK.md) |
| Tiêu chí chấm điểm | [RUBRIC.md](RUBRIC.md) |
| Quy tắc sử dụng dữ liệu, AI và API | [RULES.md](RULES.md) |
| Cách nộp bài | [SUBMISSION.md](SUBMISSION.md) |

[data/format-example.json](data/format-example.json) chỉ minh họa định dạng, không phải corpus đủ điều kiện. Phần xử lý và benchmark do bạn tự hiện thực; không bắt buộc xây chatbot.

---

## Cách chạy bài làm

Bài làm nằm trong thư mục [`starter/`](starter/). Mọi lệnh dưới đây chạy **từ thư mục `starter/`**. Đã chạy trên Windows 11, PowerShell, Python 3.13.1, Docker Desktop.

### Vị trí các thành phần

| Thành phần | Đường dẫn |
|---|---|
| Code pipeline | [`starter/src/`](starter/src/): `ingestion.py` (đọc PDF, chuẩn hóa) · `chunking.py` (A fixed / B theo đoạn) · `embeddings.py` (MiniLM local) · `store.py` (pgvector, upsert, filter) · `evaluation.py` (Hit@1 / Evidence Hit@3) · `run.py` (điều phối) |
| Manifest dữ liệu | [`starter/data/manifest.json`](starter/data/manifest.json): nguồn, giấy phép, khoảng trang, trang loại bỏ, quy tắc tính trang |
| Benchmark | [`starter/benchmark/questions.jsonl`](starter/benchmark/questions.jsonl) (20 câu, 15 dev / 5 test, 4 câu filter) · [`starter/benchmark/README.md`](starter/benchmark/README.md) (cách chia, kiểm chứng evidence, tiêu chí chọn chiến lược) |
| Experiment log | [`artifacts/experiment_log.csv`](artifacts/experiment_log.csv) |
| Kết quả | [`starter/results/`](starter/results/): `traces.jsonl` (top-3 từng câu × chiến lược) · `summary.json` (Hit@1/Hit@3 dev/test) · `stats.json` (số chunk, độ dài, thời gian, kiểm tra nạp lại) · `corpus_stats.json` · `ingestion_errors.json` · `audit_test.csv` (nhãn metadata / filter / grounding) · `coherence_sample.csv` (nhãn coherence) |
| Báo cáo | [`report/individual/2A202604080_BuiThuPhuong.md`](report/individual/2A202604080_BuiThuPhuong.md) |

### 1. Cài đặt

Yêu cầu: Docker Desktop (đang chạy), Python 3.11–3.14, mạng để tải image, thư viện và model lần đầu.

```powershell
cd starter
python -m venv .venv
.venv\Scripts\Activate.ps1                 # macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
pip install sentence-transformers==6.3.0 pymupdf==2.1
Copy-Item .env.example .env                # macOS/Linux: cp .env.example .env
```

Mở `starter/.env` và đặt:

```
EMBEDDING_MODEL=sentence-transformers/all-MiniLM-L6-v2
```

Không cần API key. Model (khoảng 90 MB) tự tải về cache Hugging Face trong lần chạy đầu.

### 2. Khởi động PostgreSQL + pgvector

```powershell
docker compose -p day6_student_starter up -d --wait
python scripts/check_setup.py              # kỳ vọng: PostgreSQL 16.x | pgvector 0.8.7 | Setup OK
```

### 3. Lấy dữ liệu

File PDF **không được commit** (xem `.gitignore`). Tạo lại như sau:

1. Mở *Psychology 2e* trên OpenStax (https://openstax.org/details/books/psychology-2e, CC BY 4.0), đọc bản web chương 1, 2, 3.
2. In 3 chương ra một file PDF bằng **"Save as PDF" của Chrome/Edge**. Không dùng "Microsoft Print to PDF", vì cách này biến chữ thành hình vẽ và không trích được text.
3. Lưu thành `starter/data/Psychology2e.pdf`. Bản dùng trong bài có **101 trang**; khoảng trang của từng chương nằm trong `manifest.json`.

Kiểm tra file đọc được chữ:

```powershell
python -c "import pymupdf; d=pymupdf.open('data/Psychology2e.pdf'); print(d.page_count, len(d[5].get_text()))"
```

Kết quả phải là `101` và một số lớn hơn 0. Nếu bản in của bạn có số trang khác, cập nhật `pdf_page_range` / `excluded_pages` trong manifest và `gold_page` trong benchmark.

### 4. Chạy

```powershell
python -m src.run --check-only    # đọc corpus + kiểm chứng benchmark, chưa embed
python -m src.run                 # chunk A/B, embed, upsert vào pgvector, chạy 20 câu × A/B/C, ghi results/
python -m src.run                 # chạy lần 2: kiểm tra nạp lại không nhân đôi
```

Kết quả mong đợi:
- `--check-only`: `Loaded 80 content pages, 0 errors` và `Benchmark OK: all evidence verified.`
- Chạy đầy đủ: in Hit@1 / Hit@3 theo `strategy/split`. Ở lần chạy 2026-11-14: A dev 6/15 · 9/15, B dev 8/15 · 12/15, C dev 8/15 · 12/15.
- Sau lần chạy thứ hai, trong `results/stats.json`: `rows_before` = `rows_after` = `{"A": 557, "B": 367}`.

Lưu ý:
- Lệnh chạy đầy đủ **ghi đè** `audit_test.csv` và `coherence_sample.csv` bằng bản trống (chưa có nhãn). Muốn chạy lại mà không mất nhãn thủ công đã chấm, sao lưu 2 file này trước khi chạy.
- Nếu Docker hoặc model lỗi, pipeline dừng và báo lỗi; không có cơ chế thay bằng vector giả.

### 5. Dừng database

```powershell
docker compose -p day6_student_starter stop    # giữ dữ liệu trong volume
```
