# Báo cáo cá nhân — Day 10: Data Pipeline & Data Observability

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
|---|---|
| Họ và tên | Trần Quang Sáng |
| MSSV | 2A202601446 |
| Khóa/Lớp | K4 |
| Tên nhóm | K4 chiều 06/08/2026 |
| Vai trò chính | Quality, freshness và baseline/comparison report (T5, T8, T12) |
| Repository | `K4_Day10_Data-Pipeli_F5-1` |
| Ngày hoàn thành | 2026-08-06 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Deliverable | File/hàm phụ trách | Input | Output | Trạng thái |
|---|---|---|---|---|
| Data quality checks | `src/observability/quality.py` — `run_data_quality_checks` | Clean dataframe | `quality_baseline.json`, quality reports theo state | Hoàn thành |
| Freshness monitoring | `src/observability/quality.py` — `build_freshness_report` | Clean/corrupted/repaired dataframe | Freshness JSON cho từng state | Hoàn thành |
| Baseline report (T8) | `src/observability/reporting.py` — `generate_phase1_report` | Source summary, metrics, quality, freshness | `data/reports/phase1_report.md` | Hoàn thành |
| Comparison report (T12) | `src/observability/reporting.py` — `generate_corruption_report` | Ba bộ metrics, quality và freshness | `data/reports/corruption_report.md` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

- Chạy lại hai entrypoint sau khi các module được tích hợp:
  `script/run_phase1.py` và `script/run_corruption_flow.py`.
- Đối chiếu số liệu trong Markdown report với các JSON artifact, kiểm tra rằng ba trạng thái dùng chung 73 câu hỏi và cùng cấu hình đánh giá.
- Xử lý khác biệt khi chạy bằng `.venv`: bổ sung `PYTHONPATH=src` để entrypoint import được các package trong `src/`.

## 3. Kết quả theo vai trò

| Nhiệm vụ | File/hàm/artifact | Kết quả | Cách xác minh |
|---|---|---|---|
| Chạy quality baseline | `data/quality/quality_baseline.json` | `overall_pass: true`, 7 check pass trên 24 rows | `uv run python script/run_phase1.py` |
| Tạo freshness baseline | `data/quality/freshness_report.json` | `is_fresh: true`, 0 stale rows | Đọc JSON freshness artifact |
| Tạo baseline report | `data/reports/phase1_report.md` | Report khớp metrics/quality/freshness JSON | Đối chiếu các giá trị trong report |
| Tạo comparison report | `data/reports/corruption_report.md` | Có bảng baseline/corrupted/repaired và delta | `script/run_corruption_flow.py` |
| Đánh giá tác động corruption | `data/results/*_metrics.json` | Corrupted giảm rõ rệt, repaired trở về baseline | So sánh cùng test set 73 samples |

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Pipeline không chỉ cần chạy được mà còn phải phát hiện dữ liệu kém chất lượng trước khi dữ liệu đi vào RAG agent. Vì vậy cần tách hai loại tín hiệu:

- Quality kiểm tra schema và tính hợp lệ của bản ghi, như cột bắt buộc, `paper_id`, title, summary và duplicate.
- Freshness kiểm tra ngày xuất bản, số dòng stale và ngày không hợp lệ theo ngưỡng 180 ngày.

Sau đó các tín hiệu này được đưa vào baseline report và comparison report để liên hệ thay đổi dữ liệu với thay đổi chất lượng agent.

### Cách triển khai

`generate_phase1_report` nhận `source_summary`, metrics, quality và freshness từ pipeline rồi dựng Markdown từ chính các payload đó. Hàm không tự tính lại số liệu, giúp report không bị lệch với JSON nguồn.

`generate_corruption_report` tạo bảng ba trạng thái, tính delta của các metric số so với baseline, đồng thời ghi quality/freshness của corrupted và repaired. Report chỉ trình bày delta quan sát được, không tự khẳng định recovery nếu số liệu không chứng minh điều đó.

