"""
EDA Script for Vietnam Labor Law RAG Project
Generates visualizations for slides and reports
"""
import json
import os
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from collections import Counter
import tiktoken

# Setup
plt.style.use('seaborn-v0_8-whitegrid')
plt.rcParams['font.size'] = 12
plt.rcParams['figure.figsize'] = (12, 6)
plt.rcParams['font.family'] = 'DejaVu Sans'

OUTPUT_DIR = "./eda_figures"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Load data
print("📊 Loading data...")
with open("legal_decrees.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(f"✅ Loaded {len(data)} documents")

# Create DataFrame
df = pd.DataFrame([{
    "text": d["page_content"],
    "doc_type": d["metadata"]["doc_type"],
    "doc_name": d["metadata"]["doc_name"],
    "short_name": d["metadata"]["short_name"],
    "chapter": d["metadata"]["chapter"],
    "article_id": d["metadata"]["article_id"],
    "article_title": d["metadata"]["article_title"],
    "effective_date": d["metadata"]["effective_date"],
    "char_count": len(d["page_content"]),
    "word_count": len(d["page_content"].split())
} for d in data])

# Token counting
print("📝 Counting tokens...")
try:
    enc = tiktoken.get_encoding("cl100k_base")
    df["token_count"] = df["text"].apply(lambda x: len(enc.encode(x)))
except:
    # Approximate: 1 token ≈ 4 chars for Vietnamese
    df["token_count"] = df["char_count"] // 4

print(f"✅ Token counting done")

# ============================================================================
# FIGURE 1: Documents Distribution by Source
# ============================================================================
print("📊 Creating Figure 1: Document distribution...")

fig, ax = plt.subplots(figsize=(12, 6))
doc_counts = df["short_name"].value_counts()

colors = sns.color_palette("husl", len(doc_counts))
bars = ax.barh(doc_counts.index, doc_counts.values, color=colors)

# Add value labels
for bar, val in zip(bars, doc_counts.values):
    ax.text(bar.get_width() + 1, bar.get_y() + bar.get_height()/2, 
            f'{val}', va='center', fontsize=11, fontweight='bold')

ax.set_xlabel("Số lượng Điều luật", fontsize=13)
ax.set_ylabel("Văn bản pháp luật", fontsize=13)
ax.set_title("📚 Phân bố số lượng Điều luật theo Văn bản", fontsize=15, fontweight='bold')
ax.invert_yaxis()

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/01_document_distribution.png", dpi=150, bbox_inches='tight')
print(f"   ✅ Saved: {OUTPUT_DIR}/01_document_distribution.png")
plt.close()

# ============================================================================
# FIGURE 2: Token Distribution Histogram
# ============================================================================
print("📊 Creating Figure 2: Token distribution...")

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# Histogram
ax1 = axes[0]
ax1.hist(df["token_count"], bins=50, color='steelblue', edgecolor='white', alpha=0.8)
ax1.axvline(df["token_count"].mean(), color='red', linestyle='--', linewidth=2, label=f'Mean: {df["token_count"].mean():.0f}')
ax1.axvline(df["token_count"].median(), color='orange', linestyle='--', linewidth=2, label=f'Median: {df["token_count"].median():.0f}')
ax1.set_xlabel("Số tokens", fontsize=12)
ax1.set_ylabel("Số lượng Điều", fontsize=12)
ax1.set_title("📈 Phân bố Token Count", fontsize=14, fontweight='bold')
ax1.legend()

# Boxplot by document
ax2 = axes[1]
df_sorted = df.sort_values("short_name")
sns.boxplot(data=df_sorted, x="short_name", y="token_count", ax=ax2, palette="husl")
ax2.set_xlabel("Văn bản", fontsize=12)
ax2.set_ylabel("Số tokens", fontsize=12)
ax2.set_title("📦 Token Distribution theo Văn bản", fontsize=14, fontweight='bold')
ax2.tick_params(axis='x', rotation=45)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/02_token_distribution.png", dpi=150, bbox_inches='tight')
print(f"   ✅ Saved: {OUTPUT_DIR}/02_token_distribution.png")
plt.close()

# ============================================================================
# FIGURE 3: Token Range Statistics
# ============================================================================
print("📊 Creating Figure 3: Token range statistics...")

# Token ranges
ranges = [
    ("< 200", (0, 200)),
    ("200-500", (200, 500)),
    ("500-1000", (500, 1000)),
    ("1000-2000", (1000, 2000)),
    ("2000-4000", (2000, 4000)),
    ("> 4000", (4000, float('inf')))
]

range_counts = []
for name, (low, high) in ranges:
    count = len(df[(df["token_count"] >= low) & (df["token_count"] < high)])
    range_counts.append({"range": name, "count": count, "pct": count/len(df)*100})

range_df = pd.DataFrame(range_counts)

fig, ax = plt.subplots(figsize=(10, 6))
colors = ['#2ecc71', '#27ae60', '#f39c12', '#e67e22', '#e74c3c', '#c0392b']
bars = ax.bar(range_df["range"], range_df["count"], color=colors, edgecolor='white', linewidth=1.5)

# Add labels
for bar, row in zip(bars, range_df.itertuples()):
    height = bar.get_height()
    ax.text(bar.get_x() + bar.get_width()/2., height + 5,
            f'{row.count}\n({row.pct:.1f}%)',
            ha='center', va='bottom', fontsize=11, fontweight='bold')

ax.set_xlabel("Token Range", fontsize=13)
ax.set_ylabel("Số lượng Điều", fontsize=13)
ax.set_title("📊 Phân bố Điều luật theo Token Range", fontsize=15, fontweight='bold')
ax.set_ylim(0, max(range_df["count"]) * 1.2)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/03_token_ranges.png", dpi=150, bbox_inches='tight')
print(f"   ✅ Saved: {OUTPUT_DIR}/03_token_ranges.png")
plt.close()

# ============================================================================
# FIGURE 4: Chapter Distribution (for BLLĐ)
# ============================================================================
print("📊 Creating Figure 4: Chapter distribution...")

bllđ = df[df["short_name"] == "BLLĐ"].copy()
if len(bllđ) > 0:
    # Extract chapter number
    bllđ["chapter_num"] = bllđ["chapter"].str.extract(r'Chương\s+([IVXLCDM]+|[0-9]+)', expand=False)
    chapter_counts = bllđ["chapter_num"].value_counts().head(15)
    
    fig, ax = plt.subplots(figsize=(12, 6))
    colors = sns.color_palette("viridis", len(chapter_counts))
    bars = ax.bar(chapter_counts.index, chapter_counts.values, color=colors, edgecolor='white')
    
    ax.set_xlabel("Chương", fontsize=13)
    ax.set_ylabel("Số lượng Điều", fontsize=13)
    ax.set_title("📖 Số Điều theo Chương - Bộ luật Lao động", fontsize=15, fontweight='bold')
    
    plt.tight_layout()
    plt.savefig(f"{OUTPUT_DIR}/04_bllđ_chapters.png", dpi=150, bbox_inches='tight')
    print(f"   ✅ Saved: {OUTPUT_DIR}/04_bllđ_chapters.png")
    plt.close()

# ============================================================================
# FIGURE 5: Summary Statistics Table
# ============================================================================
print("📊 Creating Figure 5: Summary statistics...")

stats = {
    "Tổng số văn bản": len(df["short_name"].unique()),
    "Tổng số Điều luật": len(df),
    "Min tokens": df["token_count"].min(),
    "Max tokens": df["token_count"].max(),
    "Mean tokens": round(df["token_count"].mean(), 1),
    "Median tokens": round(df["token_count"].median(), 1),
    "Total tokens": df["token_count"].sum(),
}

fig, ax = plt.subplots(figsize=(8, 4))
ax.axis('off')

table_data = [[k, v] for k, v in stats.items()]
table = ax.table(cellText=table_data, 
                 colLabels=["Metric", "Value"],
                 loc='center',
                 cellLoc='left',
                 colColours=['#3498db', '#3498db'])

table.auto_set_font_size(False)
table.set_fontsize(12)
table.scale(1.5, 2)

# Style header
for i in range(2):
    table[(0, i)].set_facecolor('#2c3e50')
    table[(0, i)].set_text_props(color='white', fontweight='bold')

plt.title("📋 Thống kê Dataset", fontsize=15, fontweight='bold', pad=20)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/05_summary_stats.png", dpi=150, bbox_inches='tight')
print(f"   ✅ Saved: {OUTPUT_DIR}/05_summary_stats.png")
plt.close()

# ============================================================================
# FIGURE 6: Document Type Pie Chart
# ============================================================================
print("📊 Creating Figure 6: Document type pie chart...")

fig, ax = plt.subplots(figsize=(8, 8))
doc_type_counts = df["doc_type"].value_counts()

colors = ['#3498db', '#e74c3c', '#2ecc71']
explode = [0.02] * len(doc_type_counts)

wedges, texts, autotexts = ax.pie(doc_type_counts.values, 
                                   labels=doc_type_counts.index,
                                   autopct='%1.1f%%',
                                   colors=colors[:len(doc_type_counts)],
                                   explode=explode,
                                   shadow=True,
                                   startangle=90)

for autotext in autotexts:
    autotext.set_fontsize(12)
    autotext.set_fontweight('bold')

ax.set_title("📊 Phân loại Văn bản Pháp luật", fontsize=15, fontweight='bold')

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/06_doc_type_pie.png", dpi=150, bbox_inches='tight')
print(f"   ✅ Saved: {OUTPUT_DIR}/06_doc_type_pie.png")
plt.close()

# ============================================================================
# Print Summary
# ============================================================================
print("\n" + "="*60)
print("📊 EDA COMPLETION SUMMARY")
print("="*60)
print(f"\n📁 Output directory: {OUTPUT_DIR}")
print(f"📄 Generated {len(os.listdir(OUTPUT_DIR))} figures")
print(f"\n📈 Dataset Statistics:")
for k, v in stats.items():
    print(f"   {k}: {v}")

print("\n✅ All figures generated successfully!")
print("="*60)
