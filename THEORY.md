# Lý thuyết bài lab — Data Pipeline & Data Observability cho RAG

> Tài liệu này giải thích **vì sao** làm từng bước, không phải **cách gõ code**.
> Cách làm từng bước xem [Guide.md](Guide.md); chia việc và timeline xem [PLAN_K4_CHIEU_2026-08-06.md](PLAN_K4_CHIEU_2026-08-06.md).

---

## 1. Bài toán: vì sao cần RAG

Hỏi thẳng một LLM về bài báo học thuật mới có ba vấn đề:

1. **Kiến thức bị cắt theo ngày huấn luyện.** Bài báo công bố sau mốc đó thì model không biết.
2. **Không trích được nguồn.** Model trả lời trôi chảy nhưng không chỉ được câu trả lời đến từ đâu.
3. **Không kiểm soát được phạm vi.** Không giới hạn được model chỉ trả lời trong corpus của mình.

**RAG (Retrieval-Augmented Generation)** giải quyết bằng cách tách làm hai tầng:

```
câu hỏi ──> [RETRIEVAL] tìm k đoạn văn liên quan trong corpus của mình
                 │
                 ▼
          [GENERATION] LLM đọc k đoạn đó rồi mới trả lời
```

Hệ quả quan trọng cho cả bài lab: **chất lượng câu trả lời bị chặn trên bởi chất lượng dữ liệu được nạp vào**. LLM giỏi đến mấy cũng không trả lời đúng nếu tầng retrieval đưa nhầm tài liệu, hoặc tài liệu đúng nhưng nội dung đã bị hỏng. Đó chính là điều bài lab bắt phải chứng minh bằng số, chứ không phải nói suông.

---

## 2. Vòng đời dữ liệu

```
Crossref API
   │  (1) fetch — lưu raw response NGUYÊN VẸN trước khi parse
   ▼
data/raw/crossref_response.json ──> data/raw/crossref_records.json
   │  (2) clean — chuẩn hóa, lọc, tính field dẫn xuất
   ▼
data/clean/papers_clean.csv|.json
   │  (3) embed + index
   ▼
ChromaDB collection `papers-baseline` + data/embeddings/papers_embeddings.json
   │  (4) hỏi–đáp trên test set cố định
   ▼
data/results/baseline_metrics.json + baseline_answers.json
   │  (5) quan sát dữ liệu
   ▼
data/quality/*.json + freshness_report.json
   │  (6) báo cáo
   ▼
data/reports/phase1_report.md
```

### Vì sao phải lưu raw *trước khi* parse

`src/ingestion/crossref.py` yêu cầu ghi raw response xuống đĩa **trước** bước parse. Ba lý do:

- **Khả năng phục hồi.** Raw snapshot là nguồn sự thật duy nhất để tái tạo lại dữ liệu sạch. Ở pha 2, repair *bắt buộc* chạy lại cleaning từ raw — nếu không có raw thì không repair được, chỉ còn cách copy baseline, và đó là gian lận kết quả.
- **Khả năng truy vết (lineage).** Khi clean data có gì lạ, phải trả lời được: lỗi do nguồn hay do code cleaning của mình? Chỉ so được khi còn raw.
- **Tái lập được thí nghiệm.** Crossref là API sống, gọi lại hôm sau ra kết quả khác. Nếu refresh giữa các lần đo thì ba trạng thái baseline/corrupted/repaired không còn so sánh được với nhau. Vì thế `REFRESH_SOURCE` mặc định tắt.

Nguyên tắc chung: **raw là bất biến (immutable)**. Mọi biến đổi tạo file mới, không ghi đè raw.

---

## 3. Cleaning và schema

Cleaning không phải "xóa dòng xấu". Nó là bước biến dữ liệu của *nguồn* thành dữ liệu của *hệ thống mình*, với một schema đã khóa.

Schema tối thiểu (chốt trong contract mục 3 của plan):

