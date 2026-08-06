# Member Role Report — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Xuân Quang |
| MSSV | 2A202601776 |
| Khóa/Lớp | K4 |
| Tên nhóm | F5-1 |
| Vai trò chính | **TRUY TÌM** — embedding/index, evaluation, tích hợp hai entrypoint; chủ trì tổng hợp `group_report.md` (T6, T7, T11, T13) |
| Repository | https://github.com/Mrgintamago/K4_Day10_Data-Pipeli_F5-1 |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| T6 — Embed, index & eval wiring | `retrieval/index.py` (dùng), `evaluation/metrics.py` (dùng) | Clean dataframe từ Hân (T3), test set từ Hân (T4) | Collection `papers-baseline`, `data/embeddings/papers_embeddings.json` | **Hoàn thành** |
| T7 — Baseline pipeline | `src/pipelines/phase1.py::main` + 4 hàm phụ trợ | Raw records từ Tường (T2) | `baseline_metrics.json`, `baseline_answers.json`, `agent_demo_answers.json` | **Hoàn thành** — 7/7 bước |
| T11 — Corruption flow | `src/pipelines/corruption_flow.py::main` + `evaluate_state`, `require_baseline_artifacts`, `freshness_path_for` | Corrupted df từ Hân (T9), raw records từ Tường | `corrupted_metrics.json`, `repaired_metrics.json`, `papers_clean_repaired.*`, 2 collection riêng | **Hoàn thành** — 5/5 bước |
| T13 — Chủ trì tổng hợp | `report/group_report.md` | Artifact và số liệu của cả 4 người | Báo cáo nhóm 13 mục, mọi số đối chiếu JSON | **Hoàn thành** |
| Bonus — CLI hỏi–đáp | `script/ask.py` | Embeddings manifest của 3 trạng thái | CLI hỏi được trên `--state baseline\|corrupted\|repaired` | **Hoàn thành** |
| Bonus — Test cho tầng điều phối | `tests/test_pipelines.py` | — | 11 test, không gọi LLM/mạng/model | **Hoàn thành** |

Tôi **không** nhận ownership cho: `crossref.py` (Tường), `cleaning.py`/`testset.py`/`corruption.py` (Hân), `quality.py`/`reporting.py` (Sáng). Ba người này phụ thuộc vào phần của tôi ở chỗ: hai entrypoint là nơi duy nhất gọi hàm của họ theo đúng thứ tự, nên khi pipeline dừng thì traceback chỉ ra ngay module nào chưa xong.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Phát hiện `categories` rỗng 24/24 ngay khi Tường bàn giao raw | Hân (T4), Sáng (T5) | Hân bỏ loại câu hỏi `categories`; Sáng đánh dấu `categories_are_optional: true` thay vì để check fail oan trên baseline sạch |
| Phát hiện và sửa lỗi mẫu câu `authors` không khớp `qa.py` | Hân (T4) | `judge_accuracy` 0.589 → **0.918**; đã báo lại Hân và để comment giải thích ngay tại chỗ sửa |
| Phát hiện 2 file JSON chứa token `NaN` không hợp lệ | Hân (T9) | Hân sửa độc lập bằng `df.to_json()`; tôi thêm lớp thứ hai `sanitize_missing()` ở tầng điều phối |
| Đổi LLM provider khi hết credit giữa buổi | Cả nhóm | Chuyển sang `deepseek-v4-pro`; judge thật chạy lại được trên cả 3 bộ đánh giá |
| Ghi `CHANGELOG.md` theo từng task, kèm bằng chứng | Cả nhóm | Dùng làm nguồn cho `group_report.md` mục 11 |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Ráp 7 bước baseline, in tiến độ từng bước | `pipelines/phase1.py::main` | `run_phase1.py` chạy sạch, đủ artifact | `uv run python script/run_phase1.py` → `[7/7] report -> phase1_report.md` |
| Chỉ gọi API / sinh test set khi thật sự thiếu | `load_or_fetch_records`, `load_or_build_test_set` | Ba trạng thái dùng chung một test set | Log in `loaded_from_snapshot` và `loaded_existing` thay vì `fetched`/`built` |
| Chặn sớm khi thiếu artifact baseline | `corruption_flow.py::require_baseline_artifacts` | Thông báo rõ artifact nào thiếu thay vì crash giữa chừng | Test `test_require_baseline_artifacts_*` trong `tests/test_pipelines.py` |
| Tách freshness report cho từng trạng thái | `corruption_flow.py::freshness_path_for` | `freshness_report_corrupted.json`, `freshness_report_repaired.json` | Test khẳng định 3 path khác nhau |
| Repair từ raw, không copy baseline | `corruption_flow.py::main` | `papers_clean_repaired.csv|.json` | `repaired.paper_id ⊆ raw.paper_id` → `True` |
| Chuẩn hóa NaN trước khi lưu và index | `phase1.py::sanitize_missing` | JSON hợp lệ theo RFC 8259 | Parse toàn bộ `data/**/*.json` bằng `parse_constant` ném lỗi → 0 file lỗi |
| CLI hỏi–đáp trên cả 3 trạng thái | `script/ask.py` | In answer + top-k `paper_id` + score + HIT/MISS | `uv run python script/ask.py --state corrupted "<câu hỏi>"` |

