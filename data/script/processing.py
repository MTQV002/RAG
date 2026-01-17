import re
from docx import Document
import json
from typing import List, Dict, Optional
from dataclasses import dataclass
import os

@dataclass
class DocumentInfo:
    doc_type: str
    doc_number: str
    doc_name: str
    short_name: str
    effective_date: str
    status: str


class LegalDocumentParser:    
    def __init__(self, doc_info: DocumentInfo):
        self.doc_info = doc_info
        
    def parse(self, text: str) -> List[Dict]:
        chunks = []
        
        # Tách phần chính (Điều) và phụ lục
        main_text, appendix_text = self._split_appendix(text)
        
        # Parse phần Điều như cũ
        chapter_header_pattern = r"^(Chương [IVXLCDM]+)\.?\s*\n?([A-ZĐÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ][A-ZĐÁÀẢÃẠĂẮẰẲẴẶÂẤẦẨẪẬÉÈẺẼẸÊẾỀỂỄỆÍÌỈĨỊÓÒỎÕỌÔỐỒỔỖỘƠỚỜỞỠỢÚÙỦŨỤƯỨỪỬỮỰÝỲỶỸỴ, ]+)"
        
        chapter_matches = list(re.finditer(chapter_header_pattern, main_text, re.MULTILINE))
        
        if not chapter_matches:
            current_chapter = "Quy định chung"
            self._parse_articles(main_text, current_chapter, chunks)
        else:
            first_chapter_start = chapter_matches[0].start()
            if first_chapter_start > 0:
                before_first = main_text[:first_chapter_start]
                self._parse_articles(before_first, "Quy định chung", chunks)
            
            for i, match in enumerate(chapter_matches):
                chapter_num = match.group(1) 
                chapter_title = match.group(2).strip() 
                current_chapter = f"{chapter_num}. {chapter_title}"

                start_pos = match.end()
                if i + 1 < len(chapter_matches):
                    end_pos = chapter_matches[i + 1].start()
                else:
                    end_pos = len(main_text)
                
                chapter_content = main_text[start_pos:end_pos]
                self._parse_articles(chapter_content, current_chapter, chunks)
        
        # Parse phụ lục nếu có
        if appendix_text:
            appendix_chunks = self._parse_appendix(appendix_text)
            chunks.extend(appendix_chunks)
        
        return chunks
    
    def _split_appendix(self, text: str) -> tuple:
        """Tách phần chính và phụ lục"""
        # Tìm vị trí bắt đầu phụ lục
        appendix_patterns = [
            r"\n(PHỤ LỤC\s*\n)",
            r"\n(Phụ lục\s*\n)",
            r"\n(PHỤ LỤC:)",
            r"\n(Phụ lục:)",
        ]
        
        for pattern in appendix_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                main_text = text[:match.start()]
                appendix_text = text[match.start():]
                return main_text, appendix_text
        
        return text, ""
    
    def _parse_appendix(self, appendix_text: str) -> List[Dict]:
        """Parse phụ lục thành chunks theo tỉnh/thành phố"""
        chunks = []
        
        # Pattern tìm từng tỉnh/thành phố: "số. Tỉnh/Thành phố Tên"
        province_pattern = r"(\d+)\.\s*(Tỉnh|Thành phố)\s+([^\n]+)"
        matches = list(re.finditer(province_pattern, appendix_text))
        
        if not matches:
            # Không tìm thấy tỉnh → tạo 1 chunk cho toàn bộ phụ lục
            chunk = self._create_appendix_chunk(
                appendix_text, 
                appendix_id="PHỤ LỤC",
                appendix_title="Danh sách phân vùng lương"
            )
            if chunk:
                chunks.append(chunk)
            return chunks
        
        # Parse từng tỉnh
        for i, match in enumerate(matches):
            province_num = match.group(1)
            province_type = match.group(2)  # "Tỉnh" hoặc "Thành phố"
            province_name = match.group(3).strip()
            
            # Lấy content từ match hiện tại đến match tiếp theo
            start_pos = match.start()
            if i + 1 < len(matches):
                end_pos = matches[i + 1].start()
            else:
                end_pos = len(appendix_text)
            
            province_content = appendix_text[start_pos:end_pos].strip()
            
            chunk = self._create_appendix_chunk(
                province_content,
                appendix_id=f"PL_{province_num}",
                appendix_title=f"{province_type} {province_name}"
            )
            if chunk:
                chunks.append(chunk)
        
        return chunks
    
    def _create_appendix_chunk(self, content: str, appendix_id: str, appendix_title: str) -> Optional[Dict]:
        """Tạo chunk cho phụ lục"""
        if not content.strip():
            return None
        
        page_content = f"""[{self.doc_info.doc_name}]
[Phụ lục - {appendix_title}]
{content}"""
        
        return {
            "page_content": page_content,
            "metadata": {
                "doc_type": self.doc_info.doc_type,
                "doc_number": self.doc_info.doc_number,
                "doc_name": self.doc_info.doc_name,
                "short_name": self.doc_info.short_name,
                "chapter": "Phụ lục",
                "article_id": appendix_id,
                "article_title": appendix_title,
                "effective_date": self.doc_info.effective_date,
                "status": self.doc_info.status,
                "references": [],
            }
        }
    
    def _parse_articles(self, text: str, chapter: str, chunks: List[Dict]):
        article_pattern = r"(Điều \d+\..*?)(?=\nĐiều \d+\.|$)"
        articles = re.findall(article_pattern, text, re.DOTALL)
        
        for article in articles:
            chunk = self._create_chunk(article, chapter)
            if chunk:
                chunks.append(chunk)
    
    def _clean_article(self, article: str) -> str:
        """Loại bỏ footer/signature không cần thiết"""
        # Loại bỏ bảng "Nơi nhận" và chữ ký
        patterns_to_remove = [
            r"\| Nơi nhận:.*?\| --- \| --- \|",  # Bảng Nơi nhận markdown
            r"\n\| Nơi nhận:.*$",  # Bảng Nơi nhận đến cuối
            r"TM\. CHÍNH PHỦ.*$",  # Chữ ký Chính phủ
            r"KT\. THỦ TƯỚNG.*$",  # KT. Thủ tướng  
        ]
        
        cleaned = article
        for pattern in patterns_to_remove:
            cleaned = re.sub(pattern, "", cleaned, flags=re.DOTALL | re.MULTILINE)
        
        return cleaned.strip()
    
    def _create_chunk(self, article: str, chapter: str) -> Optional[Dict]:
        header_match = re.match(r"Điều (\d+)\.\s*([^\n]+)", article)
        if not header_match:
            return None
        article_id = header_match.group(1)
        article_title = header_match.group(2).strip()
        
        # Clean article content
        cleaned_article = self._clean_article(article)
        references = self._extract_references(cleaned_article, article_id)
        
        page_content = f"""[{self.doc_info.doc_name}]
[{chapter}]
{cleaned_article}"""
        
        return {
            "page_content": page_content,
            "metadata": {
                "doc_type": self.doc_info.doc_type,
                "doc_number": self.doc_info.doc_number,
                "doc_name": self.doc_info.doc_name,
                "short_name": self.doc_info.short_name,
                "chapter": chapter,
                "article_id": article_id,
                "article_title": article_title,
                "effective_date": self.doc_info.effective_date,
                "status": self.doc_info.status,
                "references": references,
            }
        }
    
    def _extract_references(self, text: str, current_article_id: str = None) -> List[str]:
        refs = set()
        
        internal = re.findall(r"(?:khoản \d+\s+)?Điều (\d+)", text)
        for r in internal:
            if current_article_id is None or r != current_article_id:
                refs.add(f"Điều {r}")
        
        external_patterns = [
            r"(Luật [^,\.;]+\d{4})",
            r"(Bộ luật [^,\.;]+\d{4})",
            r"(Nghị định số \d+/\d+/NĐ-CP)",
            r"(Thông tư số \d+/\d+/TT-[A-Z]+)",
        ]
        for pattern in external_patterns:
            matches = re.findall(pattern, text)
            refs.update(matches)
        
        return list(refs)