| Trường | Vì sao cần |
| --- | --- |
| `paper_id` | **Khóa xuyên suốt** raw → clean → index → eval. Không có nó thì không nối được "câu trả lời này lấy từ tài liệu nào" |
| `title`, `summary` | Nội dung người đọc và LLM nhìn thấy |
| `published`, `age_days` | Đầu vào cho freshness monitoring |
| `authors_joined`, `categories_joined` | Metadata phẳng để nhét vào Chroma (vector store không nhận list lồng nhau) |
| `text_for_embedding` | Chuỗi thực sự được đem đi embed |
| `abs_url`, `pdf_url` | Trích nguồn trong câu trả lời |

### `text_for_embedding` — vì sao tách riêng

Embedding model không đọc cả bản ghi, nó đọc **một chuỗi**. Việc chọn ghép gì vào chuỗi đó (title + summary + categories?) là một quyết định thiết kế ảnh hưởng trực tiếp tới retrieval. Tách thành cột riêng để:

- Quyết định đó **hiện rõ và kiểm tra được**, không giấu trong code.
- Khi corruption làm hỏng `summary`, phải **build lại** `text_for_embedding` thì corruption mới thực sự chạm tới tầng embedding (xem mục 7).

### `paper_id` phải ổn định

Metric `retrieval_hit_rate` so `retrieved_doc_ids` với `ground_truth_doc_ids`. Nếu `paper_id` đổi giữa các lần chạy (ví dụ sinh theo số thứ tự dòng), test set cũ trỏ vào ID không còn tồn tại và hit rate tụt về 0 **vì lỗi kỹ thuật, không phải vì chất lượng dữ liệu**. Đó là hỏng thí nghiệm, không phải phát hiện.

---

## 4. Embedding và vector store

- **Model:** `sentence-transformers/all-MiniLM-L6-v2` (`src/core/config.py`, dùng qua `src/retrieval/embeddings.py`). Model nhỏ, chạy CPU, không cần API key — đủ cho corpus vài chục bài.
- **Ý tưởng:** mỗi văn bản → một vector. Văn bản gần nghĩa → vector gần nhau. Tìm kiếm ngữ nghĩa = tìm vector gần nhất, khác hẳn tìm từ khóa: hỏi "mô hình ngôn ngữ tự truy hồi" vẫn khớp tài liệu viết "retrieval-augmented LLM".
- **Độ đo:** cosine — `LocalEmbeddingIndex.build` tạo collection với `{"hnsw": {"space": "cosine"}}` (`src/retrieval/index.py:103`). Chroma trả về *distance*, code quy về score bằng `max(0, 1 - distance)` (`index.py:161`).
- **`top_k = 4`** (`src/core/config.py`): lấy 4 tài liệu gần nhất làm context. k nhỏ quá thì bỏ sót tài liệu đúng; k lớn quá thì nhồi nhiễu vào prompt và LLM dễ bám vào đoạn sai.

### Vì sao mỗi trạng thái một collection riêng

Ba collection: `papers-baseline`, `papers-corrupted`, `papers-repaired`.

`LocalEmbeddingIndex.build` **xóa collection cũ cùng tên rồi tạo lại** (`index.py:97-104`). Nếu ba trạng thái dùng chung một tên, chạy corruption sẽ phá luôn index baseline, và không còn cách nào so sánh ngoài chạy lại từ đầu. Tách tên collection + tách embeddings manifest là cách giữ ba thí nghiệm độc lập trên cùng một máy.

---

## 5. Evaluation — đo cái gì và đo để làm gì

Toàn bộ định nghĩa nằm trong `src/evaluation/metrics.py::evaluate_pipeline`. Bốn chỉ số, mỗi chỉ số soi một tầng khác nhau:

