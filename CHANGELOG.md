# Changelog

Nhật ký buổi làm K4 chiều 06/08/2026. Ghi theo **task** trong [PLAN_K4_CHIEU_2026-08-06.md](PLAN_K4_CHIEU_2026-08-06.md) mục 4.

**Quy ước ghi:** thêm một mục mỗi khi (a) một task chuyển trạng thái, hoặc (b) pull về có thay đổi từ thành viên khác. Mỗi mục ghi: giờ, task, ai, **bằng chứng xác minh** (số liệu hoặc lệnh đã chạy), không chỉ ghi "đã xong".

Ký hiệu: ✅ xong & đã xác minh · 🟡 code xong, chờ blocker · ⬜ chưa bắt đầu · 📥 pull về từ người khác · 📄 tài liệu

---

## Trạng thái hiện tại

| Task | Owner | Trạng thái | CP |
| --- | --- | --- | --- |
| T0 Setup env | Cả nhóm | ✅ trên máy TV4 (3 máy còn lại tự làm) | CP0 |
| T1 Contract | Cả nhóm | ✅ chốt trong plan mục 3 | CP0 |
| T2 Raw ingestion | TV1 Tường | ✅ merged `main` (PR #1) | CP1 |
| T3 Clean dataframe | TV2 Hân | ✅ 24 rows, đủ 10 cột | CP2 |
| T4 Test set | TV2 Hân | ✅ 73 samples | CP2 |
| T5 Quality + freshness | TV3 Sáng | ✅ 7 check pass, `is_fresh` true | CP2 |
| T6 Index + eval wiring | TV4 Quang | ✅ chạy thật, hit_rate=1.000 | CP2 |
| T7 Baseline pipeline | TV4 Quang | ✅ **chạy hết 7/7 bước** | CP3 |
| T8 Baseline report | TV3 Sáng | ✅ `phase1_report.md` khớp JSON | CP3 |
| T9 Corruption + log | TV2 Hân | ✅ 6 loại lỗi, 24→22 rows | CP4 |
| T10 Repair từ raw | **TV1** (đổi từ TV2+TV1) | ✅ repaired == baseline chính xác | CP4 |
| T11 Corruption flow | TV4 Quang | ✅ **chạy hết 5/5 bước** | CP5 |
| T12 Comparison report | TV3 Sáng | ✅ `corruption_report.md` đã sinh | CP5 |
| T13 Group + báo cáo cá nhân | TV4 chủ trì | ⬜ (4 file cá nhân đã tạo khung) | CP6 |
| T14 Review + demo | Cả nhóm | ⬜ | CP6 |

## ✅ PHA 1 + PHA 2 XONG — cả hai entrypoint chạy end-to-end

| Metric | Baseline | Corrupted | Repaired |
| --- | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | **0.740** | 1.000 |
| `mean_token_f1` | 0.921 | **0.269** | 0.921 |
| `judge_accuracy` | 0.918 | **0.260** | 0.918 |
| `mean_judge_score` | 4.671 | **2.041** | 4.671 |

`repaired == baseline` chính xác đến từng chữ số. Judge thật cả 3 bộ (fallback 0/73).

**Còn lại: T13 group report (TV4 chủ trì) + T14 review & demo (cả nhóm).**

🔒 **Test set đã KHÓA** từ đây — `data/eval/test_set.json` không được sinh lại nữa, nếu không 3 trạng thái mất khả năng so sánh.

---

## Nhật ký

### `14:21` — 📄 Kế hoạch buổi + 4 báo cáo cá nhân · TV4 · `4cff058`

- Tạo `PLAN_K4_CHIEU_2026-08-06.md`: chia vai trò theo 3 khối (DATA / TRUY TÌM / TỔNG HỢP), contract dùng chung, bảng 15 task với quan hệ chặn, timeline CP0–CP6, checklist, Definition of Done.
- Tạo 4 file `report/<MSSV>_HoTen.md`.
- **Đổi vai trò:** chủ trì tổng hợp `group_report.md` (T13) chuyển từ TV3 Sáng sang TV4 Quang. TV3 vẫn giữ T5, T8, T12.

### `14:49` — 📄 Lý thuyết + sơ đồ pipeline · TV4 · `5a3ed3f`

- Tạo `THEORY.md` (10 mục): vì sao cần RAG, vòng đời dữ liệu, schema, embedding/vector store, 4 metric, quality vs freshness, bảng 6 loại corruption → tín hiệu dự kiến, repair, cạm bẫy, 11 câu hỏi tự kiểm.
- Ghi rõ **bẫy fallback judge** (`metrics.py:61-70`): khi LLM lỗi, `judge_accuracy` tụt về heuristic token F1 — hai cột số trông độc lập nhưng cùng một nguồn.
- Thêm mục 1.1 vào plan: 2 sơ đồ Mermaid (luồng dữ liệu + owner; 3 trạng thái so sánh).

### `15:00` — 📥 Pull: `.gitignore` · TV3 Sáng · `b22bb82`

- Thêm 4 dòng vào `.gitignore`. Không đụng file của ai. Local rebase lên trên.

### `15:32` — ✅ **T7 + T11** hai entrypoint pipeline · TV4 · `c91c3cf`

- `src/pipelines/phase1.py`: 7 bước có in progress từng bước — load/fetch raw → clean → save → index → test set → evaluate → quality/freshness → report → agent demo.
- `src/pipelines/corruption_flow.py`: 5 bước — chặn sớm nếu thiếu artifact baseline → corrupt → eval → repair từ raw → eval → comparison report.
- Quyết định thiết kế:
  - `load_or_fetch_records` / `load_or_build_test_set` chỉ gọi API / sinh test set khi thiếu file hoặc bật `REFRESH_*` → giữ 3 trạng thái so sánh được.
  - `require_baseline_artifacts()` fail sớm với thông báo tiếng Việt thay vì crash giữa chừng.
  - `freshness_path_for()` tạo freshness riêng mỗi trạng thái tại `quality_dir/freshness_report_{state}.json` (vì `Paths` chỉ có 1 path baseline).
  - Repair gọi `load_raw_records` + `build_clean_dataframe`, không đụng clean baseline.
  - Agent demo bọc try/except — LLM lỗi không làm hỏng pipeline.
- **Xác minh:** `import pipelines.phase1, pipelines.corruption_flow` → OK; `run_phase1.py` dừng đúng ở `crossref.py:46` (TODO của TV1) ⇒ wiring đúng.
- Thêm cột **CP (giờ)** vào bảng công việc + bảng mốc chốt cứng 6 checkpoint kèm quy tắc cắt phạm vi khi trễ.

### `15:32` — ✅ 📥 **T2 Raw ingestion** · TV1 Tường · `b88f5ed` (PR #1 → `c9e2bed`)

Pull về từ nhánh `feat/data-source`. Kiểm theo tiêu chí "Xong khi" trong plan:

| Tiêu chí | Kết quả |
| --- | --- |
| `data/raw/*.json` đọc lại được qua `load_raw_records` | ✅ 24 records |
| `paper_id` không rỗng, không trùng | ✅ 0 rỗng / 0 trùng |
| title, summary, authors, `abs_url` | ✅ đủ 24/24 |
| `published` nằm trong 180 ngày | ✅ 2026-02-12 → 2026-08-01 |

- Tường làm thêm `tests/test_crossref.py` (112 dòng) — ngoài yêu cầu, tính vào bonus rubric "test hoặc validation bổ sung".
- **Phát hiện ảnh hưởng T3 + T4:** `categories` **rỗng ở 24/24 record** — Crossref không trả `subject` cho các DOI này. Chốt cách xử lý:
  1. Quality check (T5) **không được** đặt điều kiện fail trên `categories_joined`, nếu không baseline sạch cũng fail và hỏng phép so sánh.
  2. `build_test_set` (T4) bỏ loại câu hỏi `categories`, chỉ dùng summary / authors / date.
  3. Ghi lý do vào `group_report.md`: giới hạn của nguồn, không phải lỗi code.
- **Blocker chuyển:** `run_phase1.py` giờ qua được `[1/7] raw records: 24` và dừng ở `cleaning.py:25` ⇒ T3 của TV2 Hân.

### `15:39` — 📄 Đánh dấu tiến độ trong plan · TV4 · `9fa73f2`

- Thêm ký hiệu ✅ / 🟡 vào cột ID bảng công việc.
- Thêm mục 4.1 "Tiến độ" với bảng trạng thái + bằng chứng + phát hiện `categories` rỗng.
- Sửa mục 2: dòng cũ ghi "chưa có `.venv`, chưa có `.env`" đã sai — nay ghi đúng trạng thái máy TV4.

### `15:57` — ✅ CLI hỏi–đáp (bonus) · TV4 · `a54c218`

- Tạo `script/ask.py`: hỏi trực tiếp trên corpus đã index.
  - `--state baseline|corrupted|repaired` — **hỏi cùng một câu trên ba trạng thái**, cho người chấm thấy tác động corruption trong 30 giây thay vì đọc JSON.
  - Tự dò câu hỏi trong `test_set.json` → in HIT/MISS + ground truth.
  - Không truyền câu hỏi → chế độ interactive.
  - Chưa có index → báo rõ phải chạy script nào, exit 1.
  - `safe()` bọc output vì console Windows là cp1252, title unicode sẽ crash.
- **Xác minh:** smoke-test trên index tổng hợp 3 tài liệu (đã xóa collection sau khi test) — trả đúng answer, score giảm dần, HIT đúng. Chưa chạy trên dữ liệu thật vì còn chờ T3.
- Nhắm vào gạch đầu dòng bonus của rubric: "có cài đặt CLI/use case để dễ reproduce".

### `16:1x` — ✅ 📥 **T3 + T4** clean dataframe + test set · TV2 Hân · `2267944`

- `cleaning.py` (+170 dòng) và `testset.py` (+132 dòng), kèm artifact `data/clean/papers_clean.csv|.json` và `data/eval/test_set.json`.
- **Xác minh:** 24 clean rows, đủ 10 cột theo contract; test set 73 samples, phân loại `summary` 24 / `authors` 24 / `date` 24 / `retrieval` 1 — đúng như đã chốt: **không có loại `categories`** vì nguồn rỗng 24/24.

### `16:1x` — ✅ **T6 chạy thật lần đầu**, baseline evaluation có số · TV4

Chạy `script/run_phase1.py`, qua **5/7 bước** rồi dừng ở T5:

```
[1/7] raw records: 24 (loaded_from_snapshot)
[2/7] clean rows: 24
[3/7] indexed collection: papers-baseline
[4/7] test set: 73 samples (loaded_existing)
[5/7] hit_rate=1.000 token_f1=0.619 judge_acc=0.589
```

Metrics baseline (`data/results/baseline_metrics.json`):

| Metric | Giá trị | Nhận xét |
| --- | --- | --- |
| `retrieval_hit_rate` | **1.000** (0/73 miss) | Retrieval hoàn hảo. Hợp lý vì corpus chỉ 24 tài liệu mà `top_k=4` — lấy 1/6 corpus mỗi lần hỏi. **Đây là điều tốt cho thí nghiệm:** có trần 1.0 thì corruption mới có chỗ để kéo xuống và đo được |
| `mean_token_f1` | 0.619 | Câu trả lời đúng ý nhưng diễn đạt khác ground truth — đúng bản chất metric lexical |
| `judge_accuracy` | 0.589 | LLM judge chấm đúng 43/73 |
| `mean_judge_score` | 3.40 / 5 | |
| Fallback judge | **0/73** | LLM judge thật đã chạy hết, không rơi vào heuristic ⇒ số liệu judge đọc được, không phải token F1 trá hình |

- Artifact sinh ra: `data/embeddings/papers_embeddings.json`, `data/results/baseline_metrics.json`, `baseline_answers.json`, collection `papers-baseline`.
- Thêm `data/chroma/` vào `.gitignore`: 1.4 MB binary sqlite, tái tạo được bằng `run_phase1.py`, và `ask.py` đã có sẵn thông báo hướng dẫn khi thiếu index.
- **Blocker chuyển:** `quality.py:21` ⇒ T5 của TV3 Sáng.

---

## Môi trường máy TV4 (chuẩn bị trước buổi)

- `.venv` Python **3.11.9** (dự án yêu cầu `>=3.11,<3.14`; `python` mặc định trên máy là 3.14.6 nên phải chỉ định 3.11).
- `.env` đã có credential provider.
- Model `all-MiniLM-L6-v2` đã cache, verify vector **384 chiều** ⇒ buổi chiều không mất vài phút chờ tải.
- Cảnh báo vô hại: HuggingFace cache không dùng symlink trên Windows, chỉ tốn thêm dung lượng đĩa.

### `16:2x` — 📄 Gom "chuẩn bị từ raw" về một người · TV4 quyết định

Điều chỉnh phân việc giữa buổi để giảm phụ thuộc chéo trong khối DATA:

- **T10 "Repair từ raw": `TV2 + TV1` → chỉ `TV1`.** Trước đây hai người cùng sở hữu một task 40 phút, phải bàn giao giữa CP4 — tốn thời gian đồng bộ hơn là tự làm.
- Khối DATA nay chia theo **hướng của dữ liệu**, không chia theo file:
  - **TV1 — đưa dữ liệu VÀO:** Crossref, raw snapshot, `load_raw_records`, và repair (repair cũng chỉ là đọc lại từ raw). Một người nắm trọn đường `data/raw/` → repaired data.
  - **TV2 — BIẾN ĐỔI dữ liệu đã có:** cleaning, test set, corruption. Một người nắm trọn các phép biến đổi trên dataframe.
- Ghi rõ trong plan: code repair **đã có sẵn** trong `corruption_flow.py` (T11). Việc của TV1 ở T10 là **xác minh lineage và giải thích**, không phải viết lại code — so `paper_id` set giữa raw / baseline / repaired để chứng minh repaired không phải bản copy của baseline.
- Cập nhật trạng thái bảng công việc: ✅ T3, T4 (TV2), ✅ T6 (TV4).

### `16:4x` — ✅ 📥 **T5 + T8** quality, freshness & baseline report · TV3 Sáng · `b7eca25`, `d0b1875`

- `quality.py` (+127) và `reporting.py` (+101), kèm `data/quality/quality_baseline.json` + `freshness_report.json`.
- **Baseline chạy hết 7/7 bước lần đầu** — `data/reports/phase1_report.md` đã sinh, mọi số khớp JSON.
- Quality baseline `overall_pass: true`, 7 check đều pass: `required_columns`, `row_count` (24), `paper_id_not_null` (0), `paper_id_unique` (0 trùng), `title_not_blank` (0), `summary_length` (826–2610 ký tự), `freshness` (0 stale).
- Sáng đã xử lý đúng vấn đề `categories`: đánh dấu `categories_are_optional: true`, **không** đặt điều kiện fail trên cột rỗng ⇒ baseline sạch không bị fail oan.
- Freshness: `latest_published` 2026-08-01, `oldest` 2026-02-12, `stale_rows` 0, `is_fresh` true.

**Sự cố khi chạy (đã xử lý):** lần chạy đầu crash ở `huggingface_hub` — `RuntimeError: Cannot send a request, as the client has been closed`. HF cố kiểm tra bản mới của model qua mạng dù đã cache. Khắc phục: chạy với `HF_HUB_OFFLINE=1`. Ghi lại vì máy khác có thể gặp lại.

**Agent demo lỗi 402 (không chặn pipeline):** OpenRouter báo hết credit (`max_tokens` 16384 > số dư 16084). `run_agent_demo` đã bọc try/except nên pipeline vẫn chạy xong; `agent_demo_answers.json` chỉ ghi lỗi. **Ảnh hưởng rubric Mục 5 (Agent, 10 điểm)** — cần nạp credit hoặc đổi provider trước demo CP6.

### `16:4x` — ✅ Tests + demo evidence (bonus) · TV4 (giao codex)

- `tests/test_pipelines.py` — 11 test cho phần TV4, không gọi LLM/mạng/model: `load_or_fetch_records` không gọi API khi đã có snapshot, `require_baseline_artifacts` báo đúng artifact thiếu, `freshness_path_for` trả 3 path khác nhau, `ask.embeddings_path_for` map đúng 3 state, `match_test_sample` không phân biệt hoa thường.
- **Xác minh:** `pytest tests/ -q` → **17 passed** (11 mới + 6 của Tường).
- `report/demo_evidence.md` — phân tích 73 mẫu thật, bảng metric theo question_type, 2 ví dụ demo cho CP6.
- Sửa `.gitignore`: dòng `data/chroma/` tôi thêm trước đó bị thiếu newline nên dính vào `CLAUDE.md` ⇒ chroma không được ignore. Đã sửa.

### `16:4x` — 🔴 **PHÁT HIỆN: 24/24 câu hỏi `authors` fail hệ thống** · cần TV2 sửa T4

Từ `demo_evidence.md`: loại câu hỏi `authors` có **token F1 = 0.000 và judge score = 1.000 ở cả 24 câu**, không câu nào correct.

**Nguyên nhân:** test set (T4) đặt câu hỏi dạng `"Who are the authors of the paper titled ..."`, nhưng `src/retrieval/qa.py::_extract_answer` (starter code, không được sửa) chỉ nhận diện:

```python
if "who authored" in lowered or "list the authors" in lowered:
    return metadata["authors_joined"]
```

Câu hỏi không khớp chuỗi nào ⇒ rơi vào nhánh mặc định `first_sentence(summary)` ⇒ trả về tóm tắt thay vì danh sách tác giả.

| | Hiện tại | Nếu sửa |
| --- | --- | --- |
| `judge_accuracy` | 43/73 = **0.589** | 67/73 = **0.918** |

**Cách sửa (thuộc T4, file `src/evaluation/testset.py` của TV2):** đổi mẫu câu thành `"Who authored the paper titled ..."`. Sửa một chuỗi.

**Phải sửa TRƯỚC khi chạy T9 corruption** — sau đó test set bị khóa cho cả 3 trạng thái, không đổi được nữa mà không phải chạy lại baseline.

### `17:0x` — ✅ Sửa mẫu câu `authors` (T4) + đổi LLM provider · TV4

**Sửa T4** (`src/evaluation/testset.py`, file của TV2 — đã sửa thay vì chờ, cần báo lại Hân): đổi `"Who are the authors of the paper titled ..."` → `"Who authored the paper titled ..."` để khớp matcher trong `retrieval/qa.py::_extract_answer`. Có comment giải thích ngay tại chỗ để không ai đổi ngược lại.

Chạy lại với `REFRESH_TEST_SET=1` để sinh lại `test_set.json`. **Đây là lần cuối được phép đổi test set** — từ đây khóa cho cả 3 trạng thái.

**Đổi LLM provider:** `openai/gpt-4o-mini` (OpenRouter) → `deepseek-v4-pro` qua proxy `https://api.ai-box.vn/v1`. Lý do: OpenRouter hết credit, trả 402 giữa buổi.

**Bài học ghi lại:** proxy dùng tên model **không có tiền tố vendor** (`deepseek-v4-pro`), khác OpenRouter gốc (`deepseek/deepseek-v4-pro`). Sai dạng thì báo lỗi model không tồn tại.

### `17:0x` — ✅ Baseline chốt số (judge thật) · TV4

| Metric | Trước sửa T4 | Sau sửa | Ghi chú |
| --- | --- | --- | --- |
| `retrieval_hit_rate` | 1.000 | **1.000** | không đổi |
| `mean_token_f1` | 0.619 | **0.921** | metric tất định, không dùng LLM ⇒ chứng minh việc sửa có tác dụng thật |
| `judge_accuracy` | 0.589 | **0.918** | 67/73 |
| `mean_judge_score` | 3.40 | **4.67** / 5 |
| **Fallback judge** | 0/73 | **0/73** | ✅ LLM judge thật chạy hết, số liệu đọc được |

Theo loại câu hỏi: `authors` 0.917 · `date` 0.917 · `summary` 0.958 · `retrieval` 0.000 (chỉ 1 câu).

**Cảnh báo về một lần chạy trung gian:** giữa hai lần trên có một lần OpenRouter hết credit khiến **73/73 rơi vào fallback heuristic**, `judge_accuracy` vẫn hiện 0.918. Con số đó **không phải LLM chấm** mà là token F1 khoác áo khác — đúng cái bẫy ghi trong `THEORY.md`. Luôn kiểm trường `reasoning` trước khi tin cột judge.

**Agent demo (rubric Mục 5) nay chạy được** — `agent_demo_answers.json` có câu trả lời thật, không còn lỗi 402.

### `17:0x` — 🔎 Phát hiện: 6 câu còn fail là do `qa.py` dùng nháy đơn

`qa.py::answer_question` tìm tiêu đề bằng regex `r"'([^']+)'"` — **nháy đơn**, trong khi test set dùng **nháy kép**. Nên `index.lookup()` (tra cứu chính xác theo tiêu đề) không bao giờ kích hoạt; mọi câu đều phụ thuộc hoàn toàn vào semantic search. 6 câu fail là các câu semantic search không đưa đúng paper lên đầu.

**Quyết định: KHÔNG sửa.** Nếu đổi test set sang nháy đơn thì `lookup()` sẽ trả đúng tài liệu bằng tra cứu tiêu đề, **bỏ qua embedding**. Khi đó corruption làm hỏng `text_for_embedding` sẽ **không** kéo `retrieval_hit_rate` xuống — che mất chính thứ bài lab cần đo. Giữ nguyên để retrieval thực sự là semantic.

Baseline 0.918 với 6 lỗi giải thích được là baseline tốt: thật, và còn dư địa để corruption kéo xuống.

### `17:2x` — ✅ 📥 **T9 Corruption** · TV2 Hân · `5bed53f`

`corruption.py` (+302 dòng) + `corruption_log.json` có schema đầy đủ: `baseline_rows`, `corrupted_rows`, `baseline_paper_ids`, `corrupted_paper_ids`, `events` — mỗi event ghi `corruption_type`, `affected_paper_ids`, `parameter`, `before`, `after`.

Đủ **6 loại lỗi có chủ đích**, 24 rows → 22 rows:

| Loại | Số record | Tham số |
| --- | ---: | --- |
| `drop_latest` | 5 | `fraction=0.2`, sắp theo `age_days` |
| `blank_summary` | 3 | `fraction=0.15` |
| `noise_summary` | 4 | `fraction=0.2`, token `corruptnoise` |
| `truncate_title` | 19 | `chars=40` |
| `stale_published_date` | 19 | `years_back=5` |
| `duplicate_rows` | 3 | `fraction=0.15` |

### `17:3x` — ✅ **T11 Corruption flow chạy end-to-end** · TV4 — PHA 2 XONG

```
[1/5] baseline: 24 rows, hit_rate=1.000
[2/5] corrupted: 22 rows
  [corrupted] collection=papers-corrupted hit_rate=0.740 token_f1=0.269 judge_acc=0.260
[3/5] repaired: 24 rows (rebuilt tu crossref_records.json)
  [repaired] collection=papers-repaired hit_rate=1.000 token_f1=0.921 judge_acc=0.918
[4/5] da danh gia du 3 trang thai tren cung test set
[5/5] comparison report -> data/reports/corruption_report.md
```

| Metric | Baseline | Corrupted | Repaired | Δ corrupt |
| --- | ---: | ---: | ---: | ---: |
| `retrieval_hit_rate` | 1.000 | **0.740** | 1.000 | **−0.260** |
| `mean_token_f1` | 0.921 | **0.269** | 0.921 | **−0.652** |
| `judge_accuracy` | 0.918 | **0.260** | 0.918 | **−0.658** |
| `mean_judge_score` | 4.671 | **2.041** | 4.671 | **−2.630** |

- **`repaired == baseline` chính xác đến từng chữ số** ⇒ repair từ raw hoạt động, và cleaning là tất định (chạy lại cho kết quả y hệt).
- **Judge thật cả 3 bộ:** fallback 0/73 mỗi bộ ⇒ số liệu judge đọc được, không phải token F1 trá hình.

**Chuỗi bằng chứng đầy đủ** (yêu cầu cốt lõi của rubric):

| Thay đổi dữ liệu | Tín hiệu quality/freshness bắt được | Metric bị kéo xuống |
| --- | --- | --- |
| 3 duplicate rows | `paper_id_unique` **FAIL** (3 trùng) | `hit_rate` −0.26 |
| 3 summary rỗng | `summary_length` **FAIL** (`min_chars` 826 → **0**) | `token_f1` −0.65 |
| Lùi ngày 5 năm | `freshness` **FAIL** — `latest_published` 2026-08-01 → **2021-07-02**, stale 22/22 | `judge_acc` −0.66 |

Quality corrupted: `overall_pass: false`, 3 check fail. Quality repaired: `overall_pass: true`, `is_fresh: true`, 0 stale, 24 rows.

### `17:3x` — 📥 T8 báo cáo baseline · TV3 Sáng · `115d6b6`

Pull về `phase1_report.md` + artifact từ lần chạy của Sáng.

**Lưu ý provenance:** `baseline_answers.json` bản của Sáng có **fallback judge 73/73** (máy Sáng chưa có key ai-box). Bốn số tổng hợp vẫn khớp tuyệt đối với bản chạy judge thật — vì QA ở đây là *extractive*, `token_f1` phân bố nhị cực (67 câu = 1.0, 6 câu = 0.0) nên heuristic và LLM judge cho cùng kết luận. Đã chạy lại `run_phase1.py` bằng key ai-box để cả 3 bộ answers cùng dùng judge thật, tránh người chấm thấy `reasoning` lẫn lộn.
