"""
RAG vs Gemini - Hard Test Cases Evaluation
===========================================
Enhanced evaluation for complex multi-hop legal questions.
Includes advanced metrics: article coverage, calculation accuracy, sub-question scoring.

Usage:
    python eval_hard.py                    # Run all hard cases
    python eval_hard.py --file hard        # Specific file
"""
import json
import httpx
import asyncio
import os
import re
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Auto-resolve paths from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"
RESULTS_DIR = SCRIPT_DIR / "results" / "gemini"
TEST_CASE_DIR = SCRIPT_DIR / "test_case"

load_dotenv(ENV_FILE)

# Config
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

GEMINI_SYSTEM_PROMPT = """Bạn là chuyên gia pháp luật lao động Việt Nam.
Trả lời chính xác, đầy đủ từng câu hỏi con.
Trích dẫn Điều, Khoản cụ thể từ văn bản pháp luật.
Khi tính toán, trình bày công thức và kết quả rõ ràng."""


@dataclass
class HardTestResult:
    test_id: str
    category: str
    question: str
    expected_articles: List[str]
    
    # RAG results
    rag_answer: str
    rag_sources: List[str]
    rag_latency_ms: float
    rag_word_count: int
    
    # Gemini results
    gemini_answer: str
    gemini_latency_ms: float
    gemini_word_count: int
    
    # Advanced metrics
    rag_article_hits: int = 0
    rag_article_coverage: float = 0.0
    gemini_article_hits: int = 0
    gemini_article_coverage: float = 0.0
    
    sub_question_count: int = 0
    rag_sub_answered: int = 0
    gemini_sub_answered: int = 0
    
    rag_has_calculation: bool = False
    gemini_has_calculation: bool = False
    
    rag_error: str = ""
    gemini_error: str = ""


def count_sub_questions(question: str) -> int:
    """Đếm số câu hỏi con dựa trên pattern (1), (2), (3)..."""
    patterns = re.findall(r'\(\d+\)', question)
    return len(patterns) if patterns else 1


def count_answered_sub_questions(answer: str, count: int) -> int:
    """Đếm số câu hỏi con được trả lời"""
    if count == 1:
        return 1 if len(answer) > 50 else 0
    
    answered = 0
    for i in range(1, count + 1):
        # Tìm pattern (1), (2)... hoặc "Câu 1", "1.", "1)"
        patterns = [f"({i})", f"Câu {i}", f"{i}.", f"{i})"]
        for p in patterns:
            if p in answer:
                answered += 1
                break
    return answered


def check_article_coverage(answer: str, sources: List[str], expected: List[str]) -> tuple:
    """Kiểm tra bao nhiêu điều luật mong đợi được đề cập"""
    text_to_check = answer + " " + " ".join(sources)
    hits = 0
    
    for article in expected:
        # Extract article number
        match = re.search(r'Điều\s*(\d+)', article)
        if match:
            article_num = match.group(1)
            # Check in answer or sources
            if re.search(rf'Điều\s*{article_num}|{article_num}\s*(BLLĐ|BHXH|VL|ND)', text_to_check, re.IGNORECASE):
                hits += 1
    
    coverage = hits / len(expected) if expected else 0
    return hits, coverage


def has_calculation(text: str) -> bool:
    """Kiểm tra câu trả lời có tính toán không"""
    calc_patterns = [
        r'\d+\s*[×x\*]\s*\d+',  # multiplication
        r'\d+\s*[÷/]\s*\d+',   # division
        r'=\s*\d+',             # equals
        r'\d+\s*triệu',         # money
        r'\d+\s*%',             # percentage
        r'\d+\s*tháng\s*lương', # salary calculation
    ]
    return any(re.search(p, text) for p in calc_patterns)


async def call_gemini_api(question: str) -> tuple:
    """Call Gemini API"""
    start = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"https://generativelanguage.googleapis.com/v1beta/models/{GEMINI_MODEL}:generateContent?key={GEMINI_API_KEY}",
                json={
                    "contents": [{"parts": [{"text": question}]}],
                    "systemInstruction": {"parts": [{"text": GEMINI_SYSTEM_PROMPT}]},
                    "generationConfig": {
                        "temperature": 0.05,
                        "maxOutputTokens": 4024
                    }
                }
            )
            data = resp.json()
            
            if "error" in data:
                return "", 0, data['error'].get('message', 'Unknown error')
            
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                latency = (asyncio.get_event_loop().time() - start) * 1000
                return text, latency, ""
            
            return "", 0, "No response"
            
    except Exception as e:
        return "", 0, str(e)