**Một output cụ thể phần việc của tôi tạo ra:** bộ ba `baseline_metrics.json` / `corrupted_metrics.json` / `repaired_metrics.json` — ba file này là toàn bộ bằng chứng định lượng của bài lab. Chúng chỉ so sánh được với nhau vì tầng điều phối đảm bảo cả ba dùng **chung một test set, chung `top_k=4`, chung evaluator và chung model**, và mỗi trạng thái ghi vào **collection riêng** để không đè lên nhau.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Ba người còn lại viết các hàm độc lập: fetch, clean, test set, corruption, quality, report. Không hàm nào tự biết mình phải chạy khi nào, với dữ liệu nào, hay ghi vào đâu. Phần của tôi là **tầng điều phối** — biến các hàm rời rạc thành hai luồng chạy được từ đầu đến cuối, và quan trọng hơn: đảm bảo ba trạng thái dữ liệu so sánh được với nhau.

Yêu cầu khó nhất không phải "chạy cho xong" mà là **giữ tính công bằng của phép so sánh**. Nếu test set đổi giữa hai lần đo, hoặc hai trạng thái ghi chung một collection, thì delta metric không còn quy được cho corruption và cả bài lab mất ý nghĩa.

### Cách triển khai

Bốn quyết định chính trong `phase1.py` và `corruption_flow.py`:

**1. Ưu tiên artifact đã có, chỉ tạo mới khi thiếu.** `load_or_fetch_records` chỉ gọi Crossref khi snapshot chưa tồn tại hoặc bật `REFRESH_SOURCE`; `load_or_build_test_set` tương tự với `REFRESH_TEST_SET`. Crossref là API sống — gọi lại hôm sau ra dữ liệu khác. Nếu để pipeline tự fetch mỗi lần chạy thì baseline và corrupted đo trên hai tập dữ liệu khác nhau.

**2. Chặn sớm với thông báo có ích.** `require_baseline_artifacts` kiểm tra 4 file trước khi làm bất cứ việc gì, và báo đúng tên artifact bị thiếu kèm lệnh cần chạy. Không có nó thì người dùng chạy corruption trước baseline sẽ nhận `FileNotFoundError` giữa chừng, sau khi đã tốn vài phút embed.

**3. Tách trạng thái triệt để.** `evaluate_state` nhận `embeddings_path` riêng cho từng trạng thái; `LocalEmbeddingIndex._derive_collection_name` map path đó sang tên collection tương ứng. Đây không phải chi tiết trang trí: `LocalEmbeddingIndex.build` **xóa collection trùng tên rồi tạo lại**, nên nếu ba trạng thái dùng chung một tên thì chạy corruption sẽ phá luôn index baseline. `freshness_path_for` cũng tách tương tự vì `Paths` chỉ định nghĩa một đường dẫn freshness duy nhất.

**4. Lỗi phụ không được làm hỏng luồng chính.** `run_agent_demo` bọc try/except và ghi lỗi vào artifact thay vì ném ra ngoài — agent demo phụ thuộc LLM provider, không đáng để làm hỏng cả pipeline khi provider trục trặc. Quyết định này chứng minh giá trị ngay trong buổi: khi provider trả `402`, baseline vẫn chạy hết 7/7 bước.

