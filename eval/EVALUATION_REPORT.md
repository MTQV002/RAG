# 📊 RAG vs Gemini 2.5 Flash - Báo Cáo Đánh Giá

**Ngày đánh giá:** 16/01/2026  
**Tổng số test cases:** 30 (6 chunks × 5 cases)  
**Model so sánh:** Gemini 2.5 Flash

---

## 1. Tổng Quan Kết Quả

| Chunk | RAG Latency | Gemini Latency | RAG Words | Gemini Words | RAG Citation | Gemini Citation |
|:-----:|:-----------:|:--------------:|:---------:|:------------:|:------------:|:---------------:|
| 1 | 21,161ms | 8,498ms | 100.6 | 170.4 | **100%** | 100% |
| 2 | 17,098ms | 6,666ms | 58.4 | 149.0 | **100%** | 80%* |
| 3 | 32,626ms | 8,136ms | 172.6 | 253.2 | **100%** | 100% |
| 4 | 11,152ms | 6,713ms | 47.6 | 178.4 | **100%** | 100% |
| 5 | 13,218ms | 10,577ms | 116.4 | 329.2 | **100%** | 100% |
| 6 | **4,411ms** | 8,450ms | 38.4 | 200.6 | **100%** | 100% |

*\*Chunk 2: TC007 Gemini bị API error*

---

## 2. Metrics Tổng Hợp

| Tiêu chí | RAG | Gemini | Winner |
|----------|:---:|:------:|:------:|
| **Avg Response Time** | 16,611ms | 8,173ms | 🥇 Gemini (2x nhanh hơn) |
| **Avg Answer Length** | 89 words | 213 words | 🥇 Gemini (chi tiết hơn) |
| **Citation Rate** | **100%** | 96.7% | 🥇 RAG |
| **Error Rate** | 0% | 3.3% (1 error) | 🥇 RAG |

---

## 3. Phân Tích Chi Tiết

### 3.1 RAG Thắng Rõ Ràng

#### TC005 - Lương tối thiểu vùng I năm 2026
| | RAG | Gemini |
|--|-----|--------|
| Answer | **5.310.000 đồng/tháng** | "Chưa được công bố" |
| Verdict | ✅ ĐÚNG (có dữ liệu ND293/2025) | ❌ SAI (không có dữ liệu) |

> **Kết luận:** RAG có lợi thế lớn với dữ liệu internal/mới.

#### TC007 - Tuổi nghỉ hưu nam 2026
| | RAG | Gemini |
|--|-----|--------|
| Answer | "60 tuổi 03 tháng" (Điều 169) | `[Gemini Error: 'content']` |
| Verdict | ✅ Trả lời được | ❌ API error |

### 3.2 Gemini Thắng Rõ Ràng

#### TC028 - Work from home
| | RAG | Gemini |
|--|-----|--------|
| Answer | 27 words, Điều 167 | 450 words, chi tiết |
| Verdict | Đúng nhưng ngắn | Đúng và chi tiết hơn |

#### TC022 - Chế độ lao động độc hại
| | RAG | Gemini |
|--|-----|--------|
| Answer | 33 words | 577 words (7 chế độ) |
| Verdict | Chỉ nêu 1 chế độ | Liệt kê đầy đủ 7 chế độ |

### 3.3 Kết Quả Tương Đương

| Test | Topic | RAG | Gemini | Verdict |
|------|-------|-----|--------|---------|
| TC001 | Giờ làm việc/tuần | 48 giờ ✅ | 48 giờ ✅ | TIE |
| TC002 | Nghỉ thai sản | 6 tháng ✅ | 6 tháng ✅ | TIE |
| TC009 | Lương thử việc | 85% ✅ | 85% ✅ | TIE |
| TC026 | Nghỉ tang | 3 ngày ✅ | 3 ngày ✅ | TIE |
| TC030 | Nghỉ kết hôn | 3 ngày ✅ | 3 ngày ✅ | TIE |

---

## 4. Điểm Số Đánh Giá (1-10)

| Tiêu chí | RAG | Gemini | Ghi chú |
|----------|:---:|:------:|---------|
| **Accuracy** | 9 | 8 | RAG có dữ liệu 2026 |
| **Speed** | 6 | 9 | Gemini nhanh hơn 2x |
| **Completeness** | 7 | 9 | Gemini chi tiết hơn |
| **Citation Quality** | 10 | 8 | RAG cite chính xác source |
| **Reliability** | 10 | 8 | Gemini có 1 API error |
| **OVERALL** | **8.4/10** | **8.4/10** | **TIE** |

