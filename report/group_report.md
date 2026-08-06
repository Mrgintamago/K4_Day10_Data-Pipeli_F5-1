# Group Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin bài nộp

| Thông tin | Nội dung |
| --- | --- |
| Khóa/Lớp | K4 |
| Tên nhóm | **F5-1** |
| Repository | https://github.com/Mrgintamago/K4_Day10_Data-Pipeli_F5-1 |
| Ngày hoàn thành | 2026-08-06 |

### Thành viên và phân công

Nhóm chia việc theo **hướng đi của dữ liệu**, không chia theo file, để mỗi người sở hữu trọn một đoạn của pipeline và tự chẩn đoán được lỗi thuộc đoạn đó.

| STT | Họ và tên | MSSV | Vai trò chính | Module/deliverable sở hữu |
| --: | --- | --- | --- | --- |
| 1 | Cao Các Tường | 2A202601236 | **Đưa dữ liệu vào** — ingestion & repair từ raw | `src/ingestion/crossref.py`; `data/raw/*`; xác minh lineage `papers_clean_repaired.*`; `tests/test_crossref.py` |
| 2 | Lưu Nguyễn Ngọc Hân | 2A202601386 | **Biến đổi dữ liệu** — cleaning, test set, corruption | `src/ingestion/cleaning.py`, `src/evaluation/testset.py`, `src/ingestion/corruption.py`; `data/clean/*`, `data/eval/test_set.json`, `corruption_log.json` |
| 3 | Trần Quang Sáng | 2A202601446 | **Quan sát & báo cáo** — quality, freshness, 2 report kỹ thuật | `src/observability/quality.py`, `src/observability/reporting.py`; `data/quality/*`, `phase1_report.md`, `corruption_report.md` |
| 4 | Nguyễn Xuân Quang | 2A202601776 | **Truy tìm & tích hợp** — embedding/index, evaluation, 2 entrypoint; chủ trì tổng hợp | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py`, `script/ask.py`; `data/embeddings/*`, `data/results/*`; `group_report.md` |

## 2. Tóm tắt kết quả

Nhóm hoàn thành **toàn bộ 12 hàm `TODO(student)`** và chạy sạch cả hai entrypoint từ đầu đến cuối.

Baseline sinh đủ artifact: raw snapshot + raw records (24 bản ghi Crossref), clean dataset 24 dòng đúng 10 cột theo contract, embedding manifest với collection `papers-baseline` (MiniLM-L6-v2, cosine, `top_k=4`), test set cố định 73 câu, metrics + answers, 7 quality check và freshness report, cùng `phase1_report.md`. Baseline đạt `retrieval_hit_rate` 1.000, `mean_token_f1` 0.921, `judge_accuracy` 0.918 và `mean_judge_score` 4.67/5, với **judge thật chạy đủ 73/73** (không rơi vào heuristic dự phòng).

Corruption tạo 6 loại lỗi có chủ đích, kéo dataset từ 24 xuống 22 dòng. Ảnh hưởng rõ nhất là **nhóm lỗi phá nội dung** — blank summary và noise summary — vì chúng đánh trực tiếp vào `text_for_embedding`, làm cả retrieval lẫn câu trả lời cùng hỏng: `judge_accuracy` rơi từ 0.918 xuống **0.260** (−0.658) và `retrieval_hit_rate` từ 1.000 xuống **0.740** (−0.260). Đáng chú ý, `stale_published_date` **không** làm metric thay đổi nhưng khiến freshness fail hoàn toàn (22/22 dòng stale) — đây chính là dạng lỗi im lặng mà chỉ observability bắt được.

Repair chạy lại cleaning từ raw records và phục hồi **chính xác đến từng chữ số**: cả bốn metric trở về đúng giá trị baseline, quality `overall_pass` về `true`, freshness về `is_fresh: true` với 0 dòng stale.

Giới hạn còn lại: Crossref không trả trường `subject` nên `categories_joined` rỗng ở cả 24 bản ghi, và corpus 24 tài liệu là quá nhỏ để `retrieval_hit_rate` phân biệt được chất lượng retrieval ở mức tinh.

## 3. Kiến trúc và luồng dữ liệu

### Luồng end-to-end

```text
Crossref API
    -> data/raw/crossref_response.json   (raw nguyên vẹn, lưu TRƯỚC khi parse)
    -> data/raw/crossref_records.json    (PaperRecord đã parse)
    -> data/clean/papers_clean.csv|.json (10 cột, paper_id unique)
    -> data/embeddings/ + Chroma collection papers-baseline
    -> data/results/baseline_metrics.json + baseline_answers.json
    -> data/quality/ + freshness_report.json
    -> data/reports/phase1_report.md
    -> corruption (6 loại) -> papers-corrupted -> corrupted_metrics.json
    -> repair TỪ raw       -> papers-repaired  -> repaired_metrics.json
    -> data/reports/corruption_report.md
```

`data/raw/` là **bất biến** và là nguồn duy nhất để repair. Mọi đường dẫn lấy từ `Paths` trong `src/core/config.py`, không hard-code ở bất kỳ đâu.

### Trách nhiệm của từng khối

| Khối | Input | Xử lý chính | Output/artifact | Owner |
| --- | --- | --- | --- | --- |
| Ingestion | Crossref REST API | Fetch có retry/backoff, lưu raw trước khi parse, map sang `PaperRecord` | `data/raw/crossref_response.json`, `crossref_records.json` | Tường |
| Cleaning | 24 `PaperRecord` | Chuẩn hóa text, parse ngày, tính `age_days`, dựng `text_for_embedding`, dedupe | `data/clean/papers_clean.csv|.json` | Hân |
| Embedding/index | Clean dataframe | MiniLM-L6-v2 (384 chiều), Chroma cosine, collection riêng cho từng trạng thái | `data/embeddings/papers_embeddings*.json` | Quang |
| Evaluation | Clean data + test set | Sinh 73 câu hỏi, chạy QA, chấm 4 metric + LLM judge | `data/eval/test_set.json`, `data/results/*_metrics.json`, `*_answers.json` | Hân (test set), Quang (chạy & wiring) |
| Observability | Dataframe từng trạng thái | 7 quality check + freshness theo ngưỡng 180 ngày | `data/quality/quality_*.json`, `freshness_report_*.json` | Sáng |
| Corruption/repair | Clean baseline / raw records | 6 loại lỗi có log; repair = chạy lại cleaning từ raw | `papers_clean_corrupted.*`, `corruption_log.json`, `papers_clean_repaired.*` | Hân (corrupt), Tường (repair & lineage) |
| Orchestration | Tất cả | Ráp thứ tự, chặn sớm khi thiếu artifact, giữ 3 trạng thái độc lập | `run_phase1.py`, `run_corruption_flow.py`, 2 report markdown | Quang |

## 4. Cách tái hiện kết quả

### Cấu hình không chứa secret

| Biến/cấu hình | Giá trị sử dụng |
| --- | --- |
| `LLM_PROVIDER` | `openrouter` (endpoint tương thích OpenAI) |
| `LLM_MODEL` | `deepseek-v4-pro` |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` (384 chiều) |
| Số lượng Crossref records | 24 (`max_results=24`) |
| Retrieval `top_k` | 4 |
| Freshness threshold | 180 ngày |
| Random seed | Có — `corrupt_clean_dataframe` dùng `random.Random` với seed cố định để corruption tái lập được |

Không có API key, `.env` hay token nào xuất hiện trong source, report hoặc log.

### Lệnh cài đặt

```bash
uv sync --python 3.11
```

Dự án yêu cầu Python `>=3.11,<3.14`. Nhóm dùng **3.11.9**.

### Lệnh chạy

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
```

Nếu `huggingface_hub` báo `Cannot send a request, as the client has been closed`, chạy với `HF_HUB_OFFLINE=1` — model đã cache cục bộ, lỗi này chỉ do HF cố kiểm tra bản mới qua mạng.

### Kết quả tái hiện

| Lệnh | Trạng thái | Thời điểm chạy gần nhất | Bằng chứng |
| --- | --- | --- | --- |
| Baseline pipeline | **Thành công** — 7/7 bước | 2026-08-06 17:27 | `data/results/baseline_metrics.json`, `data/reports/phase1_report.md` |
| Corruption flow | **Thành công** — 5/5 bước | 2026-08-06 17:35 | `corrupted_metrics.json`, `repaired_metrics.json`, `data/reports/corruption_report.md` |
| Test suite | **17 passed** | 2026-08-06 | `tests/test_crossref.py` (6), `tests/test_pipelines.py` (11) |

## 5. Ingestion, cleaning và data contract

### Nguồn dữ liệu

| Thuộc tính | Giá trị |
| --- | --- |
| Source | Crossref REST API — `https://api.crossref.org/works` |
| Query | `agentic retrieval augmented generation large language model` |
| Filter | `from-pub-date:2026-02-07`, `has-abstract:true` |
| Thời điểm lấy dữ liệu | 2026-08-06, lưu snapshot một lần rồi khóa |
| Số record nhận được | 24 |
| Cơ chế retry/backoff | Retry với backoff cho `429`/`503`; raw response ghi xuống đĩa **trước** khi parse |

Sau lần fetch đầu, `REFRESH_SOURCE` được giữ tắt. Crossref là API sống — gọi lại sẽ ra tập dữ liệu khác và làm hỏng khả năng so sánh giữa ba trạng thái.

### Raw và clean schema

| Trường | Kiểu | Bắt buộc? | Ý nghĩa | Xử lý khi thiếu/sai |
| --- | --- | --- | --- | --- |
| `paper_id` | str | **Có** | DOI — khóa xuyên suốt raw → clean → index → eval | Loại bản ghi nếu rỗng |
| `title` | str | **Có** | Tiêu đề bài báo | Loại bản ghi nếu rỗng |
| `summary` | str | **Có** | Abstract đã bỏ thẻ HTML | Loại bản ghi nếu rỗng |
| `published` | str (ISO date) | Có | Ngày xuất bản | Loại nếu không parse được |
| `age_days` | int | Có | Số ngày từ lúc xuất bản — đầu vào freshness | Tính từ `published` |
| `authors_joined` | str | Không | Danh sách tác giả đã nối phẳng | Chuỗi rỗng |
| `categories_joined` | str | Không | Chủ đề đã nối phẳng | **Rỗng toàn bộ 24/24** — Crossref không trả `subject` |
| `text_for_embedding` | str | **Có** | Chuỗi thực sự đem đi embed | Dựng lại sau mọi biến đổi |
| `abs_url` | str | Không | Link trang abstract | Chuỗi rỗng |
| `pdf_url` | str | Không | Link PDF | Rỗng ở 15/24 — nguồn không cung cấp |

Metadata dạng danh sách được nối phẳng vì Chroma không nhận cấu trúc lồng nhau.

### Quy tắc cleaning

| Quy tắc | Quality dimension | Số record bị tác động | Cách xác minh |
| --- | --- | ---: | --- |
| Loại bản ghi thiếu `paper_id`/`title`/`summary` | Completeness | 0 | `quality_baseline.json` → `paper_id_not_null`, `title_not_blank` pass |
| Chuẩn hóa khoảng trắng, bỏ thẻ HTML trong abstract | Validity | 24 | `summary_length` min 826 / max 2610 ký tự |
| Dedupe theo `paper_id` | Uniqueness | 0 | `paper_id_unique` pass, 24 unique |
| Parse ngày và tính `age_days` | Timeliness | 24 | `freshness_report.json`, 0 dòng stale |

**`text_for_embedding`** ghép `title` + `authors` + `summary` thành một chuỗi. Tách thành cột riêng vì hai lý do: quyết định "embed cái gì" trở nên hiện rõ và kiểm tra được thay vì giấu trong code; và khi corruption phá `summary`, phải **dựng lại** cột này thì lỗi mới thực sự chạm tới tầng embedding.

**Document ID** dùng chính DOI (`paper_id`). Ổn định là bắt buộc: `retrieval_hit_rate` so `retrieved_doc_ids` với `ground_truth_doc_ids`, nên nếu ID đổi giữa các lần chạy thì hit rate tụt vì lỗi kỹ thuật chứ không phải vì chất lượng dữ liệu.

**`age_days`** = số ngày từ `published` đến thời điểm chạy, so với ngưỡng 180 ngày để quyết định một dòng có stale hay không.

## 6. Evaluation setup

| Thành phần | Cấu hình thực tế |
| --- | --- |
| Số câu hỏi | **73** |
| Các `question_type` | `summary` (24), `authors` (24), `date` (24), `retrieval` (1) |
| Ground-truth document ID | Sinh trực tiếp từ `paper_id` của bản ghi tạo ra câu hỏi |
| Embedding model | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector store/collection | ChromaDB, cosine — `papers-baseline` / `papers-corrupted` / `papers-repaired` |
| Retrieval `top_k` | 4 |
| LLM provider/model | `openrouter` (endpoint tương thích OpenAI) / `deepseek-v4-pro` |
| Test set dùng chung | `data/eval/test_set.json` — **một file duy nhất cho cả ba trạng thái** |

**Không có loại câu hỏi `categories`** dù Guide có gợi ý: Crossref không trả trường `subject` cho tập DOI này nên `categories_joined` rỗng toàn bộ, không tạo được ground truth. Đây là giới hạn của nguồn, không phải thiếu sót của implementation.

**Vì sao test set phải giữ nguyên:** so sánh chỉ có nghĩa khi **đúng một biến thay đổi** — ở đây là chất lượng dữ liệu. Nếu sinh lại test set giữa các lần đo, chênh lệch metric không còn quy được cho corruption. Vì thế `REFRESH_TEST_SET` giữ tắt và test set bị khóa ngay sau khi baseline chốt. Ba trạng thái cũng dùng chung `top_k=4`, cùng evaluator và cùng model.

Ba collection tách tên là bắt buộc: `LocalEmbeddingIndex.build` **xóa collection trùng tên rồi tạo lại**, nên dùng chung một tên sẽ phá index baseline ngay khi chạy corruption.

## 7. Kết quả baseline

### Artifact checklist

| Artifact | Đường dẫn thực tế | Trạng thái | Ghi chú |
| --- | --- | --- | --- |
| Raw response/records | `data/raw/` | **Có** | 24 bản ghi, `paper_id` 0 rỗng / 0 trùng |
| Cleaned dataset | `data/clean/papers_clean.csv|.json` | **Có** | 24 dòng, đủ 10 cột |
| Embedding manifest/index | `data/embeddings/papers_embeddings.json` | **Có** | collection `papers-baseline` |
| Evaluation set | `data/eval/test_set.json` | **Có** | 73 câu, đã khóa |
| Baseline metrics | `data/results/baseline_metrics.json` | **Có** | kèm `baseline_answers.json` 73 mẫu |
| Quality/freshness | `data/quality/` | **Có** | `quality_baseline.json`, `freshness_report.json` |
| Baseline report | `data/reports/phase1_report.md` | **Có** | mọi số khớp JSON |
| Agent demo | `data/results/agent_demo_answers.json` | **Có** | agent trả lời có trích `paper_id` |

### Baseline metrics

| Metric | Giá trị | Diễn giải |
| --- | ---: | --- |
| `retrieval_hit_rate` | **1.0000** | 0/73 miss. Corpus 24 tài liệu mà `top_k=4` — mỗi lần hỏi lấy 1/6 corpus, nên trúng là dễ. **Không** nên đọc là "retrieval hoàn hảo tuyệt đối"; giá trị của nó là tạo trần 1.0 để corruption có chỗ kéo xuống và đo được |
| `mean_token_f1` | **0.9206** | QA là *extractive* nên câu trả lời thường trùng nguyên văn ground truth. Metric tất định, không phụ thuộc LLM — dùng làm mỏ neo kiểm chứng |
| `judge_accuracy` | **0.9178** | 67/73 câu được LLM judge chấm đúng |
| `mean_judge_score` | **4.6712** / 5 | Phân bố nhị cực: 67 câu điểm 5, 6 câu điểm 1 |
| Ragas | N/A | Chỉ chạy khi `RUN_RAGAS=1`; nhóm tắt vì tốn quota LLM và không thuộc phần bắt buộc |

**Kiểm chứng judge:** `baseline_answers.json` có **0/73** bản ghi chứa `"Fallback heuristic judge"`. Điều này quan trọng — khi LLM judge lỗi, `metrics.py` âm thầm rơi xuống heuristic dựa trên token F1, khiến `judge_accuracy` trông như một cột độc lập nhưng thực chất là token F1 khoác áo khác. Nhóm đã gặp đúng tình huống này giữa buổi (xem mục 11).

## 8. Data quality và freshness

### Quality checks

| Check | Quality dimension | Ngưỡng/kỳ vọng | Kết quả baseline | Bằng chứng |
| --- | --- | --- | --- | --- |
| `required_columns` | Schema conformity | Đủ 10 cột contract | **Pass** — thiếu 0 | `quality_baseline.json` |
| `row_count` | Completeness | > 0 | **Pass** — 24 | `quality_baseline.json` |
| `paper_id_not_null` | Completeness | 0 null | **Pass** — 0 | `quality_baseline.json` |
| `paper_id_unique` | Uniqueness | 0 trùng | **Pass** — 0 | `quality_baseline.json` |
| `title_not_blank` | Completeness | 0 rỗng | **Pass** — 0 | `quality_baseline.json` |
| `summary_length` | Validity | Không có dòng rỗng | **Pass** — 0 rỗng, 826–2610 ký tự | `quality_baseline.json` |
| `freshness` | Timeliness | `age_days` ≤ 180 | **Pass** — 0 stale | `quality_baseline.json` |

`overall_pass: true`. Quality check **cố ý không** đặt điều kiện fail trên `categories_joined` (đánh dấu `categories_are_optional: true`) — nếu để fail thì baseline sạch cũng fail, và toàn bộ phép so sánh baseline/corrupted mất ý nghĩa.

### Freshness

| Thuộc tính | Giá trị |
| --- | --- |
| Freshness được đo tại | Clean dataframe của từng trạng thái, qua cột `age_days` và `published` |
| Timestamp mới nhất | `2026-08-01` (cũ nhất `2026-02-12`) |
| Ngưỡng freshness | 180 ngày |
| Trạng thái baseline | **Fresh** — `is_fresh: true` |
| Lý do | 0/24 dòng vượt ngưỡng; filter `from-pub-date` khi gọi Crossref đã giới hạn sẵn trong 180 ngày |

## 9. Corruption scenarios và repair

| Corruption | Cách tạo | Record bị tác động | Quality signal kỳ vọng | Tác động thực tế | Cách repair |
| --- | --- | ---: | --- | --- | --- |
| `drop_latest` | Xóa 20% bản ghi mới nhất theo `age_days` | 5 | Freshness: `latest_published` lùi lại | 24 → 22 dòng; mất 5 `paper_id`, các câu hỏi về chúng không còn tài liệu để trúng | Chạy lại cleaning từ raw |
| `blank_summary` | Xóa nội dung `summary` ở 15% dòng | 3 | Quality: `summary_length` fail | **Fail** — `min_chars` 826 → 0 | Chạy lại cleaning từ raw |
| `noise_summary` | Chèn token `corruptnoise` vào summary | 4 | Không check nào bắt trực tiếp | Không có tín hiệu quality, nhưng kéo `token_f1` xuống | Chạy lại cleaning từ raw |
| `truncate_title` | Cắt tiêu đề còn 40 ký tự | 19 | Độ dài title bất thường | Lookup theo tiêu đề hỏng | Chạy lại cleaning từ raw |
| `stale_published_date` | Lùi ngày xuất bản 5 năm | 19 | Freshness fail | **Fail** — `latest_published` 2026-08-01 → **2021-07-02**, stale 22/22 | Chạy lại cleaning từ raw |
| `duplicate_rows` | Nhân bản 15% dòng | 3 | Quality: `paper_id_unique` fail | **Fail** — 3 dòng trùng; context lặp đẩy tài liệu khác ra khỏi top-4 | Chạy lại cleaning từ raw |

Sau corruption: 24 → **22 dòng**, trong đó chỉ **19 `paper_id` duy nhất**.

Corruption log:

- Đường dẫn: `data/results/corruption_log.json`
- Trạng thái: **Có**
- Nhận xét: log ghi `baseline_rows`, `corrupted_rows`, danh sách `paper_id` trước/sau, và với mỗi sự kiện có `corruption_type`, `affected_paper_ids`, `parameter`, `before`, `after`. Đủ để tái lập và đối chiếu từng thay đổi.

**Repair đảm bảo phục hồi từ nguồn đáng tin cậy, không phải che kết quả lỗi.** `corruption_flow.py` gọi `load_raw_records(paths.raw_records_json)` rồi `build_clean_dataframe(...)` — tức là chạy lại đúng bước cleaning trên raw snapshot, **không hề đọc `papers_clean.csv` của baseline**. Bốn bằng chứng đã kiểm:

1. `repaired.paper_id ⊆ raw.paper_id` → `True`
2. `repaired == baseline` so sánh từng ô → `True`
3. 5 `paper_id` mất khi corrupt đều lấy lại được → 24/24
4. Raw snapshot không đổi trước và sau corruption

Điểm quan trọng: nếu chỉ copy baseline thì chỉ chứng minh được "nhóm còn giữ backup". Chạy lại từ raw chứng minh thêm rằng **cleaning là tất định** — chạy lại cho kết quả y hệt. Nếu repaired *khác* baseline, đó sẽ là tín hiệu cleaning phụ thuộc thứ tự dòng hoặc thời điểm chạy.

## 10. So sánh baseline, corrupted và repaired

| Metric/signal | Baseline | Corrupted | Repaired | Thay đổi do corruption | Mức phục hồi | Nhận xét |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | **0.7397** | 1.0000 | **−0.2603** | **100%** | Mất tài liệu + duplicate đẩy tài liệu đúng ra khỏi top-4 |
| `mean_token_f1` | 0.9206 | **0.2686** | 0.9206 | **−0.6519** | **100%** | Tụt mạnh nhất — metric tất định nên đây là bằng chứng chắc nhất |
| `judge_accuracy` | 0.9178 | **0.2603** | 0.9178 | **−0.6575** | **100%** | 67/73 → 19/73 câu đúng |
| `mean_judge_score` | 4.6712 | **2.0411** | 4.6712 | **−2.6301** | **100%** | Trên thang 1–5 |
| Quality checks pass/fail | `true` | **`false`** | `true` | 3 check fail | **100%** | Fail: `paper_id_unique`, `summary_length`, `freshness` |
| Freshness status | Fresh | **Stale** | Fresh | 0 → 22 dòng stale | **100%** | `latest_published` 2026-08-01 → 2021-07-02 |

Ba trạng thái dùng chung `data/eval/test_set.json` (73 câu), chung `top_k=4`, chung evaluator và chung model. Judge thật chạy đủ trên cả ba bộ: **fallback 0/73** mỗi bộ.

### Kết luận có quan hệ nhân quả

**1. `blank_summary` + `duplicate_rows` → quality signal fail → retrieval và answer metric cùng tụt.**
Xóa nội dung 3 summary khiến `summary_length` chuyển fail (`min_chars` 826 → 0), và nhân bản 3 dòng khiến `paper_id_unique` fail. Vì `text_for_embedding` được dựng lại sau khi corrupt, vector đem đi index thực sự bị hỏng — `retrieval_hit_rate` xuống 0.7397 (−0.2603) và `mean_token_f1` xuống 0.2686 (−0.6519). Đây là chuỗi hoàn chỉnh từ *thay đổi dữ liệu* → *tín hiệu quan sát* → *chất lượng agent*.

**2. Repair từ raw → quality và freshness phục hồi → metric phục hồi hoàn toàn.**
Chạy lại cleaning từ `crossref_records.json` đưa dataset về 24 dòng / 24 `paper_id` duy nhất, `overall_pass` về `true`, `is_fresh` về `true` với 0 dòng stale. Cả bốn metric trở về đúng giá trị baseline — khớp tuyệt đối, không phải xấp xỉ.

**3. `stale_published_date` → freshness fail nhưng metric KHÔNG đổi — phát hiện quan trọng nhất về mặt quan sát.**
Lùi ngày xuất bản 5 năm không làm hỏng nội dung nào, nên retrieval và câu trả lời đều không bị ảnh hưởng. Nhưng freshness fail hoàn toàn: 22/22 dòng stale, `latest_published` lùi về 2021-07-02. Đây chính là lý do observability tồn tại tách khỏi evaluation: **có những lỗi dữ liệu mà metric hoàn toàn im lặng**. Một pipeline chỉ nhìn metric sẽ báo "xanh" trong khi đang phục vụ dữ liệu cũ 5 năm.

## 11. Vấn đề tích hợp quan trọng

Nhóm gặp ba vấn đề tích hợp đáng ghi lại. Vấn đề thứ nhất ảnh hưởng số liệu nặng nhất:

**Vấn đề 1 — 24/24 câu hỏi loại `authors` fail hệ thống**

- **Triệu chứng:** loại `authors` có `token_f1 = 0.000` và judge score = 1.0 ở **cả 24 câu**, kéo `judge_accuracy` toàn cục xuống 0.589.
- **Nguyên nhân:** test set đặt câu hỏi dạng `"Who are the authors of the paper titled ..."`, nhưng `src/retrieval/qa.py::_extract_answer` chỉ nhận diện chuỗi `"who authored"` hoặc `"list the authors"`. Không khớp mẫu nào, câu hỏi rơi vào nhánh mặc định và trả về `first_sentence(summary)` — tức là trả tóm tắt cho câu hỏi về tác giả.
- **Cách xử lý:** đổi mẫu câu trong `src/evaluation/testset.py` thành `"Who authored the paper titled ..."`, kèm comment giải thích tại chỗ để không ai đổi ngược lại. Sinh lại test set một lần duy nhất rồi khóa.
- **Cách xác minh:** `mean_token_f1` 0.619 → **0.921** và `judge_accuracy` 0.589 → **0.918**. Dùng `token_f1` làm bằng chứng vì nó tất định, không phụ thuộc LLM.

**Vấn đề 2 — `judge_accuracy` là số giả**

- **Triệu chứng:** một lần chạy giữa buổi cho `judge_accuracy` 0.918 trông rất đẹp.
- **Nguyên nhân:** provider LLM hết credit và trả `402`. `metrics.py::_judge_answer` bắt mọi exception rồi âm thầm rơi xuống heuristic dựa trên token F1 — pipeline không hề báo lỗi, nhưng **73/73 bản ghi** có `reasoning` là `"Fallback heuristic judge used because the LLM evaluator was unavailable"`.
- **Cách xử lý:** đổi sang `deepseek-v4-pro` qua endpoint tương thích OpenAI và chạy lại toàn bộ.
- **Cách xác minh:** đếm số bản ghi chứa `"Fallback heuristic"` trong cả ba file `*_answers.json` — phải bằng 0. Nhóm giờ coi đây là bước kiểm bắt buộc trước khi tin bất kỳ con số judge nào.

**Vấn đề 3 — JSON artifact không hợp lệ do NaN**

- **Triệu chứng:** `papers_clean_corrupted.json` và `papers_embeddings_corrupted.json` chứa token `NaN` trần. Python đọc được, nhưng `jq` và `JSON.parse` từ chối vì RFC 8259 không cho phép.
- **Nguyên nhân:** `pd.read_csv` biến ô trống (`categories_joined`, `pdf_url`) thành `NaN` float; `json.dumps` in ra `NaN`. Baseline không dính vì đi thẳng từ bộ nhớ. Rủi ro kèm theo: `first_sentence(NaN)` **crash `TypeError`** nếu ai chạy lại từ file CSV corrupted.
- **Cách xử lý:** hai lớp bảo vệ độc lập — `sanitize_missing()` ở tầng điều phối (`pipelines/`) chuẩn hóa `NaN → ""` trước khi lưu và trước khi index; `_records_for_json()` trong `corruption.py` dùng `df.to_json()` để `NaN → null`. Phát hiện thêm rằng `to_csv` không phân biệt được `""` với NaN, nên corruption lưu một ký tự khoảng trắng để lỗi vẫn nhìn thấy được trong CSV.
- **Cách xác minh:** parse toàn bộ `data/**/*.json` bằng parser nghiêm ngặt (`parse_constant` ném lỗi) — không file nào lỗi.

## 12. Giới hạn và hướng cải thiện

| Giới hạn hiện tại | Ảnh hưởng | Hướng cải thiện có thể kiểm chứng |
| --- | --- | --- |
| Corpus chỉ 24 tài liệu, `top_k=4` | `retrieval_hit_rate` baseline đạt trần 1.0, không phân biệt được chất lượng retrieval ở mức tinh | Tăng `max_results` lên 200+; kỳ vọng baseline hit rate xuống dưới 1.0 và metric trở nên nhạy hơn |
| `categories_joined` rỗng 24/24 | Mất một chiều metadata; không tạo được câu hỏi loại `categories` | Bổ sung nguồn thứ hai (OpenAlex/Semantic Scholar) để lấy subject, hoặc phân loại bằng LLM rồi đối chiếu thủ công |
| `qa.py` khớp tiêu đề bằng regex **nháy đơn**, test set dùng nháy kép | `index.lookup()` không bao giờ kích hoạt; 6 câu fail vì semantic search không đưa đúng paper lên đầu | **Cố ý giữ nguyên** — xem giải thích bên dưới |
| Chỉ 1 câu hỏi loại `retrieval` | Không đủ mẫu để kết luận về loại này | Sinh thêm 20+ câu `retrieval` với ground truth nhiều tài liệu |
| Judge dùng một model duy nhất | Điểm judge mang thiên lệch của riêng model đó | Chấm chéo bằng 2 provider và báo cáo độ đồng thuận |
| `mean_token_f1` phân bố nhị cực (1.0 hoặc 0.0) | Do QA là extractive, metric không phân biệt được các mức đúng một phần | Chuyển sang QA sinh câu trả lời, hoặc bổ sung metric ngữ nghĩa |

**Vì sao cố ý không sửa lỗi nháy đơn:** nếu đổi test set sang nháy đơn, `index.lookup()` sẽ trả đúng tài liệu bằng **tra cứu tiêu đề chính xác** và bỏ qua embedding. Khi đó corruption làm hỏng `text_for_embedding` sẽ **không** kéo `retrieval_hit_rate` xuống — che mất chính hiện tượng bài lab cần đo. Baseline 0.918 với 6 lỗi giải thích được có giá trị hơn 1.000 đạt được bằng cách vô hiệu hóa tầng retrieval.

## 13. Checklist trước khi nộp

- [x] Thông tin nhóm và repository chính xác.
- [x] Phân công khớp với module, artifact và kết quả thực tế.
- [x] Lệnh tái hiện đã được chạy lại trên phiên bản dùng để nộp.
- [x] Baseline, corrupted và repaired dùng cùng evaluation set (73 câu, `top_k=4`, cùng model).
- [x] Bảng metrics khớp với các file trong `data/results/` — đã đối chiếu từng số.
- [x] Quality/freshness conclusions khớp với `data/quality/`.
- [x] Các đường dẫn báo cáo và artifact truy cập được.
- [ ] Mỗi thành viên đã hoàn thành báo cáo vai trò riêng.
- [x] Không có `.env`, API key, token hoặc secret trong source, report, log hay ảnh.
- [x] Không còn `NotImplementedError` nào trong `src/` — 12/12 hàm đã hoàn thành.
- [x] Không hard-code đường dẫn; mọi path lấy từ `Paths` trong `src/core/config.py`.
- [x] Test suite pass: **17 passed**.

---

**Tài liệu bổ sung của nhóm:** [`THEORY.md`](../THEORY.md) — giải thích lý thuyết từng bước · [`CHANGELOG.md`](../CHANGELOG.md) — nhật ký buổi theo task, kèm bằng chứng · [`report/demo_evidence.md`](demo_evidence.md) — phân tích 73 mẫu và ví dụ hit/miss · `script/ask.py` — CLI hỏi–đáp trên cả ba trạng thái dữ liệu.