Ngoài ra `sanitize_missing` chuẩn hóa `NaN → ""` tại ba chỗ (sau khi đọc CSV, trước khi lưu, trước khi index) để artifact JSON hợp lệ và metadata Chroma không chứa float NaN.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `list[PaperRecord]` từ `crossref.py`; `pd.DataFrame` 10 cột từ `cleaning.py`; `data/eval/test_set.json` |
| Output | `*_metrics.json` (4 metric + `samples` + `ragas`), `*_answers.json` (73 bản ghi có `retrieved_doc_ids`, `token_f1`, `judge`), embeddings manifest, 2 report markdown |
| Module phụ thuộc | `ingestion/crossref.py`, `ingestion/cleaning.py`, `ingestion/corruption.py`, `evaluation/testset.py`, `evaluation/metrics.py`, `observability/quality.py`, `observability/reporting.py`, `retrieval/index.py` |
| Module sử dụng output | `observability/reporting.py` (đọc metrics để dựng 2 report); `script/ask.py` (đọc embeddings manifest) |
| Điều kiện lỗi cần xử lý | Raw records rỗng → `RuntimeError` có thông báo; thiếu artifact baseline → chặn trước khi embed; LLM provider lỗi → agent demo ghi lỗi vào file, pipeline vẫn chạy tiếp; NaN từ CSV → chuẩn hóa trước khi lưu và index |

### Cách xác minh

```bash
uv run python script/run_phase1.py
uv run python script/run_corruption_flow.py
uv run python -m pytest tests/ -q
```

- **Kết quả mong đợi:** baseline in `[7/7]`, corruption flow in `[5/5]`, ba bộ metrics sinh ra trên cùng test set, test suite pass.
- **Kết quả thực tế:**
  - `[5/7] hit_rate=1.000 token_f1=0.921 judge_acc=0.918` → `[7/7] report -> phase1_report.md`
  - `[corrupted] hit_rate=0.740 token_f1=0.269 judge_acc=0.260` · `[repaired] hit_rate=1.000 token_f1=0.921 judge_acc=0.918` → `[5/5] comparison report`
  - `17 passed` (11 test của tôi + 6 test của Tường)
- **Artifact/log:** `data/results/*_metrics.json`, `data/reports/phase1_report.md`, `data/reports/corruption_report.md`. Không có secret trong bất kỳ file nào.

Một kiểm tra tôi coi là bắt buộc và đã chạy trên cả ba bộ: đếm số bản ghi chứa `"Fallback heuristic"` trong `*_answers.json` — kết quả **0/73 mỗi bộ**, nghĩa là LLM judge thật đã chạy.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** sau khi sửa lỗi mẫu câu `authors`, còn đúng 6/73 câu fail. Truy ra nguyên nhân: `qa.py::answer_question` tìm tiêu đề bằng regex **nháy đơn** `r"'([^']+)'"`, trong khi test set của Hân dùng **nháy kép**. Hệ quả là `index.lookup()` — tra cứu chính xác theo tiêu đề — không bao giờ được kích hoạt, mọi câu hỏi phụ thuộc hoàn toàn vào semantic search.

- **Các phương án đã cân nhắc:**
  1. Đổi test set sang nháy đơn để `lookup()` hoạt động. Nhanh, một dòng, và gần như chắc chắn đẩy baseline lên sát 1.000 ở cả bốn metric.
  2. Giữ nguyên nháy kép, chấp nhận baseline 0.918 với 6 lỗi giải thích được.

- **Phương án đã chọn:** phương án 2 — giữ nguyên.

- **Lý do:** đây là trade-off giữa *điểm số trông đẹp* và *tính hợp lệ của thí nghiệm*. Nếu `lookup()` hoạt động, nó trả đúng tài liệu bằng tra cứu tiêu đề và **bỏ qua hoàn toàn tầng embedding**. Khi đó corruption phá `text_for_embedding` — blank summary, noise — sẽ **không** kéo `retrieval_hit_rate` xuống, vì tài liệu đúng vẫn được tìm thấy qua tiêu đề. Nói cách khác, sửa lỗi này sẽ che mất chính hiện tượng mà bài lab yêu cầu chứng minh. Baseline cao hơn nhưng thí nghiệm mất giá trị.

- **Bằng chứng quyết định phù hợp:** giữ nguyên nên `retrieval_hit_rate` phản ánh đúng chất lượng embedding, và corruption kéo được nó từ 1.000 xuống **0.740** (−0.260). Nếu chọn phương án 1, cột này nhiều khả năng đứng yên ở 1.000 qua cả ba trạng thái và nhóm sẽ không có bằng chứng nào cho thấy corruption ảnh hưởng tới **tầng retrieval** — chỉ còn bằng chứng ở tầng sinh câu trả lời.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** một lần chạy giữa buổi cho `judge_accuracy = 0.918`, trông rất đẹp và trùng khớp với lần chạy trước đó. Không có exception, không có cảnh báo, pipeline in `[7/7]` bình thường.