def table_to_text(table) -> str:
    """Chuyển table trong docx thành text dạng markdown"""
    lines = []
    for i, row in enumerate(table.rows):
        cells = [cell.text.strip().replace('\n', ' ') for cell in row.cells]
        line = "| " + " | ".join(cells) + " |"
        lines.append(line)
        if i == 0:
            separator = "| " + " | ".join(["---"] * len(cells)) + " |"
            lines.append(separator)
    return "\n".join(lines)


def read_docx(path: str) -> str:
    doc = Document(path)
    content_parts = []
    
    from docx.oxml.ns import qn
    from docx.text.paragraph import Paragraph
    from docx.table import Table as DocxTable
    
    for child in doc.element.body:
        if child.tag == qn('w:p'):
            para = Paragraph(child, doc)
            if para.text.strip():
                content_parts.append(para.text)
        elif child.tag == qn('w:tbl'):
            tbl = DocxTable(child, doc)
            table_text = table_to_text(tbl)
            if table_text.strip():
                content_parts.append("\n" + table_text + "\n")
    
    return "\n".join(content_parts)


DOCUMENTS = [
    # Luật
    {
        "filename": "45_2019_LD.docx",
        "doc_info": DocumentInfo(
            doc_type="luật",
            doc_number="45/2019/QH14",
            doc_name="Bộ luật Lao động",
            short_name="BLLĐ",
            effective_date="01/01/2021",
            status="còn hiệu lực"
        )
    },
    {
        "filename": "84_2015_ATVSLD.docx",
        "doc_info": DocumentInfo(
            doc_type="luật",
            doc_number="84/2015/QH13",
            doc_name="Luật An toàn, vệ sinh lao động",
            short_name="ATVSLĐ",
            effective_date="01/07/2016",
            status="còn hiệu lực"
        )
    },
    {
        "filename": "41_2024_BHXH.docx",
        "doc_info": DocumentInfo(
            doc_type="luật",
            doc_number="41/2024/QH15",
            doc_name="Luật Bảo hiểm xã hội 2024",
            short_name="BHXH",
            effective_date="01/07/2025",
            status="còn hiệu lực"
        )
    },
    {
        "filename": "74_2025_VL.docx",
        "doc_info": DocumentInfo(
            doc_type="luật",
            doc_number="74/2025/QH15",
            doc_name="Luật Việc làm",
            short_name="VL",
            effective_date="01/01/2026",
            status="còn hiệu lực"
        )
    },
    # Nghị định
    {
        "filename": "145_2020_ND-CP_m_459400.docx",
        "doc_info": DocumentInfo(
            doc_type="nghị_định",
            doc_number="145/2020/NĐ-CP",
            doc_name="Nghị định hướng dẫn Bộ luật Lao động về điều kiện lao động",
            short_name="ND145",
            effective_date="01/02/2021",
            status="còn hiệu lực"
        )
    },
    {
        "filename": "12_2022_ND-CP_m_479312.docx",
        "doc_info": DocumentInfo(
            doc_type="nghị_định",
            doc_number="12/2022/NĐ-CP",
            doc_name="Nghị định xử phạt vi phạm hành chính trong lĩnh vực lao động",
            short_name="ND12",
            effective_date="17/01/2022",
            status="còn hiệu lực"
        )
    },
    {
        "filename": "293_2025_ND-CP_m_665866.docx",
        "doc_info": DocumentInfo(
            doc_type="nghị_định",
            doc_number="293/2025/NĐ-CP",
            doc_name="Nghị định về mức lương tối thiểu vùng 2026",
            short_name="ND293",
            effective_date="01/01/2026",
            status="còn hiệu lực"
        )
    },
]


