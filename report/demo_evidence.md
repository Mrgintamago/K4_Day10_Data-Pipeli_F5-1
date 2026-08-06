# Demo evidence — baseline RAG

Nguồn phân tích: `data/results/baseline_answers.json` (73 mẫu).

## Phân bố kết quả theo loại câu hỏi

| Question type | Số câu | Hit rate | Mean token F1 | Mean judge score |
|---|---:|---:|---:|---:|
| `authors` | 24 | 1.000 | 0.000 | 1.000 |
| `date` | 24 | 1.000 | 0.917 | 4.708 |
| `retrieval` | 1 | 1.000 | 0.162 | 2.000 |
| `summary` | 24 | 1.000 | 0.960 | 4.542 |

Hit rate tổng thể bằng **1.0** vì corpus chỉ có 24 tài liệu và mỗi câu lấy `top_k=4`; điều này cho xác suất phủ tài liệu đúng khá cao, không có nghĩa retrieval hoàn hảo tuyệt đối. Chỉ số hit chỉ yêu cầu ít nhất một `ground_truth_doc_id` xuất hiện trong danh sách retrieve, không đánh giá thứ hạng, mức liên quan của ba tài liệu còn lại hay chất lượng câu trả lời.

## Ví dụ A — retrieval hit, câu trả lời đúng

- **Question:** What is the summary of the paper titled "SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation"?
- **Ground truth:** Summary In high-risk industrial settings, leveraging large language models (LLMs) for automated accident analysis and generating safety reports has emerged as an efficient workflow.
- **Answer:** Summary In high-risk industrial settings, leveraging large language models (LLMs) for automated accident analysis and generating safety reports has emerged as an efficient workflow.
- **Ground-truth doc IDs:** `10.2118/234689-pa`
- **Retrieved doc IDs:** `10.2118/234689-pa`, `10.20944/preprints202604.0339.v1`, `10.55041/isjem07213`, `10.21203/rs.3.rs-9770645/v1`
- **Kết quả:** retrieval hit = `true`, token F1 = `1.0`, judge score = `5`, judge correct = `true`.

Tài liệu đúng đứng đầu và answer trùng ground truth, nên retrieval hit đi cùng kết quả judge đúng trong ví dụ này.

## Ví dụ B — retrieval hit nhưng judge fail

- **Question:** Who are the authors of the paper titled "SafeRAG: A Large-Language-Model-Based Multistage Retrieval-Augmented Framework for Oil and Gas Safety Report Generation"?
- **Ground truth:** Qianwen Cao, Chiyu Zhang, Junxiong Ning, Gongru Li
- **Answer:** Summary In high-risk industrial settings, leveraging large language models (LLMs) for automated accident analysis and generating safety reports has emerged as an efficient workflow.
- **Ground-truth doc IDs:** `10.2118/234689-pa`
- **Retrieved doc IDs:** `10.2118/234689-pa`, `10.20944/preprints202604.0339.v1`, `10.55041/isjem07213`, `10.21203/rs.3.rs-9770645/v1`
- **Kết quả:** retrieval hit = `true`, token F1 = `0.0`, judge score = `1`, judge correct = `false`.

Retrieval vẫn hit vì tài liệu `10.2118/234689-pa` đứng đầu top 4. Tuy nhiên bước sinh trả về phần tóm tắt thay vì danh sách tác giả, nên câu trả lời không đáp ứng câu hỏi và judge chấm fail. Đây là minh chứng rõ rằng retrieval hit là điều kiện cần nhưng chưa đủ cho answer correctness.