- **Lệnh hoặc bước tái hiện:**
  ```bash
  uv run python script/run_phase1.py
  # roi dem so ban ghi co "Fallback heuristic" trong baseline_answers.json
  ```

- **Nguyên nhân gốc:** LLM provider hết credit và trả `402`. `evaluation/metrics.py::_judge_answer` bắt **mọi** exception rồi âm thầm rơi xuống heuristic dựa trên `token_f1`:

  ```python
  except Exception:
      score = 5 if _token_f1(...) >= 0.95 else 3 if _token_f1(...) >= 0.5 else 1
  ```

  Kết quả là `judge_accuracy` trông như một cột độc lập nhưng thực chất là `token_f1` khoác áo khác. Nguy hiểm gấp đôi vì con số **trùng khớp** với lần chạy judge thật — QA ở đây là *extractive* nên `token_f1` phân bố nhị cực (67 câu = 1.0, 6 câu = 0.0), khiến heuristic và LLM judge cho cùng kết luận. Một sự trùng hợp làm lỗi càng khó phát hiện.

- **Cách xử lý:** đổi `LLM_MODEL` sang `deepseek-v4-pro` qua endpoint tương thích OpenAI và chạy lại toàn bộ. Ghi cảnh báo vào `THEORY.md`, `PLAN` và `CHANGELOG` để cả nhóm biết.

- **Cách xác minh sau khi sửa:** đếm số bản ghi chứa `"Fallback heuristic"` trong cả ba file `*_answers.json` — kết quả **0/73** mỗi file. Kiểm thêm trường `reasoning` của vài mẫu, thấy nội dung do LLM sinh (`"The model answer lists the same authors in the same order as the reference answer..."`) chứ không phải câu cố định của heuristic.

- **Điều học được:** một fallback im lặng nguy hiểm hơn một exception. Exception thì dừng pipeline và ai cũng thấy; fallback thì cho ra số trông hợp lý và không ai nghi ngờ. **Mọi metric phụ thuộc dịch vụ ngoài đều cần một trường ghi lại nó được tính bằng cách nào**, và bước kiểm trường đó phải là thói quen chứ không phải việc làm khi nghi ngờ. Đây cũng là lý do tôi luôn dùng `mean_token_f1` — metric tất định — làm mỏ neo khi cần chứng minh một thay đổi có tác dụng thật.

## 7. Hiểu biết về luồng end-to-end

**1. Dữ liệu đi từ Crossref đến vector index như thế nào?**
Gọi Crossref REST API với query và filter lấy từ `config.py`, lưu **raw response nguyên vẹn xuống đĩa trước khi parse** — bước này quan trọng vì raw snapshot là nguồn duy nhất để repair sau này. Parse thành `PaperRecord`, rồi cleaning chuẩn hóa text, parse ngày, tính `age_days` và dựng cột `text_for_embedding`. MiniLM-L6-v2 biến cột đó thành vector 384 chiều, nạp vào ChromaDB với độ đo cosine. Toàn bộ đường dẫn lấy từ `Paths`, không hard-code ở đâu.

**2. Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**
Mỗi câu hỏi sinh từ một bản ghi cụ thể, nên `ground_truth_doc_ids` chính là `paper_id` của bản ghi đó. Khi đánh giá, hệ thống truy vấn lấy `top_k=4` tài liệu và so `retrieved_doc_ids` với `ground_truth_doc_ids`: trùng ít nhất một là **hit**. Đây là thước đo *tầng retrieval*. Riêng biệt với nó, `token_f1` và LLM judge chấm nội dung câu trả lời — thước đo *tầng sinh*. Tách hai tầng cho phép định vị lỗi: hit rate giảm nghĩa là lỗi từ dữ liệu/embedding; hit rate giữ nguyên mà judge giảm nghĩa là lấy đúng tài liệu nhưng nội dung tài liệu đã hỏng.

**3. Quality checks khác freshness monitoring ở điểm nào?**
Quality hỏi *"dữ liệu hiện có đúng và đủ không"* — null, trùng lặp, độ dài summary, đủ cột. Freshness hỏi *"dữ liệu có mới không"* — `latest_published`, số dòng vượt ngưỡng 180 ngày. Khác biệt này không phải hình thức: kết quả của nhóm cho thấy `stale_published_date` làm freshness fail hoàn toàn (22/22 dòng stale) trong khi **không metric nào thay đổi**. Nếu chỉ có quality check thông thường và evaluation, lỗi đó hoàn toàn vô hình — pipeline báo "xanh" trong khi đang phục vụ dữ liệu cũ 5 năm.

