"""
Post-processing script: Xử lý legal_decrees.json sau khi chạy processing.py
- Sửa Điều 5 NĐ 293 vì lý do phụ lục thành phố dài quá nên tóm tắt lại 
- Tối ưu content cho RAG

Chạy: python ND293_process.py
"""
import json

INPUT_FILE = './legal_decrees.json'
OUTPUT_FILE = './legal_decrees.json'  


def fix_nd293_dieu5(data: list) -> bool:
    for item in data:
        meta = item['metadata']
        if meta['doc_number'] == '293/2025/NĐ-CP' and meta['article_id'] == '5':
            new_content = """[Nghị định về mức lương tối thiểu vùng 2026]
[Quy định chung]
Điều 5. Hiệu lực và trách nhiệm thi hành
1. Nghị định này có hiệu lực thi hành từ ngày 01 tháng 01 năm 2026.
2. Nghị định số 74/2024/NĐ-CP ngày 30 tháng 6 năm 2024 của Chính phủ quy định mức lương tối thiểu đối với người lao động làm việc theo hợp đồng lao động hết hiệu lực kể từ ngày Nghị định này có hiệu lực thi hành.
3. Bãi bỏ khoản 7 Điều 15 và Phụ lục I kèm theo của Nghị định số 128/2025/NĐ-CP.
4. Người sử dụng lao động có trách nhiệm rà soát các thỏa thuận trong hợp đồng lao động, thỏa ước lao động tập thể để điều chỉnh cho phù hợp.
5. Các Bộ trưởng, Thủ trưởng cơ quan ngang bộ, Chủ tịch UBND tỉnh/thành phố và người sử dụng lao động chịu trách nhiệm thi hành Nghị định này.

DANH MỤC ĐỊA BÀN ÁP DỤNG MỨC LƯƠNG TỐI THIỂU (TÓM TẮT):

| Vùng | Lương tháng | Lương giờ | Địa bàn áp dụng |
| --- | --- | --- | --- |
| Vùng I | 5.310.000 đ | 25.500 đ | Nội thành Hà Nội, TP.HCM, Hải Phòng, Đồng Nai, Bình Dương, Bà Rịa-Vũng Tàu |
| Vùng II | 4.730.000 đ | 22.700 đ | Ngoại thành Hà Nội, TP.HCM; Đà Nẵng, Cần Thơ, Long An, Tây Ninh, Bình Định, Khánh Hòa |
| Vùng III | 4.140.000 đ | 20.000 đ | Các thành phố, thị xã thuộc tỉnh; các huyện công nghiệp |
| Vùng IV | 3.700.000 đ | 17.800 đ | Các vùng nông thôn còn lại |

Lưu ý: Danh mục chi tiết từng xã/phường xem Phụ lục Nghị định 293/2025/NĐ-CP."""

            old_len = len(item['page_content'])
            item['page_content'] = new_content
            print(f"Đã sửa NĐ 293 Điều 5: {old_len:,} → {len(new_content):,} ký tự")
            return True
    return False


def check_long_chunks(data: list, threshold: int = 10000):
    long_chunks = []
    for item in data:
        length = len(item['page_content'])
        if length > threshold:
            meta = item['metadata']
            long_chunks.append({
                'doc_name': meta['doc_name'],
                'article_id': meta['article_id'],
                'length': length
            })
    return long_chunks


def main():
    print("="*60)
    print("POST-PROCESSING legal_decrees.json")
    print("="*60)
    with open(INPUT_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    print(f"\nLoaded {len(data)} chunks from {INPUT_FILE}")
    
    # Fix NĐ 293 Điều 5
    print("\n Xử lý NĐ 293 Điều 5 (cắt PHỤ LỤC)...")
    fixed = fix_nd293_dieu5(data)
    if not fixed:
        print(" Không tìm thấy NĐ 293 Điều 5")
    
    # Kiểm tra chunks dài
    print("\n Kiểm tra chunks > 10,000 ký tự:")
    long_chunks = check_long_chunks(data)
    if long_chunks:
        for chunk in long_chunks:
            print(f" - {chunk['doc_name']} Điều {chunk['article_id']}: {chunk['length']:,} ký tự")
    else:
        print(" Không có chunks > 10,000 ký tự")
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    print("\n" + "="*60)
    print("HOÀN TẤT POST-PROCESSING")
    print("="*60)


if __name__ == "__main__":
    main()
