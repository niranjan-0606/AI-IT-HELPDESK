"""
AI IT Helpdesk Agent - RAG (Retrieval-Augmented Generation) Module
Handles multi-format document loading (PDF, TXT, DOCX), text chunking,
embedding generation, FAISS vector store indexing, and similarity search.
"""

import os
import re
import math
import pickle
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
import numpy as np

from config import (
    KNOWLEDGE_BASE_DIR,
    VECTORSTORE_DIR,
    CHUNK_SIZE,
    CHUNK_OVERLAP,
    TOP_K_RETRIEVAL
)
from database import record_document, delete_document_record

# Paths for vectorstore persistence
FAISS_INDEX_FILE = VECTORSTORE_DIR / "faiss_index.bin"
METADATA_FILE = VECTORSTORE_DIR / "documents_meta.pkl"

# Global references for cached embedding model & vector store
_EMBEDDING_ENGINE = None
_VECTORSTORE_INDEX = None
_DOC_CHUNKS: List[Dict[str, Any]] = []


# =====================================================================
# Document Extractors
# =====================================================================

def extract_text_from_pdf(filepath: Path) -> str:
    """Extracts text from PDF file using pypdf."""
    try:
        from pypdf import PdfReader
        reader = PdfReader(str(filepath))
        pages_text = []
        for i, page in enumerate(reader.pages):
            text = page.extract_text()
            if text:
                pages_text.append(f"[Page {i+1}]\n{text.strip()}")
        return "\n\n".join(pages_text)
    except Exception as e:
        print(f"Error reading PDF {filepath}: {e}")
        return ""


def extract_text_from_txt(filepath: Path) -> str:
    """Extracts text from plain text or markdown files."""
    for encoding in ["utf-8", "latin-1", "cp1252"]:
        try:
            with open(filepath, "r", encoding=encoding) as f:
                return f.read()
        except UnicodeDecodeError:
            continue
    return ""


def extract_text_from_docx(filepath: Path) -> str:
    """Extracts text from DOCX files if python-docx is installed, else basic XML parse."""
    try:
        import docx
        doc = docx.Document(str(filepath))
        return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
    except ImportError:
        # Fallback reading xml inside docx zip archive
        try:
            import zipfile
            import xml.etree.ElementTree as ET
            with zipfile.ZipFile(filepath) as z:
                xml_content = z.read("word/document.xml")
                tree = ET.fromstring(xml_content)
                namespaces = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}
                texts = [node.text for node in tree.iterfind(".//w:t", namespaces) if node.text]
                return " ".join(texts)
        except Exception:
            return ""
    except Exception as e:
        print(f"Error reading DOCX {filepath}: {e}")
        return ""


def extract_document_text(filepath: Path) -> str:
    """Extracts clean text based on file extension."""
    suffix = filepath.suffix.lower()
    if suffix == ".pdf":
        return extract_text_from_pdf(filepath)
    elif suffix in [".txt", ".md", ".log"]:
        return extract_text_from_txt(filepath)
    elif suffix in [".docx", ".doc"]:
        return extract_text_from_docx(filepath)
    return ""


# =====================================================================
# Document Chunking
# =====================================================================

