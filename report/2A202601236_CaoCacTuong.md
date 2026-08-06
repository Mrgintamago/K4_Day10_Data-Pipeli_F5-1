# Member Role Report - Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Cao Các Tường |
| MSSV | 2A202601236 |
| Khóa/Lớp | K4 |
| Tên nhóm | F5-1 |
| Vai trò chính | DATA - nguồn dữ liệu, raw ingestion và repair từ raw (T2, T10) |
| Repository | `K4_Day10_Data-Pipeli_F5-1` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| T2 - Fetch, parse và load raw | `src/ingestion/crossref.py`: `parse_crossref_payload`, `fetch_source_records`, `load_raw_records`; `tests/test_crossref.py` | Crossref REST payload và `Settings` | `data/raw/crossref_response.json`, `data/raw/crossref_records.json`, danh sách `PaperRecord` | Hoàn thành, merged qua PR #1 |
| T10 - Repair và xác minh lineage | `load_raw_records`, `build_clean_dataframe`; đoạn repair tại `src/pipelines/corruption_flow.py:95-99` | Raw snapshot bất biến `data/raw/crossref_records.json` | `data/clean/papers_clean_repaired.csv`, `data/clean/papers_clean_repaired.json` | Hoàn thành, commit `9c8bb30` |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Kiểm tra dữ liệu nguồn trước handoff | TV2 - cleaning, test set; TV3 - quality | Phát hiện `categories` rỗng ở 24/24 raw record do Crossref không trả `subject`; thống nhất coi categories là optional và không tạo câu hỏi category |
| Xác minh dữ liệu repair cho tích hợp | TV4 - T11 corruption flow | Bàn giao repaired CSV/JSON gồm 24 dòng, 24 ID duy nhất, khớp baseline và sẵn sàng tạo index `papers-repaired` |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Chuẩn hóa payload Crossref thành schema ổn định | `src/ingestion/crossref.py`, `data/raw/crossref_records.json` | 24 `PaperRecord`; DOI được chuẩn hóa thành `paper_id`; 0 ID rỗng, 0 ID trùng | `tests/test_crossref.py`; kiểm artifact raw |
| Bảo toàn raw response và hỗ trợ retry API | `fetch_source_records` | Lưu response trước khi parse; retry các mã 429/5xx; raw snapshot đọc ngược lại được | 6/6 unit test pass, bao gồm retry và parse failure |
| Tái tạo clean data từ raw | `data/clean/papers_clean_repaired.csv`, `data/clean/papers_clean_repaired.json` | 24 dòng, đủ 10 cột, 24 ID duy nhất; không còn duplicate, noise, blank hoặc stale do corruption | So tập ID raw/baseline/repaired và parse JSON strict |
| Xác minh recovery end-to-end | `data/results/repaired_metrics.json`, `data/quality/quality_repaired.json` | Quality pass, freshness pass; bốn metric repaired khớp baseline | `data/reports/corruption_report.md` |

Output cụ thể của tôi là raw snapshot có thể tái sử dụng và hai file repaired được tái tạo từ raw. Raw có SHA-256 `94925723AC99BCC2443ECF5A48A2429450B2A9C2F884A2108562676218EF408F`; checksum không đổi trong quá trình corruption/repair.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Crossref là API sống nên kết quả có thể thay đổi theo thời điểm hoặc lỗi tạm thời. Pipeline cần lưu bằng chứng nguồn trước khi parse, tạo `paper_id` ổn định và đọc lại snapshot mà không gọi mạng. Khi dữ liệu clean bị corruption, pipeline cũng phải chứng minh có thể phục hồi từ nguồn raw thay vì sao chép bản baseline đã lưu.

### Cách triển khai

Ở T2, tôi kiểm tra cấu trúc `message.items`, bỏ item không hợp lệ hoặc DOI trùng, chuẩn hóa DOI về chữ thường, làm sạch markup trong abstract, ghép tên tác giả, lấy ngày xuất bản và URL PDF. `fetch_source_records` retry tối đa bốn lần cho lỗi mạng, 429 và 5xx, có exponential backoff hoặc tôn trọng `Retry-After`. Response API được ghi ra đĩa trước khi parse để vẫn giữ được bằng chứng khi schema nguồn lỗi. `load_raw_records` dựng lại `PaperRecord` và kiểm tra schema, ID, title, authors và categories.

