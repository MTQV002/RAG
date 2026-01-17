
import json
import httpx
import asyncio
import os
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict, Optional
from dotenv import load_dotenv

# Auto-resolve paths from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"
RESULTS_DIR = SCRIPT_DIR / "results"
TEST_CASE_DIR = SCRIPT_DIR / "test_case"

load_dotenv(ENV_FILE)

# ===== CONFIG =====
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
SERP_API_KEY = os.getenv("SERP_API_KEY")


@dataclass
class ComparisonResult:
    test_id: str
    question: str
    rag_answer: str
    google_answer: str
    rag_sources: List[str]
    # Timing
    rag_latency_ms: float
    google_latency_ms: float
    # Metrics
    rag_word_count: int
    google_word_count: int
    rag_char_count: int
    google_char_count: int
    rag_has_citation: bool  # Has "Điều" reference
    google_has_citation: bool


def load_test_cases_from_chunks(chunks: List[int]) -> List[Dict]:
    all_cases = []
    for chunk_num in chunks:
        path = TEST_CASE_DIR / f"test_cases_chunk{chunk_num}.json"
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                cases = json.load(f)
                all_cases.extend(cases)
                print(f"   ✅ Loaded chunk {chunk_num}: {len(cases)} cases")
        else:
            print(f"   ⚠️ Chunk {chunk_num} not found: {path}")
    return all_cases


async def search_google(query: str) -> str:
    """
    Search Google using SerpAPI - get AI Overview FULL content
    """
    if not SERP_API_KEY:
        return "[ERROR: Set SERP_API_KEY in .env file]"
    
    try:
        search_query = f"{query} luật lao động Việt Nam"
        
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(
                "https://serpapi.com/search",
                params={
                    "q": search_query,
                    "api_key": SERP_API_KEY,
                    "hl": "vi",
                    "gl": "vn",
                    "google_domain": "google.com.vn"
                }
            )
            data = resp.json()
            
            result_parts = []
            
            # 1. AI Overview (Gemini/AI answer) - Get FULL
            if "ai_overview" in data:
                ai = data["ai_overview"]
                if isinstance(ai, dict):
                    # Try different keys
                    for key in ["text", "snippet", "answer", "text_blocks"]:
                        if key in ai:
                            content = ai[key]
                            if isinstance(content, list):
                                result_parts.append("[AI Overview]\n" + "\n".join(str(x) for x in content))
                            else:
                                result_parts.append(f"[AI Overview]\n{content}")
                            break
                elif isinstance(ai, str):
                    result_parts.append(f"[AI Overview]\n{ai}")
            
            # 2. Answer Box
            if "answer_box" in data:
                box = data["answer_box"]
                for key in ["answer", "snippet", "result", "contents"]:
                    if key in box:
                        result_parts.append(f"[Answer Box]\n{box[key]}")
                        break
            
            # 3. Organic Results (top 3)
            if "organic_results" in data:
                for i, result in enumerate(data["organic_results"][:3]):
                    snippet = result.get("snippet", "")
                    title = result.get("title", "")
                    link = result.get("link", "")
                    if snippet:
                        result_parts.append(f"[Result {i+1}] {title}\n{snippet}\n{link}")
            
            # Debug: print what keys we got
            if not result_parts:
                print(f"  📋 SerpAPI keys: {list(data.keys())}")
                return f"[No content found. Keys: {list(data.keys())}]"
            
            return "\n\n".join(result_parts)
            
    except Exception as e:
        return f"[Google Error: {str(e)}]"


async def call_rag_api(question: str) -> tuple:
    """
    Call RAG API - get FULL answer
    """
    start_time = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
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
            
            latency_ms = (asyncio.get_event_loop().time() - start_time) * 1000
            return full_response, sources, latency_ms
            
    except Exception as e:
        return f"[RAG Error: {str(e)}]", [], 0


async def search_google_with_timing(query: str) -> tuple:
    """Search Google and return (answer, latency_ms)"""
    start = asyncio.get_event_loop().time()
    answer = await search_google(query)
    latency = (asyncio.get_event_loop().time() - start) * 1000
    return answer, latency


def has_citation(text: str) -> bool:
    """Check if text contains legal citation (Điều, Khoản, etc.)"""
    import re
    return bool(re.search(r'(Điều|điều|Khoản|khoản|Nghị định|BLLĐ|Luật)', text))


