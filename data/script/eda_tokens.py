"""
EDA: Phân tích token distribution trong legal_decrees.json
Tìm các documents >8k tokens (vượt limit reranker BGE-M3)
"""
import json
from collections import defaultdict

# Simple tokenizer estimate (1 token ≈ 4 chars cho tiếng Việt)
def estimate_tokens(text: str) -> int:
    return len(text) // 4

def main():
    with open('legal_decrees.json', 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    print(f"{'='*60}")
    print(f"📊 EDA: Token Distribution Analysis")
    print(f"{'='*60}")
    print(f"Tổng số documents: {len(data)}\n")
    
    # Analyze each document
    results = []
    for item in data:
        text = item.get('page_content', '')
        meta = item.get('metadata', {})
        tokens = estimate_tokens(text)
        
        results.append({
            'tokens': tokens,
            'chars': len(text),
            'doc_name': meta.get('doc_name', ''),
            'short_name': meta.get('short_name', ''),
            'article_id': meta.get('article_id', ''),
            'article_title': meta.get('article_title', '')[:50],
            'chapter': meta.get('chapter', '')[:30],
        })
    
    # Sort by tokens
    results.sort(key=lambda x: x['tokens'], reverse=True)
    
    # Statistics
    tokens_list = [r['tokens'] for r in results]
    print(f"📈 Token Statistics:")
    print(f"   Min: {min(tokens_list):,} tokens")
    print(f"   Max: {max(tokens_list):,} tokens")
    print(f"   Avg: {sum(tokens_list)//len(tokens_list):,} tokens")
    print(f"   Median: {sorted(tokens_list)[len(tokens_list)//2]:,} tokens")
    
    # Distribution buckets
    buckets = defaultdict(int)
    for t in tokens_list:
        if t < 1000:
            buckets['<1k'] += 1
        elif t < 2000:
            buckets['1k-2k'] += 1
        elif t < 4000:
            buckets['2k-4k'] += 1
        elif t < 8000:
            buckets['4k-8k'] += 1
        else:
            buckets['>8k ⚠️'] += 1
    
    print(f"\n📊 Token Distribution:")
    for bucket in ['<1k', '1k-2k', '2k-4k', '4k-8k', '>8k ⚠️']:
        count = buckets[bucket]
        pct = count * 100 / len(results)
        bar = '█' * int(pct / 2)
        print(f"   {bucket:8s}: {count:3d} ({pct:5.1f}%) {bar}")
    
    # Documents >8k tokens (reranker issue)
    over_8k = [r for r in results if r['tokens'] > 8000]
    
    print(f"\n{'='*60}")
    print(f"⚠️  DOCUMENTS >8K TOKENS (Reranker truncation)")
    print(f"{'='*60}")
    
    if over_8k:
        print(f"Số lượng: {len(over_8k)} documents\n")
        for i, r in enumerate(over_8k, 1):
            print(f"{i}. [{r['short_name']}] Điều {r['article_id']}: {r['article_title']}")
            print(f"   Tokens: {r['tokens']:,} | Chars: {r['chars']:,}")
            print(f"   Chapter: {r['chapter']}")
            print()
    else:
        print("✅ Không có document nào >8k tokens!")
    
    # Top 10 longest documents
    print(f"{'='*60}")
    print(f"📋 TOP 10 LONGEST DOCUMENTS")
    print(f"{'='*60}")
    for i, r in enumerate(results[:10], 1):
        status = "⚠️" if r['tokens'] > 8000 else "✅"
        print(f"{i:2d}. {status} [{r['short_name']:6s}] Đ.{r['article_id']:3s} | {r['tokens']:,} tokens | {r['article_title'][:40]}")
    
    # Group by doc_type
    print(f"\n{'='*60}")
    print(f"📁 GROUP BY DOCUMENT")
    print(f"{'='*60}")
    
    by_doc = defaultdict(list)
    for r in results:
        by_doc[r['short_name']].append(r['tokens'])
    
    for doc_name, token_list in sorted(by_doc.items()):
        max_t = max(token_list)
        avg_t = sum(token_list) // len(token_list)
        over = len([t for t in token_list if t > 8000])
        status = f"⚠️ {over} >8k" if over else "✅"
        print(f"   {doc_name:8s}: {len(token_list):3d} articles | Max: {max_t:,} | Avg: {avg_t:,} | {status}")

if __name__ == "__main__":
    main()
