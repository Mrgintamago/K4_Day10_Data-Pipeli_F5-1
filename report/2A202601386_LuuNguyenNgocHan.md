# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                                |
| --------------- | ------------------------------------------------------- |
| Họ và tên       | Lưu Nguyễn Ngọc Hân                                    |
| MSSV            | 2A202601386                                             |
| Khóa/Lớp        | K4                                                      |
| Tên nhóm        | F5-1                                                    |
| Vai trò chính  `| **Biến đổi dữ liệu** — clean dataframe, test set, controlled corruption |
| Repository      | `K4_Day10_Data-Pipeli_F5-1`                             |
| Ngày hoàn thành | 2026-08-06                                              |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

Khối DATA được chia theo *hướng của dữ liệu*: TV1 giữ mọi thứ liên quan đến raw (fetch, snapshot, repair-from-raw), TV2 giữ mọi *phép biến đổi* trên dataframe. Tôi chịu trách nhiệm cho toàn bộ artifact ở `data/clean/`, `data/eval/test_set.json`, và `data/results/corruption_log.json` thuộc trách nhiệm trực tiếp của tôi.

| Module/deliverable                      | File/hàm phụ trách                                       | Input nhận vào                                                            | Output bàn giao                                                                                                                                                                                          | Trạng thái     |
| ---------------------------------------- | ---------------------------------------------------------- | -------------------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ---------------- |
| **Clean dataframe** (T3)                 | `src/ingestion/cleaning.py::build_clean_dataframe`       | `list[PaperRecord]` từ TV1 (`data/raw/crossref_records.json`), `run_date` UTC | `data/clean/papers_clean.csv` & `.json` — 24 dòng, 10 cột đúng contract PLAN §3 (`paper_id, title, summary, published, age_days, authors_joined, categories_joined, text_for_embedding, abs_url, pdf_url`), `paper_id` unique, summary length 826–2610 ký tự, `age_days` 5–175 | Hoàn thành |
| **Test set** (T4)                        | `src/evaluation/testset.py::build_test_set`               | Clean dataframe                                                            | `data/eval/test_set.json` — 73 câu (24 summary + 24 authors + 24 date + 1 retrieval), mọi `ground_truth_doc_ids` resolve về row thật (0 dangling)                                                            | Hoàn thành |
| **Controlled corruption** (T9)           | `src/ingestion/corruption.py::corrupt_clean_dataframe`    | Clean dataframe (TV4 truyền `.copy(deep=True)`)                            | `data/clean/papers_clean_corrupted.csv` (22 dòng / 19 unique id) + `data/results/corruption_log.json` ghi 6 event trước/sau + `corrupted_records`                                                          | Hoàn thành |
| **Review/đối chiếu repair** (T10)        | Hỗ trợ TV1 trong `pipelines/corruption_flow.py`           | `data/raw/crossref_records.json` (bất biến)                                 | `data/clean/papers_clean_repaired.csv` (24 dòng, sinh lại từ raw)                                                                                                                                       | Hoàn thành (chủ trì TV1, tôi review/đối chiếu) |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động                                                                                                            | Thành viên/module được hỗ trợ                         | Kết quả                                                                                                                                                                                                                                                                                                                                  |
| ----------------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| **Phát hiện + báo bug `tz-aware` vs `tz-naive`** trong `_parse_published`                                               | TV1 + cả nhóm                                        | Lần chạy đầu của `build_clean_dataframe` cho ra `age_days = 10000` ở 24/24 dòng vì `datetime.now(UTC)` (aware) trừ `datetime.fromisoformat("2026-06-15")` (naive) raise `TypeError`. Sửa bằng cách sync `tzinfo` trước khi subtract; verify lại cho `age_days` 5–175.                                                                       |
| **Đề xuất đổi phrasing câu `authors`** từ `"Who are the authors"` → `"Who authored"`                                  | TV4 (`retrieval/qa.py::_extract_answer`)              | Khi sinh test set trên raw thật, tôi thấy `qa.py::_extract_answer` chỉ nhận mẫu `"who authored"` / `"list the authors"`. Giữ phrasing gốc sẽ làm 24/24 câu rơi vào nhánh mặc định (trả summary thay vì authors). Đã đổi trong `testset.py` kèm comment khóa; TV4 đổi tương ứng. Sau fix: `judge_accuracy` 0.589 → 0.918, `token_f1` 0.619 → 0.921.   |
| **Báo bug `NaN` literal** trong JSON artifact (commit `99b87d0`)                                                       | TV4 (`pipelines/corruption_flow.py`)                  | Khi xem `data/clean/papers_clean_corrupted.json` phát hiện 36 vị trí có token `NaN` trần (RFC 8259 không cho phép); CSV/JSON đều không phân biệt `""` với missing. TV4 fix hai lớp: (a) `sanitize_missing()` ở tầng điều phối chuẩn hoá `NaN → ""`; (b) helper `_records_for_json()` dùng `df.to_json()` (NaN → null). Trong code của tôi, `_corrupt_blank_summary` đổi sang lưu 1 space `" "` thay vì `""` để corruption vẫn nhìn thấy được trong CSV. |
| **Góp ý giữ `qa.py` định danh nháy đơn cố ý**                                                                       | TV4, cả nhóm                                          | PLAN ghi nhận `qa.py` tra cứu title bằng regex nháy đơn `r"'([^']+)'"`; đổi sang nháy đơn sẽ cho `lookup()` trả đúng tài liệu và bỏ qua embedding — che mất tín hiệu đo của bài lab. Quyết định: giữ nháy đơn, chấp nhận 6 câu fail cố ý.                                                                                                  |
| **Đề xuất bỏ câu hỏi `categories`**                                                                                    | Cả nhóm (TV3)                                         | Crossref không trả `subject` cho 24/24 DOI set này → `categories_joined` rỗng toàn bộ. Nếu giữ câu hỏi `categories` thì `ground_truth` rỗng và metric bị kéo giả tạo. PLAN §4.1 đã ghi nhận; T4 bỏ loại câu này, chỉ giữ summary / authors / date. Quality check TV3 đánh dấu `categories_are_optional: true`.                                  |
| **Góp ý `_records_for_json` helper** dùng `df.to_json()`                                                              | TV4                                                   | Khi viết `_records_for_json()` trong `corruption.py`, tôi dùng `json.loads(df.to_json(orient="records"))` để log corruption strict-valid. TV4 lấy pattern này áp dụng rộng hơn ở tầng pipeline.                                                                                                                                          |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện                                            | File/hàm/artifact liên quan                                                    | Kết quả bàn giao                                                                                                          | Cách xác minh                                                                                                                                                                  |
| ------------------------------------------------------------------- | -------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Biến 24 raw records thành clean dataframe 10 cột                  | `src/ingestion/cleaning.py` + `data/clean/papers_clean.{csv,json}`              | 24 rows, `paper_id` unique, summary length 826–2610, `age_days` 5–175                                                     | `data/quality/quality_baseline.json` → `overall_pass: true`, 7/7 check pass. Đọc CSV: 24 dòng (không tính header), tất cả `paper_id` unique.                                    |
| Sinh evaluation set 73 câu hỏi                                     | `src/evaluation/testset.py` + `data/eval/test_set.json`                          | 73 câu: 24 summary + 24 authors + 24 date + 1 retrieval; 0 dangling doc ids                                                | `Counter(question_type)` trên file JSON cho đúng tỷ lệ trên. Check từng `ground_truth_doc_ids` ∈ `clean.paper_id` set — 0 vi phạm.                                                  |
| Tạo 6 loại corruption + log trước/sau                              | `src/ingestion/corruption.py` + `data/results/corruption_log.json` + `data/clean/papers_clean_corrupted.csv` | 22 dòng / 19 unique id (drop 5 + duplicate 3), 6 events trong log                                                          | Đếm `affected_paper_ids` mỗi event: drop_latest=5, blank_summary=3, noise_summary=4, truncate_title=19, stale_published_date=19, duplicate_rows=3. CSV: 22 dòng, 19 unique id.    |
| Review/đối chiếu repair từ raw                                     | TV1 trong `pipelines/corruption_flow.py`                                         | `data/clean/papers_clean_repaired.csv` — 24 dòng, `paper_id` unique                                                       | So với `papers_clean.csv`: tất cả cột khớp trừ `text_for_embedding` (24 dòng khác vì rebuilt từ chunk hiện tại nhưng title/summary đã giống baseline). Quality: 7/7 pass.           |

**Output cụ thể giúp xác minh cả nhóm:** `data/results/corruption_log.json` ghi rõ "loại lỗi nào tác động record nào, trước/sau ra sao". Ví dụ event `stale_published_date` với `before=["2026-08-01", ...]` → `after=["2021-07-02", ...]` đúng 5 năm lùi theo `DEFAULT_STALE_YEARS_BACK=5`. Reviewer muốn biết "tại sao retrieval tụt 0.260?" có thể cross-check `affected_paper_ids` của `drop_latest` (5 record freshest) với `baseline_answers.json` để thấy câu nào trỏ vào record bị drop.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải giải

Khối DATA phải biến raw records (đã parse sẵn từ TV1) thành artifact có thật trên đĩa để 3 khối còn lại (TRUY TÌM, TỔNG HỢP) dùng được: (a) clean dataframe đủ 10 cột theo contract PLAN §3, (b) test set cố định có `ground_truth_doc_ids` trỏ đúng vào clean data, (c) bộ corrupted có kiểm soát để chứng minh pipeline nhạy với data xấu. Quan trọng nhất: mọi bước phải truy vết được từ raw — repair là "chạy lại từ đầu", không phải "chữa cháy".

### Cách triển khai

**`build_clean_dataframe` (T3).** Vòng for trên từng `PaperRecord`. Mỗi record được:

1. Chuẩn hoá `paper_id` về lowercase, strip markup trên `title`/`summary` (regex `r"<[^>]+>"` qua `_clean_text`).
2. Drop record nếu thiếu `paper_id` hoặc `title` (không embed được nếu thiếu 2 field này).
3. Parse `published` qua `datetime.fromisoformat(value[:10])` — chỉ lấy 10 ký tự đầu để bỏ phần time/timezone của Crossref; fallback thử `%Y-%m-%d`, `%Y/%m/%d`, `%Y-%m`.
4. Tính `age_days = max((run_date - parsed).days, 0)` — **đồng bộ tzinfo trước khi subtract** (xem mục 6). Sentinel `_MISSING_DATE_AGE_DAYS = 10_000` khi không parse được, giữ freshness report tất định.
5. Bỏ phần tử rỗng trong `authors`/`categories`, join còn lại bằng `", "`.
6. Build `text_for_embedding` theo thứ tự `Title → Summary → Authors → Categories` (title là signal mạnh nhất cho MiniLM, comment đã ghi rõ).
7. Sau khi có DataFrame: `drop_duplicates(subset=['paper_id'], keep='first')` → drop rows có `text_for_embedding` rỗng → sort theo `age_days, paper_id` asc để freshest-first, deterministic.

**`build_test_set` (T4).** Với từng row trong clean df, sinh tối đa 3 loại câu hỏi (đã bỏ `categories`):

- `summary`: "What is the summary of the paper titled X?" → `ground_truth` = `first_sentence(summary)`.
- `authors`: "Who authored the paper titled X?" → `ground_truth` = `authors_joined`. **Phải** bắt đầu bằng `"Who authored"` để khớp matcher trong `retrieval/qa.py::_extract_answer` — comment khóa tại chỗ.
- `date`: "When was the paper titled X published?" → `ground_truth` = `published` (ISO date).
- `retrieval` (fallback): dùng 1 paper bất kỳ có `text_for_embedding` không rỗng làm anchor cho semantic search.

Sau khi build xong, **integrity check**: mọi `ground_truth_doc_ids` phải tồn tại trong `paper_id` của clean df, nếu không `RuntimeError` ngay — đảm bảo evaluator không bao giờ dereference doc không tồn tại.

**`corrupt_clean_dataframe` (T9).** 6 bước tuần tự theo PLAN §5 CP4, mỗi bước ghi 1 event vào log trước khi mutate:

1. `drop_latest` (fraction=0.20) — sort theo `age_days, paper_id`, drop N rows freshest nhất. Default 24×0.20=4.8 → round 5. Giữ ≥1 row cho eval.
2. `blank_summary` (fraction=0.15) — chọn ngẫu nhiên, set summary = `" "` (1 space). Lý do: pandas `to_csv` không phân biệt `""` với NaN (đều round-trip về NaN) → lưu 1 space để lỗi vẫn nhìn thấy được trong CSV; log vẫn ghi before/after dưới dạng `""` để audit trung thực.
3. `noise_summary` (fraction=0.20) — chọn ngẫu nhiên, nối `" corruptnoise {randint(1000-9999)}"` vào summary.
4. `truncate_title` (chars=40) — cắt mọi title còn 40 ký tự.
5. `stale_published_date` (years_back=5) — shift `published` đi `5×365` ngày, cộng `age_days` tương ứng.
6. `duplicate_rows` (fraction=0.15) — chọn rows, concat bản sao vào cuối df.

Cuối cùng `_rebuild_text_for_embedding` chạy lại từ title/summary/authors/categories hiện tại — đảm bảo Chroma embed thấy signal đã corrupt, không phải bản gốc. RNG được seed cứng `20260806` nên rerun reproduce byte-for-byte.

### Input, output và contract

| Thành phần              | Mô tả                                                                                                                                                       |
| ------------------------ | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Input (T3)              | `list[PaperRecord]` từ `data/raw/crossref_records.json` + `run_date: datetime` (UTC)                                                                      |
| Input (T4)              | `pd.DataFrame` clean từ T3                                                                                                                                |
| Input (T9)              | `pd.DataFrame` clean (TV4 đã `copy(deep=True)` trước khi truyền vào; `corrupt_clean_dataframe` cũng `df.copy(deep=True)` bên trong — input không bao giờ bị mutate) |
| Output (T3)             | `pd.DataFrame` 10 cột tất định, sort by `age_days, paper_id` asc                                                                                          |
| Output (T4)             | `list[dict]` các câu hỏi, ghi `data/eval/test_set.json`                                                                                                   |
| Output (T9)             | `pd.DataFrame` corrupted (22 rows / 19 unique id) + `corruption_log.json` (6 events + before/after + `corrupted_records` strict-valid JSON)                 |
| Module phụ thuộc        | TV1 — `src/ingestion/crossref.py::PaperRecord`, `load_raw_records`                                                                                       |
| Module sử dụng output   | TV4 — `retrieval/index.py::LocalEmbeddingIndex.build`, `evaluation/metrics.py::evaluate_pipeline` (đọc clean df + test set); TV3 — `observability/quality.py` |
| Điều kiện lỗi          | Raw records rỗng / paper_id trống / title rỗng → skip row có log; published không parse được → sentinel `age_days = 10_000`                                |

### Cách xác minh

```bash
# T3: chạy cleaning trên raw thật
uv run python -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
from datetime import UTC, datetime
from core.config import load_settings
from ingestion.crossref import load_raw_records
from ingestion.cleaning import build_clean_dataframe
s = load_settings(Path('.').resolve())
records = load_raw_records(s.paths.raw_records_json)
df = build_clean_dataframe(records, datetime.now(UTC))
print(len(df), df['paper_id'].is_unique, df['age_days'].min(), df['age_days'].max())
"