| Metric | Định nghĩa trong code | Soi tầng nào | Đọc thế nào |
| --- | --- | --- | --- |
| `retrieval_hit_rate` | Tỉ lệ câu hỏi mà **ít nhất một** `retrieved_doc_ids` nằm trong `ground_truth_doc_ids` | **Retrieval** | Tụt ⇒ lỗi ở dữ liệu/embedding/index, chưa liên quan tới LLM |
| `mean_token_f1` | F1 trên **tập token** giữa câu trả lời và ground truth | Generation (từ vựng) | Rẻ và tất định, nhưng thô: diễn đạt khác đi là tụt điểm dù đúng nghĩa |
| `judge_accuracy` | Tỉ lệ câu được LLM-judge đánh `correct = true` | Generation (ngữ nghĩa) | Sát cảm nhận người dùng hơn, nhưng có nhiễu của chính LLM |
| `mean_judge_score` | Trung bình điểm 1–5 của judge | Generation (mức độ) | Bắt được thay đổi nhỏ mà `judge_accuracy` (nhị phân) không thấy |

### Vì sao cần cả hai loại

`retrieval_hit_rate` và các chỉ số generation tách nhau ra để **định vị lỗi**:

- Hit rate giảm, judge cũng giảm → lỗi từ dữ liệu, lan xuống câu trả lời.
- Hit rate giữ nguyên nhưng judge giảm → lấy đúng tài liệu nhưng nội dung tài liệu đã hỏng (ví dụ summary bị blank hoặc nhiễu).

Đây chính là "chuỗi bằng chứng" mà rubric đòi.

### LLM-as-judge và cái bẫy fallback

`_judge_answer` gọi LLM với `with_structured_output(JudgeVerdict)` để lấy `score`, `correct`, `reasoning`. **Nếu LLM lỗi (hết key, rate limit, mạng), hàm này không crash mà rơi xuống heuristic dựa trên token F1** (`metrics.py:61-70`).

Hệ quả phải ghi vào báo cáo: nếu fallback được kích hoạt, `judge_accuracy` không còn là "LLM chấm" mà chỉ là token F1 khoác áo khác — hai cột số trông độc lập nhưng thực ra cùng một nguồn. Kiểm bằng trường `reasoning` trong `*_answers.json`: có chữ "Fallback heuristic judge" tức là judge thật không chạy.

### Ragas

Chỉ chạy khi `RUN_RAGAS=1` (`metrics.py:74`), gồm `answer_relevancy`, `context_precision`, `context_recall`, `faithfulness`. Chậm và tốn quota LLM ⇒ là phần bonus, cắt đầu tiên khi thiếu giờ.

### Vì sao test set phải cố định

Ba trạng thái dùng chung `data/eval/test_set.json`, chung `top_k=4`, chung evaluator, chung model. Đổi bất cứ thứ nào giữa các lần đo thì chênh lệch số không còn quy được cho corruption — đó là lý do `REFRESH_TEST_SET` mặc định tắt. Nguyên tắc thí nghiệm: **chỉ đổi một biến tại một thời điểm**, ở đây biến đó là *chất lượng dữ liệu*.

---

## 6. Data observability: quality vs freshness

Hai câu hỏi khác nhau, đừng gộp:

| | **Data quality** | **Data freshness** |
| --- | --- | --- |
| Hỏi | Dữ liệu hiện có **đúng và đủ** không? | Dữ liệu có **mới** không? |
| Kiểm | row count, `paper_id` không null & unique, `title` không null, độ dài `summary` | `latest_published`, `oldest_published`, `stale_rows`, `total_rows`, `is_fresh` |
| Hàm | `run_data_quality_checks` | `build_freshness_report` |
| Bắt được | Bản ghi hỏng, trùng, thiếu trường | Pipeline "chạy xanh" nhưng đang phục vụ dữ liệu cũ |

Cả hai ở `src/observability/quality.py` (nhóm phải implement — hiện là `NotImplementedError`). Ngưỡng freshness: **180 ngày**, `freshness_threshold_days` trong `src/core/config.py`; đây cũng là filter khi gọi Crossref (`from-pub-date`).

### Vì sao freshness đáng một chỉ số riêng