def process_all_documents(law_dir: str, decree_dir: str) -> List[Dict]:
    all_chunks = []
    
    for doc_config in DOCUMENTS:
        if doc_config["doc_info"].doc_type == "luật":
            filepath = os.path.join(law_dir, doc_config["filename"])
        else:
            filepath = os.path.join(decree_dir, doc_config["filename"])
            
        if not os.path.exists(filepath):
            print(f"❌ File not found: {filepath}")
            continue
            
        text = read_docx(filepath)
        parser = LegalDocumentParser(doc_config["doc_info"])
        chunks = parser.parse(text)
        
        # Đếm số điều và phụ lục
        articles = [c for c in chunks if not c['metadata']['article_id'].startswith('PL_')]
        appendix = [c for c in chunks if c['metadata']['article_id'].startswith('PL_')]
        
        all_chunks.extend(chunks)
        print(f"✅ {doc_config['doc_info'].short_name}: {len(articles)} điều, {len(appendix)} phụ lục")
    
    return all_chunks


if __name__ == "__main__":
    from pathlib import Path
    
    # Get script directory and resolve paths relative to it
    SCRIPT_DIR = Path(__file__).parent.resolve()
    DATA_DIR = SCRIPT_DIR.parent  # data/ folder
    
    LAW_DIR = DATA_DIR / "Law"
    DECREE_DIR = DATA_DIR / "ND"
    OUTPUT_PATH = DATA_DIR / "legal_decrees.json"
    
    print(f"📁 Script dir: {SCRIPT_DIR}")
    print(f"📁 Law dir: {LAW_DIR}")
    print(f"📁 Decree dir: {DECREE_DIR}")
    
    chunks = process_all_documents(str(LAW_DIR), str(DECREE_DIR))
    
    with open(OUTPUT_PATH, 'w', encoding='utf-8') as f:
        json.dump(chunks, f, ensure_ascii=False, indent=2)
    
    print(f"\n📊 Total: {len(chunks)} chunks")
    print(f"💾 Saved to: {OUTPUT_PATH}")