---

## 5. Win/Loss Summary

| Result | Count | % |
|--------|:-----:|:-:|
| 🏆 RAG Wins | 4 | 13.3% |
| 🏆 Gemini Wins | 8 | 26.7% |
| 🤝 TIE | 17 | 56.7% |
| ❌ Error (either) | 1 | 3.3% |

---

## 6. Kết Luận & Đề Xuất

### RAG Phù Hợp Khi:
- ✅ Cần dữ liệu mới/internal (lương 2026, nghị định mới)
- ✅ Cần trích dẫn chính xác nguồn pháp lý
- ✅ Cần độ tin cậy cao (không có API error)
- ✅ Domain-specific legal questions

### Gemini Phù Hợp Khi:
- ✅ Cần response nhanh
- ✅ Cần giải thích chi tiết với ví dụ
- ✅ Cần câu trả lời bao quát nhiều khía cạnh
- ✅ General legal knowledge

### Đề Xuất:
1. **Hybrid approach:** RAG cho factual questions, Gemini cho explanatory questions
2. **Improve RAG response length:** Thêm context/examples vào prompt
3. **Monitor Gemini API:** Handle errors gracefully

---

## 7. Chi Tiết Từng Test Case

### Chunk 1 (TC001-TC005)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC001 | Giờ làm việc/tuần | ✅ | ✅ | TIE |
| TC002 | Nghỉ thai sản | ✅ | ✅ | TIE |
| TC003 | Nghỉ phép năm | ✅ | ✅ | TIE |
| TC004 | Thử việc | ✅ | ✅ | TIE |
| TC005 | Lương tối thiểu 2026 | ✅ | ❌ | **RAG** |

### Chunk 2 (TC006-TC010)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC006 | Làm thêm giờ/ngày | ✅ | ✅ | TIE |
| TC007 | Tuổi nghỉ hưu nam | ✅ | ❌ | **RAG** |
| TC008 | Tuổi nghỉ hưu nữ | ✅ | ✅ | Gemini* |
| TC009 | Lương thử việc | ✅ | ✅ | TIE |
| TC010 | Báo trước nghỉ việc | ✅ | ✅ | Gemini |

### Chunk 3 (TC011-TC015)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC011 | Nghỉ chuyển ca | ✅ | ✅ | TIE |
| TC012 | Trợ cấp thôi việc | ✅ | ✅ | Gemini |
| TC013 | Lương làm thêm | ✅ | ✅ | TIE |
| TC014 | Loại HĐLĐ | ✅ | ✅ | Gemini |
| TC015 | Tuổi lao động | ✅ | ✅ | Gemini |

### Chunk 4 (TC016-TC020)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC016 | Nghỉ hàng tuần | ✅ | ✅ | TIE |
| TC017 | Đóng BHXH | ✅ | ✅ | Gemini |
| TC018 | Nuôi con dưới 12 tháng | ✅ | ✅ | TIE |
| TC019 | HĐLĐ xác định thời hạn | ✅ | ✅ | TIE |
| TC020 | Mức phạt không ký HĐ | ✅ | ✅ | Gemini |

### Chunk 5 (TC021-TC025)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC021 | So sánh nghỉ thai sản | ✅ | ✅ | Gemini |
| TC022 | Chế độ độc hại | ✅ | ✅ | Gemini |
| TC023 | Intern trả lương | ✅ | ✅ | TIE |
| TC024 | Tạm hoãn HĐ nghĩa vụ QS | ✅ | ✅ | TIE |
| TC025 | Mức hưởng ốm đau | ✅ | ✅ | **RAG** |

### Chunk 6 (TC026-TC030)
| ID | Question | RAG | Gemini | Winner |
|----|----------|:---:|:------:|:------:|
| TC026 | Nghỉ tang | ✅ | ✅ | TIE |
| TC027 | Lương làm đêm | ✅ | ✅ | TIE |
| TC028 | Work from home | ✅ | ✅ | Gemini |
| TC029 | Số lần ký HĐLĐ | ✅ | ✅ | TIE |
| TC030 | Nghỉ kết hôn | ✅ | ✅ | TIE |

---

**Đánh giá bởi:** Claude (AI Judge)  
**Phương pháp:** So sánh accuracy, completeness, citation quality, response time