Đây là dạng lỗi im lặng nguy hiểm nhất: **không có exception, không có null, mọi test pass** — chỉ là dữ liệu đã ngừng cập nhật ba tháng. Không có freshness check thì không ai biết cho tới khi người dùng hỏi về bài báo mới và agent trả lời bằng corpus cũ.

Ý chính của "observability" so với "testing": test hỏi *code có đúng không*, observability hỏi *dữ liệu đang chảy qua hệ thống lúc này có lành không*. Code không đổi vẫn có thể phục vụ dữ liệu hỏng.

---

## 7. Corruption là một thí nghiệm có kiểm soát

`src/ingestion/corruption.py::corrupt_clean_dataframe` phải tạo 6 loại lỗi **có chủ đích** và ghi `data/results/corruption_log.json` (loại lỗi, bản ghi bị tác động, tham số, giá trị trước/sau).

Không phải "làm hỏng dữ liệu cho vui" — mỗi loại lỗi là một giả thuyết: *lỗi này sẽ hiện lên ở tín hiệu nào?*

| Loại lỗi | Mô phỏng sự cố thật | Tín hiệu quan sát dự kiến | Metric dự kiến bị ảnh hưởng |
| --- | --- | --- | --- |
| Xóa bản ghi mới nhất | Job ingest fail âm thầm | Freshness: `latest_published` lùi lại, `is_fresh` = false | Hit rate giảm ở câu hỏi về bài mới |
| Blank `summary` | Trường bị rỗng ở upstream | Quality: check độ dài summary fail | Hit rate + judge đều giảm |
| Nhiễu vào text | Lỗi encoding / parse HTML | Có thể **không** check nào bắt được | Judge giảm dù hit rate giữ nguyên |
| Truncate `title` | Cắt cột ở DB | Quality: độ dài title bất thường | Lookup theo title hỏng |
| Stale publication date | Sai timezone / parse ngày | Freshness fail | **Metric có thể không đổi** |
| Duplicate rows | Ingest chạy hai lần | Quality: `paper_id` unique fail | Context bị lặp, đẩy tài liệu khác ra khỏi top-4 |

### Hai kết quả đều là phát hiện có giá trị

- **Quality bắt được + metric giảm** → chứng minh được chuỗi `data → signal → chất lượng agent`.
- **Metric im lặng nhưng quality/freshness kêu** (điển hình: stale date) → chứng minh **vì sao cần observability**: có những lỗi mà evaluation không thấy, chỉ giám sát dữ liệu mới thấy. Đừng coi trường hợp này là thất bại, hãy viết nó vào báo cáo.

### Đừng quên rebuild `text_for_embedding`

Bước 7 trong pseudo-code của `corrupt_clean_dataframe`. Nếu chỉ sửa `summary` mà giữ nguyên `text_for_embedding`, dữ liệu **trông** hỏng trong CSV nhưng vector đem đi index vẫn là vector cũ ⇒ metric không đổi, và kết luận rút ra sẽ sai.

---

## 8. Repair và chuỗi bằng chứng

**Repair = chạy lại cleaning từ `data/raw/crossref_records.json`.** Không copy `papers_clean.csv` của baseline.

Vì sao khắt khe:

- Copy baseline chỉ chứng minh "tôi còn giữ một bản backup", không chứng minh **pipeline** có khả năng phục hồi.
- Chạy lại từ raw chứng minh raw đủ để tái tạo trạng thái sạch — đúng vai trò của một data pipeline thật.
- Nếu repaired **không** khớp baseline, đó là thông tin quan trọng: cleaning của nhóm không tất định (có randomness, phụ thuộc thời gian như `age_days`, hoặc phụ thuộc thứ tự dòng).

Sản phẩm cuối là `data/reports/corruption_report.md` với ba cột baseline / corrupted / repaired và delta giữa chúng. Điều kiện qua cổng:

> Nêu được **một** chuỗi cụ thể: thay đổi dữ liệu nào → tín hiệu quality/freshness nào đổi → metric nào đổi bao nhiêu.

