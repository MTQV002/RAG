import json
from pathlib import Path
from llama_index.core import Document, VectorStoreIndex, StorageContext, Settings
from llama_index.core.node_parser import SentenceSplitter
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from dotenv import load_dotenv
import os
from typing import List, Dict

# Auto-resolve paths from script location
SCRIPT_DIR = Path(__file__).parent.resolve()
JSON_FILE_PATH = SCRIPT_DIR / "legal_decrees.json"
HF_CACHE_DIR = SCRIPT_DIR / "hf_cache"
ENV_FILE = SCRIPT_DIR / ".env"
DENSE_MODEL_NAME = "AITeamVN/Vietnamese_Embedding" 
SPARSE_MODEL_NAME = "Qdrant/bm25"

# ===== CHUNK SETTINGS =====
CHUNK_SIZE =  10000
CHUNK_OVERLAP = 0  

# ===== NEW COLLECTION NAME00000 =====
NEW_COLLECTION_NAME = "legal_decrees_LBV"


def load_data(json_path: str) -> List[Dict]:
    with open(json_path, 'r', encoding='utf-8') as f:
        data_list = json.load(f)
    print(f"Loaded: {len(data_list)} documents")
    return data_list


def create_documents(data_list: List[Dict]) -> List[Document]:
    documents = []
    for item in data_list:
        metadata = item.get('metadata', {})
        doc = Document(
            text=item.get('page_content', ''),
            metadata={
                "doc_type": metadata.get('doc_type', ''),
                "doc_number": metadata.get('doc_number', ''),
                "doc_name": metadata.get('doc_name', ''),
                "short_name": metadata.get('short_name', ''),
                "chapter": metadata.get('chapter', ''),
                "article_id": metadata.get('article_id', ''),
                "article_title": metadata.get('article_title', ''),
                "effective_date": metadata.get('effective_date', ''),
                "status": metadata.get('status', ''),
                "references": json.dumps(metadata.get('references', []), ensure_ascii=False),
            },
            excluded_llm_metadata_keys=['doc_number', 'short_name', 'references', 'status', 'effective_date'], 
            excluded_embed_metadata_keys=['doc_number', 'short_name', 'article_id', 'references', 'effective_date', 'status'] 
        )
        documents.append(doc)
    return documents


def index_to_qdrant(
    documents: List[Document],
    url: str,
    api_key: str,
    collection_name: str
) -> VectorStoreIndex:
    embed_model = HuggingFaceEmbedding(
        model_name=DENSE_MODEL_NAME, 
        cache_folder=str(HF_CACHE_DIR)
    )
    Settings.embed_model = embed_model
    Settings.llm = None
    
    # ===== DISABLE CHUNKING =====
    # Set chunk_size large enough so each article = 1 node
    Settings.node_parser = SentenceSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP
    )
    print(f"📦 Chunk settings: size={CHUNK_SIZE}, overlap={CHUNK_OVERLAP}")
    
    print(f"\n{'='*50}")
    print(f"Indexing {len(documents)} documents to '{collection_name}'")
    print(f"{'='*50}")
    
    vector_store = QdrantVectorStore(
        url=url,
        api_key=api_key, 
        collection_name=collection_name,
        enable_hybrid=True,
        fastembed_sparse_model=SPARSE_MODEL_NAME,
    )
    storage_context = StorageContext.from_defaults(vector_store=vector_store)
    
    index = VectorStoreIndex.from_documents(
        documents,
        storage_context=storage_context,
        show_progress=True
    )
    
    print(f"Done indexing '{collection_name}'")
    return index


def main():
    load_dotenv(ENV_FILE)
    
    QDRANT_URL = os.getenv('QDRANT_URL')
    QDRANT_API_KEY = os.getenv('QDRANT_API_KEY')
    # Use new collection name
    COLLECTION_NAME = NEW_COLLECTION_NAME
    
    print(f"Qdrant URL: {QDRANT_URL}")
    print(f"Collection: {COLLECTION_NAME}")
    print(f"Data file: {JSON_FILE_PATH}")
    print(f"Chunk size: {CHUNK_SIZE} tokens (no chunking)")
    
    data = load_data(str(JSON_FILE_PATH))
    documents = create_documents(data)
    
    index = index_to_qdrant(
        documents=documents,
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY,
        collection_name=COLLECTION_NAME
    )
    
    print("\n" + "="*50)
    print("ALL DONE!")
    print(f"Collection '{COLLECTION_NAME}': {len(documents)} documents")
    print("="*50)


if __name__ == "__main__":
    main()
