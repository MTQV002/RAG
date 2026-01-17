# 🔬 Đánh Giá Chi Tiết RAG vs Gemini - Hard Test Cases

> **5 Test Cases phức tạp** yêu cầu reasoning đa điều luật, tính toán, và phân tích pháp lý

---

## 📊 Tổng Quan 5 Cases

| ID | Category | RAG Latency | Gemini Latency | Winner |
|----|----------|:-----------:|:--------------:|:------:|
| TC_HARD_001 | Mang thai + độc hại | 5,836ms | 20,059ms | RAG (nhanh) |
| TC_HARD_002 | Sáp nhập + trợ cấp | 5,556ms | 20,079ms | RAG (nhanh) |
| TC_HARD_003 | Lương đêm ngày lễ | 5,972ms | 17,403ms | RAG (nhanh) |
| TC_HARD_004 | Lao động 17 tuổi | 5,480ms | 19,138ms | RAG (nhanh) |RAG
| TC_HARD_005 | Sa thải trái luật | 6,136ms | ❌ Error | RAG (stable) |
| TC_HARD_006 | Thai sản sinh đôi | 42,840ms | 18,052ms | Gemini (nhanh) |

---

## 🔍 Chi Tiết Từng Case

---

### TC_HARD_001: Lao động nữ mang thai + môi trường độc hại

**Câu hỏi:** (4 sub-questions)
1. Công ty có được sa thải không?
2. Tự nghỉ cần báo trước không?
3. Đủ điều kiện nghỉ hưu sớm không?
4. Chế độ thai sản từ BHXH?

#### RAG Retrieved:
`137 BLLĐ, 139 BLLĐ, 35 BLLĐ, 55 BHXH, 54 BHXH, 53 BHXH, 61 BHXH`

| Câu | RAG | Gemini | Đánh giá |
|-----|-----|--------|:--------:|
| (1) Sa thải | ✅ Không (Đ137) | ✅ Không (Đ37.3) | TIE - cả 2 đúng |
| (2) Báo trước | ⚠️ "Cần 45 ngày" | ✅ "Có thể không cần" (Đ35.3.d) | **Gemini** đúng hơn |
| (3) Nghỉ hưu sớm | ⚠️ "Không đủ thông tin" | ✅ "Đủ điều kiện" + NĐ135 | **Gemini** đầy đủ hơn |
| (4) Chế độ BHXH | ✅ Đ139, Đ53, Đ54 | ✅ Đ32, 34, 38, 39 + trợ cấp 1 lần | TIE |

**📌 Nhận xét:**
- RAG thiếu Điều 37 (trọng tâm) nhưng có Điều 137 (tương đương)
- RAG không tận dụng context về độc hại để kết luận nghỉ hưu sớm
- Gemini cite nhiều điều hơn và reasoning rõ hơn

**🏆 Winner: Gemini** (3/4 câu đầy đủ hơn)

---

### TC_HARD_002: Trợ cấp khi công ty sáp nhập

**Câu hỏi:** Tính trợ cấp từ công ty + TCTN (10y4m làm việc, 8y BHTN, lương 20tr)

#### RAG Retrieved:
`46 BLLĐ, 38 VL, 34 VL, 35 VL, 39 VL, 48 BLLĐ, 43 BLLĐ`

| Tiêu chí | RAG | Gemini | Đánh giá |
|----------|-----|--------|:--------:|
| Loại trợ cấp | ❌ **Thôi việc** (Đ46) | ✅ **Mất việc làm** (Đ47) | **Gemini đúng** |
| Công thức | ❌ 0.5 tháng/năm × 10.33 năm | ✅ 1 tháng/năm × (10.5 - 8) năm | **Gemini đúng** |
| Kết quả | ❌ 103.3 triệu | ✅ **50 triệu** | **Gemini đúng** |
| Thời gian TCTN | ❌ 3 tháng | ✅ Đúng theo công thức | **Gemini** |

**📌 Phân tích lỗi RAG:**
1. **Retrieval sai:** Lấy Điều 46 (thôi việc) thay vì **Điều 47** (mất việc do sáp nhập)
2. **Không trừ BHTN:** Dùng 10.33 năm thay vì (10.5 - 8) = 2.5 năm
3. **Tính sai công thức:** Dùng 0.5 tháng/năm thay vì 1 tháng/năm