Ví dụ dạng viết đúng:
> Blank `summary` ở 5/24 bản ghi → check độ dài summary chuyển fail (5 dòng vi phạm) → `retrieval_hit_rate` 0.83 → 0.58, `mean_judge_score` 4.2 → 3.1. Sau repair từ raw: 0.83 và 4.2, khớp baseline.

---

## 9. Cạm bẫy thường gặp

| Cạm bẫy | Vì sao hỏng | Cách tránh |
| --- | --- | --- |
| Hard-code đường dẫn | Ba trạng thái ghi đè lên nhau, mất baseline | Chỉ lấy path từ `Paths` trong `src/core/config.py` |
| Refresh source/test set giữa các lần đo | Chênh lệch không quy được cho corruption | Giữ `REFRESH_SOURCE`/`REFRESH_TEST_SET` tắt |
| Sửa tay metrics cho "đẹp" | Gian lận, và rubric đối chiếu report với artifact | Mọi số trong report copy từ JSON |
| Kết luận "đã recovery" khi số không chứng minh | Vượt quá dữ liệu | Ghi đúng trạng thái + blocker, không đánh dấu hoàn thành |
| Dùng chung tên collection | `build` xóa collection cũ, mất index baseline | Ba tên riêng như trong config |
| Coi exit code 0 là xong | Pipeline chạy hết nhưng artifact rỗng/sai | Mở đọc từng file trong checklist CP3 |
| Commit `.env` | Lộ API key, mất điểm rubric | `.env` trong `.gitignore`, kiểm `git status` trước khi push |
| Bỏ qua fallback judge | Đọc sai ý nghĩa `judge_accuracy` | Grep `reasoning` trong `*_answers.json` |

---

## 10. Câu hỏi tự kiểm trước khi demo

Mỗi thành viên phải tự trả lời được, không đọc slide:

1. Nguồn dữ liệu là gì, query và filter nào? (gợi ý: `source_query`, `source_filter` trong config)
2. Vì sao raw phải được lưu trước khi parse?
3. `paper_id` được sinh thế nào và vì sao nó phải ổn định?
4. `text_for_embedding` gồm những gì, và vì sao chọn như vậy?
5. `top_k=4` nghĩa là gì, tăng lên 10 thì metric nào có khả năng đổi và đổi theo hướng nào?
6. Chỉ ra một câu hỏi **hit** và một câu hỏi **miss** trong `baseline_answers.json`, giải thích bằng `ground_truth_doc_ids` vs `retrieved_doc_ids`.
7. Khác nhau giữa data quality và data freshness? Cho một lỗi mà chỉ freshness bắt được.
8. Loại corruption nào làm metric tụt mạnh nhất? Vì sao là loại đó?
9. Có loại corruption nào metric **không** đổi không? Điều đó nói lên gì?
10. Repair được thực hiện thế nào, và làm sao chứng minh nó không phải copy baseline?
11. `judge_accuracy` của nhóm là judge thật hay fallback heuristic? Kiểm bằng cách nào?

---

## Bản đồ lý thuyết → file code

| Khái niệm | File |
| --- | --- |
| Path, settings, ngưỡng, tên collection | `src/core/config.py` |
| Ingestion + raw snapshot | `src/ingestion/crossref.py` |
| Cleaning & schema | `src/ingestion/cleaning.py` |
| Corruption có chủ đích | `src/ingestion/corruption.py` |
| Embedding | `src/retrieval/embeddings.py` |
| Vector store, search, lookup | `src/retrieval/index.py` |
| LLM đa provider | `src/retrieval/llm.py` |
| QA / agent | `src/retrieval/qa.py`, `src/retrieval/agent.py` |
| Test set | `src/evaluation/testset.py` |
| Metrics + judge + Ragas | `src/evaluation/metrics.py` |
| Quality & freshness | `src/observability/quality.py` |
| Markdown reports | `src/observability/reporting.py` |
| Điều phối 2 luồng | `src/pipelines/phase1.py`, `src/pipelines/corruption_flow.py` |