Quality và freshness được chạy riêng cho baseline, corrupted và repaired. Repair trong flow được tạo lại bằng cách đọc raw records và chạy lại cleaning, không copy clean baseline.

### Input, output và contract

| Thành phần | Mô tả |
|---|---|
| Input baseline | `data/clean/papers_clean.csv`, `baseline_metrics.json` và các payload quality/freshness |
| Input comparison | `baseline_metrics.json`, `corrupted_metrics.json`, `repaired_metrics.json` cùng quality/freshness tương ứng |
| Output baseline | `data/reports/phase1_report.md` |
| Output comparison | `data/reports/corruption_report.md` |
| Cấu hình chung | 73 test samples, embedding `all-MiniLM-L6-v2`, `top_k=4` |
| Điều kiện lỗi | Thiếu baseline artifact phải dừng trước; thiếu credential LLM phải báo lỗi cấu hình |

### Cách xác minh

```powershell
$env:PYTHONPATH="src"
.venv\Scripts\python.exe script\run_phase1.py
.venv\Scripts\python.exe script\run_corruption_flow.py
Get-Content data\reports\phase1_report.md
Get-Content data\reports\corruption_report.md
```

- Baseline thực tế: 24 raw records, 24 clean rows, 73 test samples.
- Corrupted thực tế: 22 rows, quality fail và 22 stale rows.
- Repaired thực tế: 24 rows, quality pass và 0 stale rows.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** cần so sánh công bằng baseline, corrupted và repaired.
- **Các phương án:** sinh lại test set cho từng state; hoặc giữ cố định một test set và chỉ thay đổi corpus/index.
- **Lựa chọn:** giữ nguyên `data/eval/test_set.json` với 73 samples cho cả ba state.
- **Lý do:** nếu test set thay đổi, metric không còn phản ánh riêng tác động của data corruption. Giữ nguyên test set giúp attribution rõ ràng và tái lập được.
- **Bằng chứng:** cả ba metrics artifact đều ghi `samples: 73`; baseline và repaired có cùng các metric, trong khi corrupted giảm mạnh.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng:** chạy `uv run python script/run_phase1.py` bị lỗi quyền ghi cache tại `C:\Users\Admin\AppData\Local\uv\cache`.
- **Nguyên nhân:** `uv` không được phép khởi tạo cache trong môi trường hiện tại.
- **Cách xử lý:** dùng Python đã cài trong `.venv` và đặt `PYTHONPATH=src` để import đúng package của project.
- **Lỗi phụ khi chạy trực tiếp:** `.venv\Scripts\python.exe script\run_phase1.py` thiếu `PYTHONPATH`, dẫn tới `ModuleNotFoundError: No module named 'pipelines'`.
- **Xác minh sau khi xử lý:** baseline chạy đủ 7/7 bước trong 100.9 giây; corruption flow chạy đủ 5/5 bước trong 82.6 giây và tạo comparison report.
- **Điều học được:** entrypoint của project phụ thuộc vào package layout `src`; khi không dùng `uv`, cần tái tạo điều kiện import tương đương bằng `PYTHONPATH`.

## 7. Hiểu biết về luồng end-to-end

1. Crossref cung cấp raw response và raw records. Cleaning chuẩn hóa records thành clean dataframe, bổ sung các trường như `text_for_embedding`, `age_days` và document ID. Embedding model tạo vector, sau đó ChromaDB lưu index để semantic search.
2. Evaluation set chứa câu hỏi, ground truth và `ground_truth_doc_ids`. Retrieval được tính là hit khi document ID đúng xuất hiện trong top-k; answer metrics so sánh câu trả lời với ground truth.
3. Quality checks tập trung vào tính hợp lệ và đầy đủ của dữ liệu hiện tại. Freshness monitoring tập trung vào tuổi dữ liệu, ngày không hợp lệ và số record vượt ngưỡng stale.
4. Dùng cùng test set giúp khác biệt giữa ba state đến từ corpus/data quality, không phải do câu hỏi hoặc ground truth thay đổi.
5. Repair được xem là có hiệu quả khi repaired quality/freshness trở lại trạng thái tốt và các metrics agent phục hồi gần hoặc bằng baseline. Trong lần chạy này repaired khớp baseline ở các metric chính.