Ở T10, tôi không dùng corrupted data làm input và không copy `papers_clean.csv`. Tôi đọc `crossref_records.json` bằng `load_raw_records`, chạy lại `build_clean_dataframe(records, now_utc())`, sau đó ghi ra hai path repaired riêng. Lineage được xác minh bằng checksum raw, tập `paper_id`, schema, tính duy nhất và phép so sánh repaired với baseline.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Crossref JSON payload cho T2; raw snapshot gồm các trường của `PaperRecord` cho T10 |
| Output | Raw API response, raw record snapshot; repaired CSV/JSON với 10 cột clean bắt buộc |
| Module phụ thuộc | `src/core/config.py`, `src/core/utils.py`, `src/ingestion/cleaning.py` |
| Module sử dụng output | Cleaning/test-set/quality ở pha 1; `src/pipelines/corruption_flow.py` và index `papers-repaired` ở pha 2 |
| Điều kiện lỗi cần xử lý | HTTP timeout/429/5xx, payload thiếu `message.items`, DOI/title rỗng, record trùng, raw schema không hợp lệ |

### Cách xác minh

```powershell
.\.venv\Scripts\python.exe -c "import sys, unittest; sys.path.insert(0, 'src'); suite=unittest.defaultTestLoader.discover('tests', pattern='test_crossref.py'); result=unittest.TextTestRunner(verbosity=2).run(suite); raise SystemExit(not result.wasSuccessful())"
Get-FileHash data/raw/crossref_records.json -Algorithm SHA256
```

- **Kết quả mong đợi:** 6 test Crossref pass; raw đọc lại được; raw/baseline/repaired có cùng 24 ID; repaired JSON hợp lệ và không có dấu vết corruption.
- **Kết quả thực tế:** 6/6 test pass trong 0.104 giây; lineage check pass với 24 dòng và 24 ID duy nhất; repaired khớp baseline.
- **Artifact/log:** `data/raw/crossref_records.json`, `data/clean/papers_clean_repaired.*`, `data/reports/corruption_report.md`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Cần chọn cách phục hồi sau corruption nhưng vẫn chứng minh được khả năng tái tạo của data pipeline.
- **Các phương án đã cân nhắc:** Copy `papers_clean.csv` baseline; gọi lại Crossref API; hoặc chạy lại cleaning từ raw snapshot đã khóa.
- **Phương án đã chọn:** Chạy `load_raw_records` và `build_clean_dataframe` từ `data/raw/crossref_records.json`.
- **Lý do:** Copy baseline chỉ là khôi phục backup, không chứng minh lineage. Gọi lại API làm thay đổi corpus và khiến so sánh ba trạng thái không công bằng. Raw snapshot vừa tái lập được vừa giữ nguyên nguồn cho cùng test set.
- **Bằng chứng quyết định phù hợp:** Raw checksum không đổi; raw/baseline/repaired cùng 24 ID; quality repaired pass; bốn metric repaired trở về đúng baseline.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `Author identity unknown` và `fatal: unable to auto-detect email address` khi commit T10.
- **Lệnh hoặc bước tái hiện:** Chạy `git commit` khi máy chưa cấu hình `user.name` và `user.email`.
- **Nguyên nhân gốc:** Git không có danh tính author/committer ở local hoặc global config.
- **Cách xử lý:** Truyền identity chỉ cho lệnh commit bằng `git -c user.name="tuon10282" -c user.email="tuongcao24@gmail.com" commit -m "T10: rebuild repaired data from raw"`, không thay đổi config toàn máy.
- **Cách xác minh sau khi sửa:** Commit `9c8bb30` được tạo và push lên `origin/main`; `git show -s --format="%an <%ae>" 9c8bb30` trả đúng danh tính.
- **Điều học được:** Lỗi công cụ quản lý phiên bản không làm mất staged changes; cần kiểm `git status`, chỉ commit file thuộc task và tránh sửa global config trên máy dùng chung.

## 7. Hiểu biết về luồng end-to-end

