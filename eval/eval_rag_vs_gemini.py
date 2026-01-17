"""
RAG vs Gemini 2.5 Flash Evaluation
==================================
Compare RAG answers with Gemini 2.5 Flash API directly.

Setup:
    Create .env file with:
        GEMINI_API_KEY=your_gemini_key
        RAG_API_URL=http://localhost:8000

Usage:
    python eval_rag_vs_gemini_api.py --chunk 1
    python eval_rag_vs_gemini_api.py  # Run all
"""
import json
import httpx
import asyncio
import os
import argparse
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import List, Dict
from dotenv import load_dotenv

# Auto-resolve paths from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
ENV_FILE = SCRIPT_DIR / ".env"
RESULTS_DIR = SCRIPT_DIR / "results"
TEST_CASE_DIR = SCRIPT_DIR / "test_case"

load_dotenv(ENV_FILE)

# Config
RAG_API_URL = os.getenv("RAG_API_URL", "http://localhost:8000")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-2.5-flash"

# System prompt for Gemini to match legal context
GEMINI_SYSTEM_PROMPT = """You are a Vietnamese labor law expert assistant.
Answer questions about Vietnamese labor law accurately and concisely.
Cite specific articles (Điều) and legal documents when possible.
Respond in Vietnamese."""


@dataclass
class ComparisonResult:
    test_id: str
    question: str
    rag_answer: str
    gemini_answer: str
    rag_sources: List[str]
    rag_latency_ms: float
    gemini_latency_ms: float
    rag_word_count: int
    gemini_word_count: int
    rag_has_citation: bool
    gemini_has_citation: bool


def load_test_cases_from_chunks(chunks: List[str]) -> List[Dict]:
    all_cases = []
    for chunk in chunks:
        # Support both numeric and named chunks
        if chunk.isdigit():
            path = f"./test_cases_chunk{chunk}.json"
        else:
            path = f"./test_cases_chunk_{chunk}.json"
        
        if os.path.exists(path):
            with open(path, 'r', encoding='utf-8') as f:
                cases = json.load(f)
                all_cases.extend(cases)
                print(f"   Loaded chunk {chunk}: {len(cases)} cases")
        else:
            print(f"   Chunk {chunk} not found ({path})")
    return all_cases


async def call_gemini_api(question: str) -> tuple:
    """Call Gemini 2.5 Flash API directly"""
    start = asyncio.get_event_loop().time()
    
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
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
                return f"[Gemini Error: {data['error']['message']}]", 0
            
            if "candidates" in data and len(data["candidates"]) > 0:
                text = data["candidates"][0]["content"]["parts"][0]["text"]
                latency = (asyncio.get_event_loop().time() - start) * 1000
                return text, latency
            
            return "[No Gemini response]", 0
            
    except Exception as e:
        return f"[Gemini Error: {str(e)}]", 0


async def call_rag_api(question: str) -> tuple:
    """Call RAG API"""
    start = asyncio.get_event_loop().time()
    
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
            
            latency = (asyncio.get_event_loop().time() - start) * 1000
            return full_response, sources, latency
            
    except Exception as e:
        return f"[RAG Error: {str(e)}]", [], 0


def has_citation(text: str) -> bool:
    import re
    return bool(re.search(r'(Điều|điều|Khoản|khoản|Nghị định|BLLĐ|Luật)', text))


async def run_comparison(test_case: Dict) -> ComparisonResult:
    question = test_case["question"]
    
    # Get both answers
    rag_answer, sources, rag_latency = await call_rag_api(question)
    gemini_answer, gemini_latency = await call_gemini_api(question)
    
    return ComparisonResult(
        test_id=test_case["id"],
        question=question,
        rag_answer=rag_answer,
        gemini_answer=gemini_answer,
        rag_sources=sources,
        rag_latency_ms=rag_latency,
        gemini_latency_ms=gemini_latency,
        rag_word_count=len(rag_answer.split()),
        gemini_word_count=len(gemini_answer.split()),
        rag_has_citation=has_citation(rag_answer),
        gemini_has_citation=has_citation(gemini_answer)
    )