## 8. Phân tích kết quả

### Metrics chính

| Metric/signal | Baseline | Corrupted | Repaired | Nhận xét |
|---|---:|---:|---:|---|
| `retrieval_hit_rate` | 1.0000 | 0.7397 | 1.0000 | Corruption làm mất 26.03 điểm phần trăm; repair phục hồi hoàn toàn. |
| `mean_token_f1` | 0.9206 | 0.2686 | 0.9206 | Chất lượng câu trả lời giảm mạnh khi summary/title/index bị phá. |
| `judge_accuracy` | 0.9178 | 0.2603 | 0.9178 | Kết quả judge giảm tương ứng với degradation của answer quality. |
| `mean_judge_score` | 4.6712 | 2.0411 | 4.6712 | Điểm trung bình giảm 2.6301 điểm ở corrupted. |
| Quality checks | Pass | Fail | Pass | Corrupted fail `paper_id_unique`, `summary_length`, `freshness`. |
| Freshness status | Fresh | Not fresh | Fresh | Corrupted có 22 stale rows; repaired có 0. |

### Kết luận từ số liệu

1. **Corruption → quality/freshness signal → agent metric:** corruption làm dataset còn 22 rows và tạo duplicate, summary không đạt độ dài, dữ liệu stale. Cùng lúc đó, retrieval hit rate giảm từ `1.0000` xuống `0.7397`, mean token F1 từ `0.9206` xuống `0.2686`, judge accuracy từ `0.9178` xuống `0.2603`.
2. **Repair → quality/freshness phục hồi → agent metric phục hồi:** repaired được dựng lại từ raw records, có 24 rows, quality pass, freshness true và 0 stale rows. Các metric repaired trở lại đúng bằng baseline trong lần chạy này.

Corruption ảnh hưởng rõ nhất là các thay đổi làm hỏng nội dung dùng cho embedding/retrieval, thể hiện qua đồng thời ba chỉ số agent giảm mạnh. Quality report giúp xác nhận đây không chỉ là biến động metric mà có tín hiệu dữ liệu tương ứng.

Điểm đáng chú ý là corrupted vẫn đạt retrieval hit rate `0.7397`, không giảm về 0; điều này phù hợp với việc corruption chỉ tác động một phần corpus. Vì vậy cần xem đồng thời quality signals và nhiều metric thay vì kết luận từ một chỉ số duy nhất.

## 9. Điều học được và hướng cải thiện

### Ba điều quan trọng nhất

1. Data quality phải được kiểm tra ngay sau cleaning và trước indexing; lỗi dữ liệu có thể lan trực tiếp sang chất lượng RAG.
2. Quality và freshness là hai tín hiệu khác nhau nhưng bổ trợ: một bản ghi có thể đúng schema nhưng đã quá cũ, hoặc mới nhưng bị duplicate/thiếu nội dung.
3. Comparison report có giá trị nhất khi ba trạng thái dùng cùng test set, cùng `top_k`, cùng evaluator và có artifact lineage rõ ràng.

### Nếu có thêm thời gian

Có thể bổ sung test tự động cho `generate_phase1_report` và `generate_corruption_report`: đọc JSON fixture, sinh report vào thư mục tạm, rồi kiểm tra các metric quan trọng xuất hiện đúng định dạng. Ngoài ra có thể thêm hash hoặc run ID vào report để truy vết chính xác phiên bản raw/clean/index đã dùng.

## 10. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Mọi kết luận về kết quả đều có artifact hoặc metric để đối chiếu.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không sao chép nguyên văn báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Trần Quang Sáng  
**Ngày xác nhận:** 2026-08-06