async def call_rag_api(question: str) -> tuple:
    """Call RAG API"""
    start = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            full_response = ""
            sources = []
            
            async with client.stream(
                "POST",
                f"{RAG_API_URL}/chat",
                json={"content": question}
            ) as response:
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    json_str = line[5:].strip()
                    if not json_str:
                        continue
                    try:
                        data = json.loads(json_str)
                        if "token" in data:
                            full_response += data["token"]
                        if "nodes" in data:
                            for node in data["nodes"]:
                                meta = node.get("metadata", {})
                                sources.append(f"{meta.get('article_id', '')} {meta.get('short_name', '')}")
                    except json.JSONDecodeError:
                        continue
            
            latency = (asyncio.get_event_loop().time() - start) * 1000
            return full_response, sources, latency, ""
            
    except Exception as e:
        return "", [], 0, str(e)


async def evaluate_test_case(tc: Dict) -> HardTestResult:
    """Evaluate single test case with advanced metrics"""
    question = tc["question"]
    expected_articles = tc.get("expected_articles", [])
    sub_count = count_sub_questions(question)
    
    # Call both APIs
    rag_answer, rag_sources, rag_latency, rag_error = await call_rag_api(question)
    gemini_answer, gemini_latency, gemini_error = await call_gemini_api(question)
    
    # Calculate metrics
    rag_hits, rag_coverage = check_article_coverage(rag_answer, rag_sources, expected_articles)
    gemini_hits, gemini_coverage = check_article_coverage(gemini_answer, [], expected_articles)
    
    rag_sub = count_answered_sub_questions(rag_answer, sub_count)
    gemini_sub = count_answered_sub_questions(gemini_answer, sub_count)
    
    return HardTestResult(
        test_id=tc["id"],
        category=tc.get("category", "unknown"),
        question=question,
        expected_articles=expected_articles,
        
        rag_answer=rag_answer,
        rag_sources=rag_sources,
        rag_latency_ms=rag_latency,
        rag_word_count=len(rag_answer.split()),
        
        gemini_answer=gemini_answer,
        gemini_latency_ms=gemini_latency,
        gemini_word_count=len(gemini_answer.split()),
        
        rag_article_hits=rag_hits,
        rag_article_coverage=round(rag_coverage * 100, 1),
        gemini_article_hits=gemini_hits,
        gemini_article_coverage=round(gemini_coverage * 100, 1),
        
        sub_question_count=sub_count,
        rag_sub_answered=rag_sub,
        gemini_sub_answered=gemini_sub,
        
        rag_has_calculation=has_calculation(rag_answer),
        gemini_has_calculation=has_calculation(gemini_answer),
        
        rag_error=rag_error,
        gemini_error=gemini_error
    )


def generate_report(results: List[HardTestResult]) -> Dict:
    """Generate comprehensive report"""
    n = len(results)
    if n == 0:
        return {}
    
    # Basic metrics
    avg_rag_latency = sum(r.rag_latency_ms for r in results) / n
    avg_gemini_latency = sum(r.gemini_latency_ms for r in results) / n
    avg_rag_words = sum(r.rag_word_count for r in results) / n
    avg_gemini_words = sum(r.gemini_word_count for r in results) / n
    
    # Article coverage
    avg_rag_coverage = sum(r.rag_article_coverage for r in results) / n
    avg_gemini_coverage = sum(r.gemini_article_coverage for r in results) / n
    
    # Sub-question answering
    total_sub = sum(r.sub_question_count for r in results)
    rag_sub_answered = sum(r.rag_sub_answered for r in results)
    gemini_sub_answered = sum(r.gemini_sub_answered for r in results)
    
    # Calculation presence
    rag_calc_rate = sum(1 for r in results if r.rag_has_calculation) / n * 100
    gemini_calc_rate = sum(1 for r in results if r.gemini_has_calculation) / n * 100
    
    # Error rate
    rag_error_rate = sum(1 for r in results if r.rag_error) / n * 100
    gemini_error_rate = sum(1 for r in results if r.gemini_error) / n * 100
    
    return {
        "timestamp": datetime.now().isoformat(),
        "model": GEMINI_MODEL,
        "total_tests": n,
        "summary": {
            "latency": {
                "rag_avg_ms": round(avg_rag_latency, 0),
                "gemini_avg_ms": round(avg_gemini_latency, 0),
                "winner": "RAG" if avg_rag_latency < avg_gemini_latency else "Gemini"
            },
            "answer_length": {
                "rag_avg_words": round(avg_rag_words, 0),
                "gemini_avg_words": round(avg_gemini_words, 0)
            },
            "article_coverage": {
                "rag_avg_pct": round(avg_rag_coverage, 1),
                "gemini_avg_pct": round(avg_gemini_coverage, 1),
                "winner": "RAG" if avg_rag_coverage > avg_gemini_coverage else "Gemini"
            },
            "sub_question_answering": {
                "total_sub_questions": total_sub,
                "rag_answered": rag_sub_answered,
                "gemini_answered": gemini_sub_answered,
                "rag_rate_pct": round(rag_sub_answered / total_sub * 100, 1) if total_sub else 0,
                "gemini_rate_pct": round(gemini_sub_answered / total_sub * 100, 1) if total_sub else 0
            },
            "calculation": {
                "rag_has_calc_pct": round(rag_calc_rate, 1),
                "gemini_has_calc_pct": round(gemini_calc_rate, 1)
            },
            "errors": {
                "rag_error_pct": round(rag_error_rate, 1),
                "gemini_error_pct": round(gemini_error_rate, 1)
            }
        },
        "results": [asdict(r) for r in results]
    }