# T4: build test set
uv run python -c "
import sys; sys.path.insert(0, 'src')
import pandas as pd
from evaluation.testset import build_test_set
df = pd.read_csv('data/clean/papers_clean.csv')
q = build_test_set(df, 'data/eval/test_set.json')
print(len(q))
"

# T9: corruption + verify log
uv run python -c "
import sys; sys.path.insert(0, 'src')
from pathlib import Path
import pandas as pd
from ingestion.corruption import corrupt_clean_dataframe
df = pd.read_csv('data/clean/papers_clean.csv')
c = corrupt_clean_dataframe(df.copy(deep=True), Path('data/results/corruption_log.json'))
print(len(c), c['paper_id'].nunique())
"
```

- **Kết quả mong đợi:** T3 → `24 True 5 175`; T4 → `73`; T9 → `22 19`.
- **Kết quả thực tế:** Khớp đúng.
- **Artifact/log:** `data/clean/papers_clean.{csv,json}`, `data/eval/test_set.json`, `data/results/corruption_log.json`, `data/clean/papers_clean_corrupted.csv`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** `build_test_set` đầu tiên sinh 4 loại câu hỏi (summary, authors, date, **categories**). Khi chạy trên raw thật từ TV1, phát hiện `categories_joined` rỗng ở 24/24 records — Crossref không trả trường `subject` cho DOI set này. Nếu giữ câu hỏi `categories`, `ground_truth` sẽ rỗng và `retrieval_hit_rate` sẽ giảm giả tạo.
- **Các phương án đã cân nhắc:**
  1. Giữ 4 loại câu hỏi, chấp nhận metric bị kéo xuống bởi missing ground truth.
  2. Bỏ loại `categories`, giữ 3 loại + retrieval fallback.
  3. Tự suy ra categories từ title (LLM classify) — sai nguyên tắc "không bịa dữ liệu" và phá contract `ground_truth` lấy từ clean row.
- **Phương án đã chọn:** (2) Bỏ `categories` question.
- **Lý do:** PLAN §4.1 đã chốt giới hạn này (Crossref không trả `subject`). Metric phải phản ánh chất lượng data thật, không phải bug của câu hỏi. Phương án (3) vi phạm contract "ground truth lấy từ `paper_id` clean, không tự bịa ID".
- **Bằng chứng quyết định phù hợp:** Test set cuối có 73 questions (24+24+24+1), `baseline_metrics.json` cho `retrieval_hit_rate=1.0, mean_token_f1=0.921, judge_accuracy=0.918, mean_judge_score=4.6712`. Quality check đánh dấu `categories_are_optional: true` để không fail oan trên baseline sạch. So với trước fix (`judge_accuracy=0.589`), số đã tăng rõ rệt.

## 6. Một lỗi hoặc blocker đã xử lý

### Bug 1 — `age_days` toàn `10000` (sentinel) ở 24/24 rows

- **Triệu chứng:** Sau khi chạy `build_clean_dataframe` lần đầu, `df['age_days'].min() == df['age_days'].max() == 10000` — freshness signal vô hiệu hoàn toàn, `latest_published` trong freshness_report không khớp với raw.
- **Lệnh tái hiện:** Xem snippet verify ở mục 4.
- **Nguyên nhân gốc:** `run_date = datetime.now(UTC)` là tz-aware; `parsed = datetime.fromisoformat("2026-06-15")` là tz-naive. Phép `aware - naive` raise `TypeError`, function rơi vào nhánh `return "", _MISSING_DATE_AGE_DAYS` (10_000). Toàn bộ 24 rows đều vô hiệu.
- **Cách xử lý:** Trước khi subtract, đồng bộ tzinfo (cover cả 2 hướng):
  ```python
  if parsed.tzinfo is not None and run_date.tzinfo is None:
      parsed = parsed.replace(tzinfo=None)
  elif parsed.tzinfo is None and run_date.tzinfo is not None:
      parsed = parsed.replace(tzinfo=run_date.tzinfo)
  ```
- **Cách xác minh sau khi sửa:** `df['age_days'].min()` = 5, `max` = 175, range 170 ngày — đúng với khoảng cách từ raw date đến `now`.
- **Bài học:** Khi `datetime` đi qua nhiều layer (env, API, file), `tzinfo` có thể bị strip lúc nào không hay. Luôn normalize tz trước khi làm arithmetic.

### Bug 2 — NaN literal trong JSON artifact (báo TV4, fix ở commit `99b87d0`)

- **Triệu chứng:** `data/clean/papers_clean_corrupted.json` chứa token `NaN` trần (không phải `null`). VS Code JSON parser báo đỏ "Value expected" tại 36 vị trí — JSON spec (RFC 8259) không cho phép literal `NaN`.
- **Nguyên nhân gốc:** `pd.read_csv` biến ô trống (`categories_joined`, `pdf_url`) thành `NaN` float; `df.to_dict(orient="records")` rồi `json.dumps` in ra `NaN`. Baseline không dính vì đi thẳng từ bộ nhớ. Rủi ro kèm theo: `first_sentence(NaN)` **crash `TypeError`** nếu ai chạy lại từ file CSV corrupted.
- **Cách xử lý (TV4 đã làm, tôi báo bug):** Hai lớp bảo vệ độc lập:
  1. `sanitize_missing()` ở tầng điều phối (`pipelines/`) chuẩn hoá `NaN → ""` trước khi lưu và trước khi index.
  2. Helper `_records_for_json()` trong `corruption.py` (tôi viết) dùng `df.to_json()` để `NaN → null`.
  Phát hiện thêm: `to_csv` không phân biệt được `""` với NaN, nên `_corrupt_blank_summary` lưu `" "` (1 space) thay vì `""` để lỗi vẫn nhìn thấy được trong CSV. Log vẫn ghi `""` làm before/after để audit trung thực.
- **Cách xác minh:** Parse toàn bộ `data/**/*.json` bằng parser nghiêm ngặt (`parse_constant` ném lỗi) — không file nào lỗi.
- **Bài học:** CSV/JSON đều không phân biệt `""` (chuỗi rỗng) và missing — cần sentinel rõ ràng (whitespace) cho mọi giá trị "trống có chủ đích".

### Bug 3 — 24/24 câu hỏi `authors` fail hệ thống (TV4 fix, tôi đề xuất)

- **Triệu chứng:** loại `authors` có `token_f1 = 0.000` và judge score = 1.0 ở **cả 24 câu**, kéo `judge_accuracy` toàn cục xuống 0.589.
- **Nguyên nhân:** Test set ban đầu đặt câu hỏi dạng `"Who are the authors of the paper titled ..."`, nhưng `src/retrieval/qa.py::_extract_answer` chỉ nhận diện `"who authored"` hoặc `"list the authors"`. Không khớp mẫu nào, câu hỏi rơi vào nhánh mặc định và trả về `first_sentence(summary)` — tức là trả tóm tắt cho câu hỏi về tác giả.
- **Cách xử lý:** Đổi mẫu câu trong `src/evaluation/testset.py` thành `"Who authored the paper titled ..."`, kèm comment giải thích tại chỗ để không ai đổi ngược lại. Sinh lại test set một lần duy nhất rồi khóa file. TV4 đổi tương ứng ở phía QA nếu cần.
- **Cách xác minh:** `mean_token_f1` 0.619 → **0.921** và `judge_accuracy` 0.589 → **0.918**. Dùng `token_f1` làm bằng chứng vì nó tất định, không phụ thuộc LLM judge.
- **Bài học:** Khi 2 module contract với nhau bằng regex/string (test set ↔ QA prompt), phải đối chiếu bằng test set UPPER/lower-case, có comment chặn ở cả 2 đầu. Đây là dạng integration bug khó bắt vì unit test từng phần đều pass.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref đến vector index như thế nào?** TV1 fetch Crossref REST API → lưu `data/raw/crossref_response.json` (raw nguyên vẹn, ghi TRƯỚC khi parse theo PLAN §5 CP1) → parse thành `PaperRecord` dataclass → ghi `data/raw/crossref_records.json`. Từ đó tôi (`build_clean_dataframe`) chuyển thành `papers_clean.csv` 10 cột theo contract, đồng thời build `text_for_embedding`. TV4 (`LocalEmbeddingIndex.build`) embed bằng MiniLM-L6-v2 rồi nạp vào ChromaDB collection `papers-baseline` (mỗi trạng thái có collection riêng để tránh ghi đè — vì `LocalEmbeddingIndex.build` xoá collection trùng tên rồi tạo lại).

2. **Evaluation set và ground-truth doc IDs dùng để đo retrieval/answer quality ra sao?** `test_set.json` chứa 73 câu hỏi, mỗi câu có `ground_truth_doc_ids: [paper_id]` trỏ thẳng vào paper thật trong clean data. Khi `evaluate_pipeline` chạy, nó gọi agent trả lời từng câu, lấy `retrieved_doc_ids` (top_k=4) từ Chroma, so sánh với `ground_truth_doc_ids` để tính `retrieval_hit_rate` (có hit không, dùng `set` intersection). Token F1 đo overlap giữa `ground_truth` (text) và `answer` của agent. Judge metric dùng LLM (`deepseek-v4-pro` qua proxy `api.ai-box.vn`) chấm 1–5 cho mỗi câu trả lời.

3. **Quality checks khác freshness monitoring ở điểm nào?** Quality checks là **static schema checks** — row count, `paper_id` unique, `summary_length`, `title_not_blank`, `paper_id_not_null`, `required_columns` — tức là "data có đúng dạng không". Freshness là **time-aware signal** — `age_days` so với `threshold_days=180`, đếm `is_fresh` / `stale_rows` — tức là "data có còn cập nhật không". Một clean dataset có thể pass hết quality check nhưng 100% stale. Ví dụ trong corrupted state: `summary_length` fail (3 blank), `paper_id_unique` fail (3 dup), `freshness` fail (22 stale) — độc lập nhau, mỗi check bắt một dạng lỗi khác nhau.

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?** Vì test set là "thước đo cố định". Nếu đổi test set giữa 3 lần evaluate, delta sẽ bị nhiễu bởi sự khác biệt của câu hỏi chứ không phải bởi chất lượng data. Mục tiêu corruption/repair là chứng minh "cùng một bộ câu hỏi, khi corpus xấu thì metric giảm, khi corpus được repair thì metric phục hồi" — đó mới là bằng chứng data ảnh hưởng đến RAG quality. PLAN §6 cấm refresh Crossref hoặc test set giữa 3 lần evaluate (`REFRESH_SOURCE`, `REFRESH_TEST_SET` env vars luôn off, file `test_set.json` đã khóa từ CP3).

5. **Repair được xem là thành công dựa trên artifact và metric nào?** Repair chạy lại `build_clean_dataframe` từ `data/raw/crossref_records.json` (raw bất biến) → sinh `papers_clean_repaired.csv` cùng schema baseline. Bốn bằng chứng: (a) `repaired.paper_id ⊆ raw.paper_id` → `True`, (b) `repaired == baseline` trên 9/10 cột (chỉ `text_for_embedding` khác do rebuilt từ chunk — không phải lỗi), (c) 5 `paper_id` mất khi corrupt đều lấy lại được → 24/24, (d) raw snapshot không đổi trước/sau corruption. Bốn bằng chứng này giải quyết 2 câu hỏi: "repair có lấy lại được dữ liệu?" (a, c) và "cleaning có tất định không?" (b, d). Về metric: cả 4 chỉ số trong `repaired_metrics.json` khớp tuyệt đối với baseline (`retrieval_hit_rate=1.0, mean_token_f1=0.9206, judge_accuracy=0.9178, mean_judge_score=4.6712`).

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal                | Baseline | Corrupted | Repaired | Nhận xét của cá nhân                                                                                                                                                            |
| ---------------------------- | -------: | --------: | -------: | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `retrieval_hit_rate`         |      1.0 |    0.7397 |      1.0 | Baseline 1.0 là trần — corpus 24 papers + `top_k=4` nên gần như luôn trúng ground truth. Corrupted 0.74 = −0.26: drop_latest mất 5 câu trỏ vào paper freshest + duplicate đẩy doc đúng ra khỏi top-4. Phục hồi 100% về 1.0. |
| `mean_token_f1`              |  0.9206 |    0.2620 |  0.9206 | Metric tất định (không qua LLM). Corrupted tụt mạnh nhất = −0.66 vì QA extractive trả nguyên văn corrupted summary (rỗng hoặc có token `corruptnoise`). Phục hồi 100%. |
| `judge_accuracy`             |  0.9178 |    0.2740 |  0.9178 | 67/73 → 20/73 câu đúng. Tụt −0.64. Phục hồi 100%.                                                                                                                                |
| `mean_judge_score`           |  4.6712 |    2.0959 |  4.6712 | Trên thang 1–5. Corrupted 2.10 = thường chỉ đạt 1-2/5. Phục hồi 100%.                                                                                                              |
| Quality checks `overall_pass` |  `true`  |  `false`  |  `true`  | Corrupted fail 3 checks: `paper_id_unique` (3 dup), `summary_length` (3 blank), `freshness` (22 stale). Repaired pass all 7.                                                            |
| Freshness status             |  `is_fresh: true` (0 stale) | `is_fresh: false` (22 stale) | `is_fresh: true` (0 stale) | Threshold = 180 ngày. Corrupted: `latest_published` 2026-08-01 → 2021-07-02 (lùi 5 năm từ `stale_published_date`). Phục hồi 100%. |

### Kết luận từ số liệu

**Hai chuỗi nguyên nhân–bằng chứng:**

1. **`blank_summary` + `duplicate_rows` → quality signal fail → retrieval và answer metric cùng tụt.**
   Xoá nội dung 3 summary khiến `summary_length` chuyển fail (`min_chars` 826 → 1), và nhân bản 3 dòng khiến `paper_id_unique` fail. Vì `text_for_embedding` được rebuild sau khi corrupt (xem `_rebuild_text_for_embedding`), vector đem đi index thực sự bị hỏng — `retrieval_hit_rate` xuống 0.7397 (−0.2603) và `mean_token_f1` xuống 0.2620 (−0.6586). Đây là chuỗi hoàn chỉnh từ *thay đổi dữ liệu* → *tín hiệu quan sát* → *chất lượng agent*.

2. **Repair từ raw → quality và freshness phục hồi → metric phục hồi hoàn toàn.**
   Chạy lại cleaning từ `crossref_records.json` đưa dataset về 24 dòng / 24 `paper_id` duy nhất, `overall_pass` về `true`, `is_fresh` về `true` với 0 dòng stale. Cả bốn metric trở về đúng giá trị baseline — khớp tuyệt đối, không phải xấp xỉ. Sự phục hồi 100% chứng minh cleaning là tất định (chạy lại cho kết quả y hệt) chứ không phải nhóm đang giữ backup.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**

| Loại corruption | Affected | Ảnh hưởng chính |
|---|---|---|
| `stale_published_date` (lùi 5 năm) | 19/22 | **Im lặng** — không làm retrieval/answer tụt nhưng freshness fail hoàn toàn (22/22 stale). Metric retrieval hoàn toàn không bắt được — pipeline chỉ nhìn metric sẽ báo "xanh" trong khi đang phục vụ dữ liệu cũ 5 năm. Đây chính là lý do observability tồn tại tách khỏi evaluation. |
| `truncate_title` | 19/22 | Yếu — title chỉ làm index tham khảo trong MiniLM, không phá hoàn toàn signal semantic của summary. |
| `blank_summary` | 3/22 | **Mạnh nhất lên answer** — QA extractive trả chuỗi rỗng/1-space, kéo `token_f1` xuống gần 0. |
| `noise_summary` | 4/22 | **Mạnh lên retrieval** — token `corruptnoise NNNN` xuất hiện trong summary, đẩy embedding lệch khỏi ground-truth cluster. |
| `duplicate_rows` | 3/22 | Trung bình — duplicate làm 1 doc đúng bị đẩy xuống thấp hơn (do doc khác cùng id trong top-4), không tăng hit. |
| `drop_latest` | 5/22 | Yếu trên retrieval (5/73 câu miss) nhưng mất hoàn toàn 5 ground truth. |

**Kết quả nào khác với kỳ vọng ban đầu?**

- Ban đầu tôi kỳ vọng `categories_joined` không phải toàn rỗng — Crossref có thể trả `subject` cho một số DOI. Hoá ra 0/24. Đây là giới hạn nguồn, không phải bug, nên T4 bỏ luôn `categories` question và TV3 đánh dấu `categories_are_optional: true` ở quality check.
- Baseline `retrieval_hit_rate` = 1.0 là điều tôi lo ngại — nhỏ corpus và top_k=4 cho trần quá cao, khó thấy chất lượng retrieval tinh tế. Thực tế vẫn nhạy với corruption (xuống 0.74), đủ để đo.
- `mean_token_f1` phân bố cực kỳ nhị cực (baseline 0.92 là trung bình của 67 câu F1≈1.0 và 6 câu F1≈0.0 hệ thống) — không phân biệt được "đúng một phần". Đây là hệ quả của QA extractive + test set có ground truth đúng-dạng.
- Repair CSV khác baseline CSV đúng **1 cột**: `text_for_embedding` rebuilt từ chunk hiện tại (có thể khác thứ tự join hoặc whitespace) — tôi xác minh 9/10 cột khớp tuyệt đối, 1 cột còn lại là tái dựng deterministic từ các cột kia. Không phải bug, chỉ là artifact của việc "rebuild sau khi cleaning" để tránh stale embed text.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. **Về data pipeline:** Schema contract phải chốt trước khi code. PLAN §3 đã khóa 10 cột clean trong CP0 và cả team không ai đề xuất đổi → mọi handoff (T4, T6, T9) đều chạy mượt. Ngược lại, **regex/string contract giữa 2 module** (test set phrasing ↔ QA prompt) lại bị bug vì chốt muộn — đây là dạng integration bug mà unit test từng phần đều pass. Bài học: contract kiểu "phrasal" cần test tích hợp từ CP2, không đợi đến lúc evaluate.

2. **Về data quality/observability:** Một cột rỗng 24/24 (`categories_joined`) không phải lỗi mà là tín hiệu — nguồn dữ liệu này không có signal này. Quality checks phải **phân biệt** "missing có chủ đích" (giới hạn nguồn) với "missing do bug" (mất record). Trong corrupted state, `summary_length` fail là do **bug** (chủ đích corruption), còn `categories_joined` rỗng là do **giới hạn nguồn** — cùng một triệu chứng nhưng hành xử khác nhau trong báo cáo. Flag `categories_are_optional: true` trong quality check là cách TV3 đã làm đúng.

3. **Về ảnh hưởng data đến RAG agent:** `text_for_embedding` mới là điểm chạm thực sự giữa data và agent. Title, summary, authors, categories đều đi qua nó. Mọi corruption làm hỏng một cột nguồn sẽ lan vào embedding — **bắt buộc** rebuild `text_for_embedding` sau khi mutate. Nếu không, Chroma embed trên signal gốc và corruption "không hiệu lực". Các chỉ số retrieval/answer không đổi, tạo ảo giác "data hỏng mà không ai biết".

### Nếu có thêm thời gian

Thêm **categorical noise** như `swap_authors` — đảo `authors_joined` giữa 2 paper — để test xem agent có bị đánh lừa bởi ground truth ở doc khác không. Lý do: hiện tại các câu hỏi `authors` chỉ kiểm tra retrieval đúng paper, chưa kiểm tra agent có thực sự đọc đúng author từ content hay chỉ relay retrieval. Implementation: 2 dòng trong `corrupt_clean_dataframe` (chọn 2 paper khác id, swap `authors_joined` + rebuild `text_for_embedding`), không quá 30 phút. Metric đề xuất: so `judge_accuracy` câu `authors` swap vs không swap — nếu agent chỉ dựa retrieval thì cả hai đều "đúng" (cùng doc); nếu agent paraphrase đúng author từ content thì câu swap fail. Đây là test phân biệt "retrieval" vs "reading" trong RAG agent.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu. *(baseline 1.0/0.921/0.918/4.67, corrupted 0.74/0.26/0.27/2.10, repaired 1.0/0.921/0.918/4.67 — cross-checked với `data/results/*_metrics.json`)*
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Lưu Nguyễn Ngọc Hân
**Ngày xác nhận:** 2026-08-06