async def run_comparison(test_case: Dict) -> ComparisonResult:
    question = test_case["question"]
    
    # Get both answers with timing
    rag_answer, sources, rag_latency = await call_rag_api(question)
    google_answer, google_latency = await search_google_with_timing(question)
    
    return ComparisonResult(
        test_id=test_case["id"],
        question=question,
        rag_answer=rag_answer,
        google_answer=google_answer,
        rag_sources=sources,
        # Timing
        rag_latency_ms=rag_latency,
        google_latency_ms=google_latency,
        # Metrics
        rag_word_count=len(rag_answer.split()),
        google_word_count=len(google_answer.split()),
        rag_char_count=len(rag_answer),
        google_char_count=len(google_answer),
        rag_has_citation=has_citation(rag_answer),
        google_has_citation=has_citation(google_answer)
    )


async def run_evaluation(test_cases: List[Dict]) -> List[ComparisonResult]:
    results = []
    total = len(test_cases)
    
    for i, tc in enumerate(test_cases):
        print(f"\n[{i+1}/{total}] {tc['id']}: {tc['question'][:50]}...")
        result = await run_comparison(tc)
        results.append(result)
        
        # Preview with metrics
        print(f"  RAG: {result.rag_latency_ms:.0f}ms | Google: {result.google_latency_ms:.0f}ms")
        print(f"  RAG: {result.rag_word_count} words | Google: {result.google_word_count} words")
        print(f"  Citations: RAG={'✅' if result.rag_has_citation else '❌'} | Google={'✅' if result.google_has_citation else '❌'}")
        
        await asyncio.sleep(1)
    
    return results


def generate_report(results: List[ComparisonResult]) -> Dict:
    n = len(results)
    
    # Calculate averages
    avg_rag_latency = sum(r.rag_latency_ms for r in results) / n if n else 0
    avg_google_latency = sum(r.google_latency_ms for r in results) / n if n else 0
    avg_rag_words = sum(r.rag_word_count for r in results) / n if n else 0
    avg_google_words = sum(r.google_word_count for r in results) / n if n else 0
    rag_citation_rate = sum(1 for r in results if r.rag_has_citation) / n if n else 0
    google_citation_rate = sum(1 for r in results if r.google_has_citation) / n if n else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "total_tests": n,
        "summary": {
            "avg_rag_latency_ms": round(avg_rag_latency, 0),
            "avg_google_latency_ms": round(avg_google_latency, 0),
            "avg_rag_words": round(avg_rag_words, 1),
            "avg_google_words": round(avg_google_words, 1),
            "rag_citation_rate": round(rag_citation_rate * 100, 1),
            "google_citation_rate": round(google_citation_rate * 100, 1)
        },
        "results": [asdict(r) for r in results]
    }


def print_summary(report: Dict):
    s = report["summary"]
    print("\n" + "="*60)
    print("COMPARISON SUMMARY")
    print("="*60)
    print(f"\n⏱ Avg Response Time:")
    print(f"   RAG:    {s['avg_rag_latency_ms']:.0f}ms")
    print(f"   Google: {s['avg_google_latency_ms']:.0f}ms")
    print(f"\n Avg Answer Length:")
    print(f"   RAG:    {s['avg_rag_words']:.0f} words")
    print(f"   Google: {s['avg_google_words']:.0f} words")
    print(f"\n Citation Rate:")
    print(f"   RAG:    {s['rag_citation_rate']:.0f}%")
    print(f"   Google: {s['google_citation_rate']:.0f}%")
    print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="RAG vs Google Comparison")
    parser.add_argument("--chunk", type=int, nargs="+", help="Chunk numbers (1-6)")
    args = parser.parse_args()
    
    print("🚀 RAG vs Google Comparison")
    print(f"   RAG API: {RAG_API_URL}")
    print(f"   SERP API: {'✅' if SERP_API_KEY else '❌ Missing'}")
    
    if not SERP_API_KEY:
        print("\n❌ Set SERP_API_KEY in .env")
        return
    
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    chunks = args.chunk if args.chunk else [1, 2, 3, 4, 5, 6]
    print(f"\n Loading chunks: {chunks}")
    test_cases = load_test_cases_from_chunks(chunks)
    
    if not test_cases:
        print("❌ No test cases!")
        return
    
    print(f"\n🔄 Running {len(test_cases)} comparisons...")
    results = await run_evaluation(test_cases)
    report = generate_report(results)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = RESULTS_DIR / f"comparison_{timestamp}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n💾 Saved: {output_path}")
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
