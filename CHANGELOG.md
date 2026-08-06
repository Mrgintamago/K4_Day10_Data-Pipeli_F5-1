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
| T5 Quality + freshness | TV3 Sáng | ⬜ **đang chặn cả nhóm** | CP2 |
| T6 Index + eval wiring | TV4 Quang | ✅ chạy thật, hit_rate=1.000 | CP2 |
| T7 Baseline pipeline | TV4 Quang | 🟡 qua 5/7 bước, chờ T5 | CP3 |
| T8 Baseline report | TV3 Sáng | ⬜ | CP3 |
| T9 Corruption + log | TV2 Hân | ⬜ | CP4 |
| T10 Repair từ raw | TV2 + TV1 | ⬜ | CP4 |
| T11 Corruption flow | TV4 Quang | 🟡 chờ T7 | CP5 |
| T12 Comparison report | TV3 Sáng | ⬜ | CP5 |
| T13 Group + báo cáo cá nhân | TV4 chủ trì | ⬜ (4 file cá nhân đã tạo khung) | CP6 |
| T14 Review + demo | Cả nhóm | ⬜ | CP6 |

**Blocker duy nhất:** T5 `run_data_quality_checks` (`src/observability/quality.py:21`). Baseline pipeline đã chạy qua 5/7 bước và dừng ở đây.

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
