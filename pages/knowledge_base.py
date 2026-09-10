"""
AI IT Helpdesk Agent - Knowledge Base Page
Allows uploading institutional IT documentation (PDF, TXT, DOCX),
viewing chunk statistics, rebuilding the FAISS vector database,
and interactively testing similarity search.
"""

from pathlib import Path
import streamlit as st
import pandas as pd

from config import KNOWLEDGE_BASE_DIR
from rag import (
    rebuild_knowledge_base,
    get_knowledge_base_stats,
    similarity_search,
    extract_document_text
)
from database import get_indexed_documents
from utils.helpers import inject_custom_css, render_header


def render_knowledge_base():
    """Renders the knowledge base management and search UI."""
    inject_custom_css()

    render_header(
        title="📚 Campus IT Knowledge Base (RAG)",
        subtitle="Manage documentation, inspect vector embeddings, and test similarity retrieval"
    )

    # Fetch stats
    kb_stats = get_knowledge_base_stats()

    # Knowledge Base Overview Metrics
    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.metric("📄 Total Documents", kb_stats["total_documents"])
    with c2:
        st.metric("🧩 Indexed Chunks", kb_stats["total_chunks"])
    with c3:
        st.metric("⚡ Vector Store Status", "FAISS Ready" if kb_stats["is_indexed"] else "Empty")
    with c4:
        st.metric("🕒 Last Indexed", kb_stats["last_updated"])

    st.markdown("---")

    # Document Ingestion & Rebuild Controls
    col_upload, col_rebuild = st.columns([2, 1])

    with col_upload:
        st.subheader("📤 Upload New IT Guide")
        uploaded_file = st.file_uploader(
            "Upload PDF, TXT, or DOCX document",
            type=["pdf", "txt", "docx", "md"],
            help="The document will be automatically chunked and indexed into the FAISS vector store."
        )

        if uploaded_file is not None:
            if st.button("Save & Index Document", type="primary"):
                save_path = KNOWLEDGE_BASE_DIR / uploaded_file.name
                with open(save_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())

                with st.spinner(f"Ingesting '{uploaded_file.name}' and updating FAISS vector store..."):
                    res = rebuild_knowledge_base()
                    st.success(f"Successfully added '{uploaded_file.name}'! Total chunks indexed: {res['chunks_count']}.")
                    st.rerun()

    with col_rebuild:
        st.subheader("🔄 Rebuild Index")
        st.write("Re-scan all documents in `knowledge_base/` and regenerate vector embeddings.")
        if st.button("Rebuild Knowledge Base", use_container_width=True):
            with st.spinner("Processing documents and calculating embeddings..."):
                res = rebuild_knowledge_base()
                st.success(f"Knowledge Base Rebuilt! {res['documents_count']} files, {res['chunks_count']} total chunks.")
                st.rerun()

    st.markdown("---")

    # Interactive RAG Retrieval Sandbox
    st.subheader("🔍 Interactive RAG Search Sandbox")
    st.write("Test what context chunks the AI Agent will retrieve for any IT inquiry before generating an answer.")

    search_query = st.text_input(
        "Enter a test troubleshooting question:",
        placeholder="e.g., What should I do if the printer is offline? or How do I reset my password?"
    )

    if search_query:
        with st.spinner("Searching FAISS vector database..."):
            retrieved_chunks = similarity_search(search_query, top_k=3)

        if retrieved_chunks:
            st.markdown(f"**Retrieved {len(retrieved_chunks)} Relevant Document Chunks:**")
            for i, chunk in enumerate(retrieved_chunks, 1):
                score = chunk.get("score", 0.0)
                st.markdown(f"""
                    <div class="tool-output-box">
                        <strong>Rank {i} | Source: <code>{chunk.get('source')}</code></strong> 
                        <span style="float:right; font-weight:600; color:#2563EB;">Similarity Score: {score}</span>
                        <hr style="margin: 8px 0; border: none; border-top: 1px solid #CBD5E1;" />
                        <div style="font-size:0.9rem; line-height:1.5;">{chunk.get('text')}</div>
                    </div>
                """, unsafe_allow_html=True)
        else:
            st.warning("No matching document chunks found in the vector database.")

    st.markdown("---")

    # Indexed Documents Table
    st.subheader("📁 Repository Documents")
    indexed_docs = get_indexed_documents()

    if indexed_docs:
        df_docs = pd.DataFrame(indexed_docs)
        df_docs = df_docs.rename(columns={
            "filename": "File Name",
            "file_type": "Type",
            "chunk_count": "Chunks",
            "filesize_kb": "Size (KB)",
            "uploaded_at": "Indexed Date"
        })
        st.dataframe(df_docs[["File Name", "Type", "Chunks", "Size (KB)", "Indexed Date"]], use_container_width=True)

        # Document previewer
        st.markdown("##### 👁️ Document Quick Preview")
        selected_doc = st.selectbox("Select document to preview content:", [d["File Name"] for d in df_docs.to_dict(orient="records")])
        if selected_doc:
            doc_path = KNOWLEDGE_BASE_DIR / selected_doc
            if doc_path.exists():
                preview_text = extract_document_text(doc_path)
                with st.expander(f"Preview: {selected_doc}", expanded=False):
                    st.text_area("Content", preview_text[:2000] + ("\n... [truncated]" if len(preview_text) > 2000 else ""), height=200, disabled=True)
    else:
        st.info("No documents currently recorded in the database. Click 'Rebuild Knowledge Base' to index initial sample documents.")


try:
    st.set_page_config(page_title="IT Helpdesk - Knowledge Base", page_icon="📚", layout="wide")
except Exception:
    pass

render_knowledge_base()