async def run_evaluation(test_cases: List[Dict]) -> List[ComparisonResult]:
    results = []
    total = len(test_cases)
    
    for i, tc in enumerate(test_cases):
        print(f"\n[{i+1}/{total}] {tc['id']}: {tc['question'][:50]}...")
        result = await run_comparison(tc)
        results.append(result)
        
        print(f"  Time: RAG={result.rag_latency_ms:.0f}ms | Gemini={result.gemini_latency_ms:.0f}ms")
        print(f"  Words: RAG={result.rag_word_count} | Gemini={result.gemini_word_count}")
        print(f"  Citations: RAG={'Yes' if result.rag_has_citation else 'No'} | Gemini={'Yes' if result.gemini_has_citation else 'No'}")
        
        await asyncio.sleep(2)  # Rate limit
    
    return results


def generate_report(results: List[ComparisonResult]) -> Dict:
    n = len(results)
    
    avg_rag_latency = sum(r.rag_latency_ms for r in results) / n if n else 0
    avg_gemini_latency = sum(r.gemini_latency_ms for r in results) / n if n else 0
    avg_rag_words = sum(r.rag_word_count for r in results) / n if n else 0
    avg_gemini_words = sum(r.gemini_word_count for r in results) / n if n else 0
    rag_citation_rate = sum(1 for r in results if r.rag_has_citation) / n if n else 0
    gemini_citation_rate = sum(1 for r in results if r.gemini_has_citation) / n if n else 0
    
    return {
        "timestamp": datetime.now().isoformat(),
        "model": GEMINI_MODEL,
        "total_tests": n,
        "summary": {
            "avg_rag_latency_ms": round(avg_rag_latency, 0),
            "avg_gemini_latency_ms": round(avg_gemini_latency, 0),
            "avg_rag_words": round(avg_rag_words, 1),
            "avg_gemini_words": round(avg_gemini_words, 1),
            "rag_citation_rate": round(rag_citation_rate * 100, 1),
            "gemini_citation_rate": round(gemini_citation_rate * 100, 1)
        },
        "results": [asdict(r) for r in results]
    }


def print_summary(report: Dict):
    s = report["summary"]
    print("\n" + "="*60)
    print(f"RAG vs {report['model']} COMPARISON")
    print("="*60)
    print(f"\nAvg Response Time:")
    print(f"   RAG:    {s['avg_rag_latency_ms']:.0f}ms")
    print(f"   Gemini: {s['avg_gemini_latency_ms']:.0f}ms")
    print(f"\nAvg Answer Length:")
    print(f"   RAG:    {s['avg_rag_words']:.0f} words")
    print(f"   Gemini: {s['avg_gemini_words']:.0f} words")
    print(f"\nCitation Rate:")
    print(f"   RAG:    {s['rag_citation_rate']:.0f}%")
    print(f"   Gemini: {s['gemini_citation_rate']:.0f}%")
    print("="*60)


async def main():
    parser = argparse.ArgumentParser(description="RAG vs Gemini API Eval")
    parser.add_argument("--chunk", type=str, nargs="+", help="Chunk names (1-6 or 'hard')")
    args = parser.parse_args()
    
    print("RAG vs Gemini 2.5 Flash Evaluation")
    print(f"   RAG API: {RAG_API_URL}")
    print(f"   Gemini Model: {GEMINI_MODEL}")
    print(f"   API Key: {'Set' if GEMINI_API_KEY else 'Missing!'}")
    
    if not GEMINI_API_KEY:
        print("\nSet GEMINI_API_KEY in .env")
        return
    
    os.makedirs(RESULTS_DIR, exist_ok=True)
    
    chunks = args.chunk if args.chunk else ["1", "2", "3", "4", "5", "6"]
    print(f"\nLoading chunks: {chunks}")
    test_cases = load_test_cases_from_chunks(chunks)
    
    if not test_cases:
        print("No test cases!")
        return
    
    print(f"\nRunning {len(test_cases)} comparisons...")
    results = await run_evaluation(test_cases)
    
    report = generate_report(results)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_path = f"{RESULTS_DIR}/rag_vs_gemini_api_{timestamp}.json"
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\nSaved: {output_path}")
    print_summary(report)


if __name__ == "__main__":
    asyncio.run(main())