**🏆 Winner: Gemini** (đúng loại trợ cấp + tính đúng)

---

### TC_HARD_003: Lương làm đêm ngày lễ

**Câu hỏi:** Tính lương ca đêm 22h-6h ngày lễ (lương 10tr/26 ngày)

#### RAG Retrieved:
`98 BLLĐ, 57 ND145, 56 ND145, 106 BLLĐ, 55 ND145, 112 BLLĐ, 67 ND145`

| Tiêu chí | RAG | Gemini | Đánh giá |
|----------|-----|--------|:--------:|
| Công thức % | 300% + 30% + 20% = 350% | 300% + (20% × 300%) = 360% | **Gemini đúng** |
| Giải thích Đ98k3 | ⚠️ 20% lương gốc | ✅ 20% của tiền làm ngày lễ | **Gemini đúng** |
| Kết quả | ~1.35 triệu | ~1.38 triệu | **Gemini đúng** |
| Article coverage | 75% (3/4 điều) | 50% (2/4 điều) | **RAG** tốt hơn |

**📌 Phân tích:**
- RAG retrieve đúng các điều cần thiết
- Nhưng LLM hiểu sai Điều 98 khoản 3: "20% tiền lương... của ngày nghỉ lễ" → 20% × 300% = 60%, không phải 20% lương gốc

**🏆 Winner: Gemini** (tính đúng)

---

### TC_HARD_004: Lao động chưa thành niên 17 tuổi

**Câu hỏi:** Được làm việc không? Giờ làm? Ai ký HĐ? Làm đêm được không?

#### RAG Retrieved:
`146 BLLĐ, 107 BLLĐ, 108 BLLĐ, 137 BLLĐ, 105 BLLĐ, 160 BLLĐ, 145 BLLĐ`

| Câu | RAG | Gemini | Đánh giá |
|-----|-----|--------|:--------:|
| (1) Được làm? | ✅ Được (15-18 tuổi) | ✅ Được + Đ143 | TIE |
| (2) Giờ làm? | ✅ 8h/ngày, 40h/tuần | ✅ 8h/ngày, 40h/tuần | TIE |
| (3) Ai ký HĐ? | ⚠️ "Có thể tự ký" (mơ hồ) | ✅ "Tự ký + đồng ý của ĐDPL" (Đ18k3b) | **Gemini đúng** |
| (4) Làm đêm? | ⚠️ "Có thể theo danh mục" | ✅ "Không được" (trừ nghệ thuật) | **Gemini đúng** |

**📌 Phân tích lỗi RAG:**
- **Thiếu Điều 18** → Trả lời sai câu (3) về người ký hợp đồng
- **Thiếu Điều 143** → Không định nghĩa rõ lao động chưa thành niên
- Hiểu sai Điều 146k4 về làm đêm

**🏆 Winner: Gemini** (4/4 đúng vs RAG 2/4)

---

### TC_HARD_005: Sa thải trái pháp luật

**Câu hỏi:** Công ty sa thải vì "không hoàn thành công việc" nhưng không có quy chế

#### RAG Retrieved:
`36 BLLĐ, 41 BLLĐ, 35 BLLĐ, 12 ND12, 5 BLLĐ, 188 BLLĐ, 42 ND12`

| Câu | RAG | Gemini | Đánh giá |
|-----|-----|--------|:--------:|
| (1) Vi phạm? | ✅ Vi phạm Đ36k1 (cần quy chế) | ❌ API Error | **RAG** |
| (2) Bồi thường? | ✅ Đ41: nhận lại + lương + 2 tháng | ❌ | **RAG** |
| (3) Khởi kiện? | ✅ TAND huyện, 1 năm (Đ188) | ❌ | **RAG** |

**📌 Nhận xét:**
- RAG retrieval **rất tốt**: đúng Đ36, 41, 188
- Gemini bị API Error (overloaded)
- RAG trả lời đầy đủ cả 3 câu

**🏆 Winner: RAG** (100% vs 0%)

---

### TC_HARD_006: Thai sản sinh đôi