**4. Vì sao phải dùng cùng test set cho ba trạng thái?**
Vì đây là một thí nghiệm, và thí nghiệm chỉ có nghĩa khi **đúng một biến thay đổi** — ở đây là chất lượng dữ liệu. Nếu sinh lại test set giữa các lần đo, chênh lệch metric có thể đến từ bộ câu hỏi mới chứ không phải từ corruption, và không có cách nào tách hai nguyên nhân đó ra. Vì thế `REFRESH_TEST_SET` giữ tắt, và test set bị khóa ngay sau khi baseline chốt. Cùng lý do, ba trạng thái dùng chung `top_k=4`, cùng evaluator và cùng model.

**5. Repair được xem là thành công dựa trên artifact và metric nào?**
Bốn bằng chứng: `repaired.paper_id ⊆ raw.paper_id` (True); `repaired == baseline` so từng ô (True); 5 `paper_id` mất khi corrupt lấy lại được đủ 24/24; và bốn metric trở về đúng giá trị baseline, kèm `overall_pass: true` với `is_fresh: true`, 0 dòng stale. Điều kiện cứng: repaired phải **sinh lại bằng cách chạy cleaning từ raw records**, không được copy `papers_clean.csv`. Copy chỉ chứng minh nhóm còn giữ backup; chạy lại từ raw chứng minh thêm rằng cleaning là tất định.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | **0.7397** | 1.0000 | Baseline đạt trần vì corpus 24 tài liệu mà `top_k=4`. Tôi không đọc đây là "retrieval hoàn hảo" mà là "corpus quá nhỏ để metric phân biệt tinh" — giá trị thật của nó là tạo trần để corruption có chỗ kéo xuống |
| `mean_token_f1` | 0.9206 | **0.2686** | 0.9206 | Metric tôi tin nhất vì tất định, không phụ thuộc LLM. Chính nó chứng minh việc sửa lỗi `authors` có tác dụng thật (0.619 → 0.921) khi cột judge còn đang nghi ngờ |
| `judge_accuracy` | 0.9178 | **0.2603** | 0.9178 | 67/73 → 19/73. Chỉ đọc được sau khi xác nhận fallback 0/73 |
| `mean_judge_score` | 4.6712 | **2.0411** | 4.6712 | Phân bố nhị cực (5 hoặc 1) do QA extractive — hệ quả là judge không phân biệt được các mức đúng một phần |
| Quality checks | `true` | **`false`** | `true` | Corrupted fail 3 check: `paper_id_unique`, `summary_length`, `freshness` |
| Freshness status | Fresh, 0 stale | **Stale, 22/22** | Fresh, 0 stale | `latest_published` 2026-08-01 → 2021-07-02 → 2026-08-01 |

### Kết luận từ số liệu

**1. `blank_summary` (3 dòng) + `duplicate_rows` (3 dòng) → `summary_length` và `paper_id_unique` chuyển FAIL → `retrieval_hit_rate` −0.2603 và `mean_token_f1` −0.6519.**
Mắt xích quan trọng nằm ở bước dựng lại `text_for_embedding` sau khi corrupt: nếu chỉ sửa cột `summary` mà giữ nguyên cột này thì dữ liệu *trông* hỏng trong CSV nhưng vector đem đi index vẫn là vector cũ, và metric sẽ không đổi.

**2. Repair chạy lại cleaning từ `crossref_records.json` → `overall_pass` về `true`, `is_fresh` về `true` với 0 dòng stale → cả bốn metric trở về đúng giá trị baseline, khớp tuyệt đối chứ không phải xấp xỉ.**
Việc khớp tuyệt đối chứng minh thêm một điều ngoài "repair hoạt động": cleaning là **tất định**. Nếu repaired lệch baseline, đó sẽ là dấu hiệu cleaning phụ thuộc thứ tự dòng hoặc thời điểm chạy.