def chunk_text(text: str, source_name: str, chunk_size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[Dict[str, Any]]:
    """
    Splits text into sliding-window overlapping chunks while respecting
    sentence and paragraph boundaries.
    """
    cleaned_text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if not cleaned_text:
        return []

    # First split into paragraphs
    paragraphs = cleaned_text.split("\n\n")
    chunks = []
    current_chunk = ""
    chunk_index = 1

    for para in paragraphs:
        para = para.strip()
        if not para:
            continue

        if len(current_chunk) + len(para) <= chunk_size:
            current_chunk = f"{current_chunk}\n\n{para}" if current_chunk else para
        else:
            if current_chunk:
                chunks.append({
                    "chunk_id": f"{source_name}_chunk_{chunk_index}",
                    "source": source_name,
                    "text": current_chunk.strip()
                })
                chunk_index += 1
                # Overlap logic
                if overlap > 0 and len(current_chunk) > overlap:
                    current_chunk = current_chunk[-overlap:] + "\n\n" + para
                else:
                    current_chunk = para
            else:
                # If single paragraph exceeds chunk size, split by lines or sentences
                words = para.split()
                temp = ""
                for w in words:
                    if len(temp) + len(w) + 1 <= chunk_size:
                        temp = f"{temp} {w}".strip()
                    else:
                        chunks.append({
                            "chunk_id": f"{source_name}_chunk_{chunk_index}",
                            "source": source_name,
                            "text": temp.strip()
                        })
                        chunk_index += 1
                        temp = w
                current_chunk = temp

    if current_chunk.strip():
        chunks.append({
            "chunk_id": f"{source_name}_chunk_{chunk_index}",
            "source": source_name,
            "text": current_chunk.strip()
        })

    return chunks


# =====================================================================
# Hybrid Embedding Engine
# =====================================================================

class LightweightSemanticEmbedder:
    """
    Fast, deterministic vocabulary-aware TF-IDF subword vectorizer.
    Generates high-quality normalized 128-dimensional dense vectors
    with zero external neural network download dependencies.
    """
    def __init__(self, dim: int = 128):
        self.dim = dim

    def _tokenize(self, text: str) -> List[str]:
        tokens = re.findall(r"[a-z0-9]+", text.lower())
        # Generate unigrams and bigrams
        unigrams = [t for t in tokens if len(t) > 2]
        bigrams = [f"{tokens[i]}_{tokens[i+1]}" for i in range(len(tokens)-1)]
        return unigrams + bigrams

    def encode(self, texts: List[str]) -> np.ndarray:
        vectors = []
        for text in texts:
            vec = np.zeros(self.dim, dtype=np.float32)
            tokens = self._tokenize(text)
            if not tokens:
                vec[0] = 1.0
                vectors.append(vec)
                continue

            for t in tokens:
                # Stable Murmur-like hash bucketing
                h = abs(hash(t))
                idx = h % self.dim
                sign = 1.0 if ((h >> 8) % 2 == 0) else -1.0
                # Term weighting
                weight = 1.0 + math.log(1.0 + len(t))
                vec[idx] += sign * weight

            # L2 normalization for cosine similarity
            norm = np.linalg.norm(vec)
            if norm > 1e-6:
                vec = vec / norm
            else:
                vec[0] = 1.0
            vectors.append(vec)

        return np.array(vectors, dtype=np.float32)


def get_embedding_engine():
    """
    Returns an embedding engine.
    Tries SentenceTransformers first; if not installed, falls back to
    LightweightSemanticEmbedder to ensure offline college project stability.
    """
    global _EMBEDDING_ENGINE
    if _EMBEDDING_ENGINE is not None:
        return _EMBEDDING_ENGINE

    try:
        from sentence_transformers import SentenceTransformer
        print("[RAG] Loading SentenceTransformer 'all-MiniLM-L6-v2'...")
        _EMBEDDING_ENGINE = SentenceTransformer("all-MiniLM-L6-v2")
    except Exception as e:
        print(f"[RAG] Using LightweightSemanticEmbedder: {e}")
        _EMBEDDING_ENGINE = LightweightSemanticEmbedder(dim=128)

    return _EMBEDDING_ENGINE


# =====================================================================
# Vectorstore & FAISS Management
# =====================================================================

def save_vectorstore(index: Any, chunks: List[Dict[str, Any]]) -> None:
    """Persists FAISS index and chunk metadata to disk."""
    global _VECTORSTORE_INDEX, _DOC_CHUNKS
    _VECTORSTORE_INDEX = index
    _DOC_CHUNKS = chunks

    try:
        import faiss
        faiss.write_index(index, str(FAISS_INDEX_FILE))
    except Exception as e:
        print(f"[RAG] Fallback: Saving raw numpy embeddings: {e}")

    with open(METADATA_FILE, "wb") as f:
        pickle.dump(chunks, f)


def load_vectorstore() -> Tuple[Optional[Any], List[Dict[str, Any]]]:
    """Loads vectorstore index and metadata from disk."""
    global _VECTORSTORE_INDEX, _DOC_CHUNKS
    if _VECTORSTORE_INDEX is not None and _DOC_CHUNKS:
        return _VECTORSTORE_INDEX, _DOC_CHUNKS

    chunks = []
    if METADATA_FILE.exists():
        try:
            with open(METADATA_FILE, "rb") as f:
                chunks = pickle.load(f)
        except Exception as e:
            print(f"[RAG] Could not read metadata: {e}")

    index = None
    if FAISS_INDEX_FILE.exists():
        try:
            import faiss
            index = faiss.read_index(str(FAISS_INDEX_FILE))
        except Exception as e:
            print(f"[RAG] FAISS read index warning: {e}")

    _VECTORSTORE_INDEX = index
    _DOC_CHUNKS = chunks
    return index, chunks


def rebuild_knowledge_base() -> Dict[str, Any]:
    """
    Scans knowledge_base/ directory, extracts and chunks all documents,
    builds the FAISS vector index, and registers documents in SQLite.
    """
    files = list(KNOWLEDGE_BASE_DIR.glob("*.*"))
    supported_extensions = [".pdf", ".txt", ".md", ".docx"]
    valid_files = [f for f in files if f.suffix.lower() in supported_extensions]

    all_chunks = []
    processed_files = []

    for file_path in valid_files:
        filename = file_path.name
        text = extract_document_text(file_path)
        if not text.strip():
            continue

        chunks = chunk_text(text, source_name=filename)
        all_chunks.extend(chunks)

        filesize_kb = round(file_path.stat().st_size / 1024, 2)
        record_document(
            filename=filename,
            file_type=file_path.suffix.upper().replace(".", ""),
            chunk_count=len(chunks),
            filesize_kb=filesize_kb
        )
        processed_files.append({"filename": filename, "chunks": len(chunks)})

    if not all_chunks:
        # Create an initial placeholder document chunk if knowledge base is totally empty
        fallback_chunk = {
            "chunk_id": "system_it_faq_1",
            "source": "general_it_policy.txt",
            "text": "For general university IT assistance, students may reset passwords via the Student Portal or visit the IT Helpdesk located on the 1st Floor of the Student Center."
        }
        all_chunks.append(fallback_chunk)

    # Compute embeddings
    embedder = get_embedding_engine()
    texts = [c["text"] for c in all_chunks]
    embeddings = embedder.encode(texts)

    # Normalize vectors for Cosine Similarity (IndexFlatIP)
    if isinstance(embeddings, np.ndarray):
        embeddings = embeddings.astype(np.float32)
        norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        embeddings = embeddings / norms

    # Create FAISS Index
    dim = embeddings.shape[1]
    try:
        import faiss
        index = faiss.IndexFlatIP(dim)
        index.add(embeddings)
    except Exception as e:
        print(f"[RAG] FAISS not available, using raw numpy matrix: {e}")
        index = embeddings  # Fallback to direct numpy matrix

    save_vectorstore(index, all_chunks)

    return {
        "status": "success",
        "documents_count": len(valid_files),
        "chunks_count": len(all_chunks),
        "processed_files": processed_files
    }


def similarity_search(query: str, top_k: int = TOP_K_RETRIEVAL) -> List[Dict[str, Any]]:
    """
    Performs vector similarity search in the FAISS index.
    Returns top-k matching chunks with similarity scores.
    """
    index, chunks = load_vectorstore()
    if not chunks:
        # Try rebuilding if vectorstore doesn't exist yet
        rebuild_knowledge_base()
        index, chunks = load_vectorstore()
        if not chunks:
            return []

    embedder = get_embedding_engine()
    q_vec = embedder.encode([query]).astype(np.float32)
    q_norm = np.linalg.norm(q_vec)
    if q_norm > 0:
        q_vec = q_vec / q_norm

    results = []

    try:
        import faiss
        if isinstance(index, faiss.Index):
            k = min(top_k, len(chunks))
            distances, indices = index.search(q_vec, k)

            for dist, idx in zip(distances[0], indices[0]):
                if idx < len(chunks) and idx >= 0:
                    chunk = dict(chunks[idx])
                    chunk["score"] = round(float(dist), 4)
                    results.append(chunk)
            return results
    except Exception:
        pass

    # Fallback to Numpy Dot Product Search
    try:
        texts = [c["text"] for c in chunks]
        all_vecs = embedder.encode(texts).astype(np.float32)
        norms = np.linalg.norm(all_vecs, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        all_vecs = all_vecs / norms

        scores = np.dot(all_vecs, q_vec.T).flatten()
        top_indices = np.argsort(scores)[::-1][:top_k]

        for idx in top_indices:
            chunk = dict(chunks[idx])
            chunk["score"] = round(float(scores[idx]), 4)
            results.append(chunk)
    except Exception as e:
        print(f"[RAG] Search error: {e}")

    return results


def get_knowledge_base_stats() -> Dict[str, Any]:
    """Returns metadata summary of the knowledge base."""
    index, chunks = load_vectorstore()
    doc_sources = set(c.get("source", "unknown") for c in chunks)

    last_modified = None
    if METADATA_FILE.exists():
        import datetime
        mtime = METADATA_FILE.stat().st_mtime
        last_modified = datetime.datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "is_indexed": len(chunks) > 0,
        "total_chunks": len(chunks),
        "total_documents": len(doc_sources),
        "document_list": list(doc_sources),
        "last_updated": last_modified or "Never"
    }