def print_summary(report: Dict):
    """Print formatted summary"""
    s = report["summary"]
    
    print("\n" + "="*70)
    print(f"🔥 HARD TEST EVALUATION - {report['total_tests']} cases")
    print("="*70)
    
    print("\n📊 LATENCY")
    print(f"   RAG:    {s['latency']['rag_avg_ms']:.0f}ms")
    print(f"   Gemini: {s['latency']['gemini_avg_ms']:.0f}ms")
    print(f"   Winner: {s['latency']['winner']}")
    
    print("\n📝 ANSWER LENGTH")
    print(f"   RAG:    {s['answer_length']['rag_avg_words']:.0f} words")
    print(f"   Gemini: {s['answer_length']['gemini_avg_words']:.0f} words")
    
    print("\n📚 ARTICLE COVERAGE (expected articles found)")
    print(f"   RAG:    {s['article_coverage']['rag_avg_pct']:.1f}%")
    print(f"   Gemini: {s['article_coverage']['gemini_avg_pct']:.1f}%")
    print(f"   Winner: {s['article_coverage']['winner']}")
    
    print("\n❓ SUB-QUESTION ANSWERING")
    sq = s['sub_question_answering']
    print(f"   Total sub-questions: {sq['total_sub_questions']}")
    print(f"   RAG:    {sq['rag_answered']}/{sq['total_sub_questions']} ({sq['rag_rate_pct']:.1f}%)")
    print(f"   Gemini: {sq['gemini_answered']}/{sq['total_sub_questions']} ({sq['gemini_rate_pct']:.1f}%)")
    
    print("\n🧮 CALCULATION PRESENCE")
    print(f"   RAG:    {s['calculation']['rag_has_calc_pct']:.1f}% có tính toán")
    print(f"   Gemini: {s['calculation']['gemini_has_calc_pct']:.1f}% có tính toán")
    
    print("\n⚠️ ERRORS")
    print(f"   RAG:    {s['errors']['rag_error_pct']:.1f}%")
    print(f"   Gemini: {s['errors']['gemini_error_pct']:.1f}%")
    
    print("="*70)


def load_test_cases(file_name: str) -> List[Dict]:
    """Load test cases from file"""
    if file_name.endswith('.json'):
        path = TEST_CASE_DIR / file_name
    else:
        path = TEST_CASE_DIR / f"test_cases_chunk_{file_name}.json"
    
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    print(f"File not found: {path}")
    return []


async def main():
    parser = argparse.ArgumentParser(description="Hard Test Cases Evaluation")
    parser.add_argument("--file", type=str, default="hard", help="Test case file name (without path)")
    args = parser.parse_args()
    
    print("🔥 RAG vs Gemini - Hard Test Evaluation")
    print(f"   RAG API: {RAG_API_URL}")
    print(f"   Gemini: {GEMINI_MODEL}")
    
    if not GEMINI_API_KEY:
        print("\n❌ Missing GEMINI_API_KEY in .env")
        return
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    test_cases = load_test_cases(args.file)
    if not test_cases:
        return
    
    print(f"\n📋 Loaded {len(test_cases)} test cases from {args.file}")
    
    results = []
    for i, tc in enumerate(test_cases):
        print(f"\n[{i+1}/{len(test_cases)}] {tc['id']}: {tc['question'][:60]}...")
        result = await evaluate_test_case(tc)
        results.append(result)
        
        print(f"   ⏱️  RAG={result.rag_latency_ms:.0f}ms | Gemini={result.gemini_latency_ms:.0f}ms")
        print(f"   📚 Coverage: RAG={result.rag_article_coverage}% | Gemini={result.gemini_article_coverage}%")
        print(f"   ❓ Sub-Q: RAG={result.rag_sub_answered}/{result.sub_question_count} | Gemini={result.gemini_sub_answered}/{result.sub_question_count}")
        
        await asyncio.sleep(2)
    
    report = generate_report(results)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"hard_{args.file}_{timestamp}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved: {output_path}")
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