**Corruption nào ảnh hưởng rõ nhất và vì sao?**
Nhóm lỗi **phá nội dung** — `blank_summary` và `noise_summary` — dù chỉ chạm 7/24 bản ghi. Lý do: chúng đánh trực tiếp vào `text_for_embedding`, tức là thứ duy nhất mà retrieval nhìn thấy. Hỏng cột đó thì vector sai, tài liệu đúng không được tìm thấy, và câu trả lời sinh ra từ context sai — cả hai tầng cùng hỏng. So sánh với `truncate_title`: chạm tới 19 bản ghi, nhiều gấp gần ba lần, nhưng ảnh hưởng nhẹ hơn vì tiêu đề chỉ là một phần nhỏ của chuỗi embed và phần abstract vẫn còn nguyên.

**Kết quả nào khác với kỳ vọng ban đầu?**
Tôi kỳ vọng `stale_published_date` sẽ kéo metric xuống, vì nó chạm tới 19/24 bản ghi — diện rộng nhất cùng với `truncate_title`. Thực tế **metric không đổi chút nào**, chỉ freshness fail hoàn toàn.

Giả thuyết của tôi: `published` không nằm trong `text_for_embedding` và không được `_extract_answer` dùng cho phần lớn câu hỏi, nên lùi ngày không làm hỏng nội dung nào. Cách kiểm: đối chiếu `corrupted_answers.json` với `baseline_answers.json` ở riêng các câu `question_type = "date"` — nếu giả thuyết sai thì nhóm câu này phải tụt riêng.

Nhìn lại, đây là **kết quả có giá trị nhất của cả bài lab**, không phải một thất bại. Nó là bằng chứng trực tiếp cho câu hỏi "vì sao cần observability tách khỏi evaluation": có những lỗi dữ liệu mà mọi metric đều im lặng, và chỉ giám sát dữ liệu mới phát hiện được. Một pipeline chỉ nhìn metric sẽ báo "mọi thứ bình thường" trong khi đang trả lời bằng corpus cũ 5 năm.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

**1. Về data pipeline:** raw snapshot bất biến là thứ biến "pipeline chạy được" thành "pipeline phục hồi được". Toàn bộ pha 2 của bài lab đứng trên đúng một quyết định ở pha 1 — lưu raw response *trước khi* parse. Không có nó thì repair chỉ còn cách copy baseline, và copy không chứng minh được điều gì về khả năng của pipeline. Bài học rộng hơn: mỗi bước biến đổi phải tạo artifact mới thay vì ghi đè, để luôn quay ngược được.

**2. Về data quality/observability:** test kiểm *code có đúng không*, observability kiểm *dữ liệu đang chảy qua lúc này có lành không*. Hai việc khác nhau và không thay thế được cho nhau. Kết quả `stale_published_date` chứng minh điều đó bằng số: code không đổi một dòng, mọi test pass, mọi metric giữ nguyên — nhưng dữ liệu đã cũ 5 năm và chỉ freshness check phát hiện.

**3. Về ảnh hưởng của dữ liệu đến RAG agent:** chất lượng dữ liệu là **trần** của chất lượng agent. `judge_accuracy` rơi từ 0.918 xuống 0.260 mà không đổi một dòng code nào, không đổi model, không đổi prompt — chỉ đổi dữ liệu. Đổi model tốt hơn sẽ không cứu được tình huống này, vì tài liệu đúng không được tìm thấy hoặc nội dung nó đã hỏng.

### Nếu có thêm thời gian

Tăng `max_results` từ 24 lên 200+ và chạy lại toàn bộ.

**Lý do:** `retrieval_hit_rate` baseline đang đạt trần 1.000 chỉ vì `top_k=4` trên corpus 24 tài liệu — mỗi truy vấn lấy 1/6 corpus, trúng gần như là mặc định. Ở mức đó, metric không phân biệt được "retrieval tốt" với "corpus quá nhỏ để sai".

**Cách đo cải thiện:** với corpus 200 tài liệu và giữ nguyên `top_k=4`, mỗi truy vấn chỉ còn lấy 2% corpus. Kỳ vọng baseline hit rate xuống khoảng 0.85–0.95 — thấp hơn nhưng **có ý nghĩa hơn**, vì lúc đó chênh lệch giữa các trạng thái phản ánh chất lượng embedding thật chứ không phải kích thước corpus. Kiểm bằng cách chạy song song hai cấu hình `max_results` và so đường cong hit rate theo `top_k` ∈ {1, 2, 4, 8}: corpus lớn sẽ cho đường cong dốc hơn, corpus nhỏ gần như phẳng ở 1.0.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Xuân Quang
**Ngày xác nhận:** 2026-08-06