1. Crossref trả payload JSON. T2 lưu raw response, parse thành `PaperRecord` và lưu raw snapshot. T3 làm sạch thành dataframe 10 cột và tạo `text_for_embedding`. Model MiniLM biến text thành vector 384 chiều, sau đó Chroma lưu vector cùng metadata trong collection riêng cho từng trạng thái.
2. Mỗi mẫu evaluation chứa câu hỏi, đáp án chuẩn và `ground_truth_doc_ids`. Retriever lấy top 4 ID; retrieval hit khi danh sách lấy về giao với ground truth. Câu trả lời tiếp tục được đo bằng token F1 và judge, nên retrieval đúng chưa chắc answer đã đúng.
3. Quality checks kiểm schema và tính hợp lệ như cột bắt buộc, ID null/trùng, title/summary. Freshness tập trung vào tuổi dữ liệu so với ngưỡng 180 ngày, ngày lỗi và số dòng stale. Một dataset có thể đúng schema nhưng đã quá cũ.
4. Baseline, corrupted và repaired phải dùng cùng 73 câu hỏi, `top_k=4`, evaluator và model. Nếu đổi test set hay cấu hình, delta không còn quy được cho chất lượng dữ liệu.
5. Repair thành công khi repaired được sinh từ raw, khôi phục 24 ID duy nhất, quality/freshness pass và metric trở về baseline. Artifact hiện tại đáp ứng đủ các điều kiện đó.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét của cá nhân |
| --- | ---: | ---: | ---: | --- |
| `retrieval_hit_rate` | 1.0000 | 0.7397 | 1.0000 | Corruption làm giảm 0.2603; repair phục hồi hoàn toàn |
| `mean_token_f1` | 0.9206 | 0.2686 | 0.9206 | Giảm 0.6519, cho thấy nội dung trả lời chịu ảnh hưởng mạnh hơn retrieval hit |
| `judge_accuracy` | 0.9178 | 0.2603 | 0.9178 | Giảm 0.6575 và trở lại baseline sau repair |
| `mean_judge_score` | 4.6712 | 2.0411 | 4.6712 | Giảm 2.6301 điểm và phục hồi hoàn toàn |
| Quality checks | Pass, 0 lỗi | Fail: ID unique, summary, freshness | Pass, 0 lỗi | Các check bắt đúng duplicate, blank summary và stale date |
| Freshness status | Fresh, 0 stale | Not fresh, 22 stale | Fresh, 0 stale | Repair khôi phục ngày từ raw snapshot |

### Kết luận từ số liệu

1. Corruption làm mất 5 record mới nhất, tạo 3 duplicate, để 3 summary rỗng và đẩy ngày lùi 5 năm -> quality fail ba check và freshness ghi nhận 22 stale rows -> retrieval hit giảm từ 1.0000 xuống 0.7397, judge accuracy giảm từ 0.9178 xuống 0.2603.
2. Repair chạy lại cleaning từ raw -> khôi phục 24 ID duy nhất, 0 summary rỗng, 0 stale row và quality pass -> cả bốn metric repaired bằng baseline.

Không thể kết luận một corruption riêng lẻ ảnh hưởng mạnh nhất vì T9 áp dụng sáu loại lỗi trong cùng một lần chạy, không có ablation theo từng loại. Dựa trên cơ chế, việc drop record có thể trực tiếp làm retrieval miss, còn blank/noise/truncate làm suy yếu embedding và câu trả lời; nhưng đây là giải thích, không phải kết luận nhân quả riêng lẻ từ artifact hiện tại.

Kết quả đáng chú ý là retrieval hit vẫn đạt 0.7397 trong khi token F1 và judge accuracy chỉ khoảng 0.26. Điều này cho thấy một ground-truth document vẫn có thể xuất hiện trong top 4, nhưng nội dung đã bị truncate, blank hoặc noise nên answer quality giảm mạnh. Tôi kiểm tra giả thuyết này bằng cách đối chiếu delta retrieval với hai metric answer trong `corruption_report.md`.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Raw snapshot bất biến là nền tảng cho lineage, reproducibility và recovery; chỉ giữ clean output là chưa đủ.
2. Data quality phải phản ánh đặc điểm nguồn: `categories` rỗng ở toàn bộ Crossref sample là giới hạn nguồn, không nên đặt check bắt buộc gây false failure.
3. RAG có thể còn retrieval hit nhưng trả lời kém nếu nội dung document bị hỏng; vì vậy phải theo dõi đồng thời data signals, retrieval metric và answer metric.

### Nếu có thêm thời gian

Tôi sẽ bổ sung một kiểm tra lineage tự động cho T10: ghi checksum raw trước/sau, assert tập ID và schema, sau đó chạy từng loại corruption độc lập. Ablation này giúp định lượng loại lỗi nào làm giảm retrieval và answer metric nhiều nhất thay vì chỉ suy luận từ một kịch bản gộp.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi "đã chạy thành công" cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Cao Các Tường

**Ngày xác nhận:** 2026-08-06