**Câu hỏi:** Nghỉ bao lâu? Tổng tiền bao nhiêu?

#### RAG Retrieved:
`139 BLLĐ, 53 BHXH, 55 BHXH, 54 BHXH, 61 BHXH, 51 BHXH, 141 BHXH`

| Tiêu chí | RAG | Gemini | Đánh giá |
|----------|-----|--------|:--------:|
| Thời gian nghỉ | ✅ 7 tháng | ✅ 7 tháng | TIE |
| Trợ cấp hàng tháng | ✅ 105 triệu | ✅ 105 triệu | TIE |
| Lương cơ sở | ❌ 1,490,000đ (cũ) | ⚠️ 1,800,000đ (2023) | Cả 2 sai (đúng: 2,340,000đ) |
| Trợ cấp 1 lần | ❌ 5.96 triệu | ⚠️ 7.2 triệu | Gemini gần đúng hơn |
| Tổng | ❌ 110.96 triệu | ⚠️ 112.2 triệu | **Gemini** gần hơn |

**📌 Nhận xét:**
- RAG thiếu Điều 34, 38 BHXH (trọng tâm)
- Cả 2 dùng lương cơ sở cũ (đúng là 2,340,000đ từ NĐ73/2024)
- Số đúng: 7 × 15tr + 2 × 2 × 2.34tr = 105 + 9.36 = **114.36 triệu**

**🏆 Winner: Gemini** (gần đúng hơn)

---

## 📈 Tổng Kết

### Điểm số chi tiết

| Case | RAG Retrieval | RAG Answer | Gemini Answer | Winner |
|------|:-------------:|:----------:|:-------------:|:------:|
| TC_001 | ⚠️ Thiếu Đ37 | 2/4 câu đúng | 4/4 câu đúng | **Gemini** |
| TC_002 | ❌ Đ46 thay vì Đ47 | ❌ Sai công thức | ✅ Đúng | **Gemini** |
| TC_003 | ✅ 3/4 điều | ⚠️ Sai 20% | ✅ Đúng 360% | **Gemini** |
| TC_004 | ⚠️ Thiếu Đ18, Đ143 | 2/4 câu đúng | 4/4 câu đúng | **Gemini** |
| TC_005 | ✅ Đúng | ✅ Đúng | ❌ Error | **RAG** |
| TC_006 | ⚠️ Thiếu Đ34, Đ38 | ⚠️ Lương cơ sở cũ | ⚠️ Gần đúng hơn | **Gemini** |

### Tổng điểm

| Metric | RAG | Gemini |
|--------|:---:|:------:|
| **Cases thắng** | 1/6 | **4/6** |
| **Reliability** | **100%** | 83% (1 error) |
| **Avg Latency** | **5,786ms** | 18,946ms |
| **Retrieval chính xác** | 50% | N/A |
| **Answer chính xác** | 40% | **70%** |

---

## 💡 Root Causes của RAG

| Vấn đề | Case | Root Cause | Giải pháp |
|--------|------|------------|-----------|
| Retrieval thiếu điều quan trọng | TC_002, TC_004 | top_k thấp + semantic gap | Tăng top_k, improve embedding |
| LLM reasoning sai | TC_002, TC_003 | Không hiểu rõ điều khoản phức tạp | Cải thiện prompt với hướng dẫn tính toán |
| Data cũ | TC_006 | Lương cơ sở chưa cập nhật | Thêm NĐ 73/2024 vào training data |
| Thiếu điều liên quan | TC_001 | Không retrieve Đ37 (bảo vệ mang thai) | Thêm keyword boosting hoặc reranker mạnh hơn |

---

## ✅ Recommendations

1. **Data Update:** Thêm NĐ 73/2024 về lương cơ sở 2,340,000đ
2. **Retrieval:** Tăng `VECTOR_TOP_K` từ 15 → 20 cho hard questions
3. **Prompt Engineering:** Thêm hướng dẫn tính toán vào `CONTEXT_PROMPT`:
   - Phân biệt Điều 46 vs Điều 47
   - Công thức trừ thời gian BHTN
   - Cách tính % lương đêm ngày lễ
4. **Condense Prompt:** Đã cải thiện để giữ keywords pháp lý quan trọng
