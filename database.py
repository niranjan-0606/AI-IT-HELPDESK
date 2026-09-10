"""
AI IT Helpdesk Agent - Database Module
SQLite persistence for conversation history, support tickets, and knowledge base tracking.
"""

import sqlite3
import json
from datetime import datetime
from typing import List, Dict, Any, Optional
from config import DB_PATH


def get_connection() -> sqlite3.Connection:
    """Returns a SQLite connection configured for row-dict access."""
    conn = sqlite3.connect(str(DB_PATH), check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    """Initializes all database tables and default sample tickets if empty."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # 1. Conversations Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                category TEXT,
                priority TEXT,
                tool_called TEXT,
                tool_result TEXT,
                sources TEXT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # 2. Support Tickets Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id TEXT PRIMARY KEY,
                user_name TEXT NOT NULL,
                email TEXT,
                title TEXT NOT NULL,
                description TEXT NOT NULL,
                category TEXT NOT NULL,
                priority TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'Open',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                resolution_notes TEXT
            )
        """)

        # 3. Knowledge Base Documents Table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS knowledge_docs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT UNIQUE NOT NULL,
                file_type TEXT NOT NULL,
                chunk_count INTEGER DEFAULT 0,
                filesize_kb REAL DEFAULT 0.0,
                uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Seed initial sample tickets if table is empty
        cursor.execute("SELECT COUNT(*) FROM tickets")
        if cursor.fetchone()[0] == 0:
            sample_tickets = [
                (
                    "TICK-1001",
                    "Alex Mercer",
                    "alex.m@college.edu",
                    "Library 2nd Floor Wi-Fi Dropping",
                    "Laptops in the quiet study area repeatedly lose connection to Campus-WiFi.",
                    "Network",
                    "High",
                    "In Progress",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Investigating access point AP-LIB-02 signal strength."
                ),
                (
                    "TICK-1002",
                    "Dr. Sarah Jenkins",
                    "s.jenkins@college.edu",
                    "Lab Printer Printing Gibberish Characters",
                    "The HP LaserJet in CS Lab B prints 40 blank pages with random symbols.",
                    "Printer",
                    "Medium",
                    "Open",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    None
                ),
                (
                    "TICK-1003",
                    "Student Council Desk",
                    "council@college.edu",
                    "Password Reset Portal Account Locked",
                    "Student ID 2024982 locked after multiple failed attempts on Student SIS.",
                    "Account",
                    "Medium",
                    "Resolved",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Verified identity via student ID card and issued self-service temporary PIN."
                ),
                (
                    "TICK-1004",
                    "Prof. Robert Lang",
                    "rlang@college.edu",
                    "MATLAB Crash on Startup Error 0xC0000005",
                    "MATLAB R2024b crashes immediately after license verification on faculty PC.",
                    "Software",
                    "Critical",
                    "In Progress",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Reinstalling Visual C++ 2015-2022 redistributable dependencies."
                ),
                (
                    "TICK-1005",
                    "Maya Patel",
                    "mpatel@college.edu",
                    "C Drive Full Alert on Engineering Workstation",
                    "Workstation CAD-04 showing 200MB free space; unable to save SolidWorks files.",
                    "Hardware",
                    "Low",
                    "Resolved",
                    datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "Cleared 45GB temp render cache from %LOCALAPPDATA%\\Temp."
                )
            ]
            cursor.executemany("""
                INSERT INTO tickets (ticket_id, user_name, email, title, description, category, priority, status, created_at, resolution_notes)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, sample_tickets)

        conn.commit()


# =====================================================================
# Conversation Persistence
# =====================================================================

def save_message(
    session_id: str,
    role: str,
    content: str,
    category: Optional[str] = None,
    priority: Optional[str] = None,
    tool_called: Optional[str] = None,
    tool_result: Optional[Any] = None,
    sources: Optional[List[str]] = None
) -> int:
    """Saves a conversation turn to SQLite."""
    with get_connection() as conn:
        cursor = conn.cursor()
        tool_res_str = json.dumps(tool_result) if tool_result is not None else None
        sources_str = json.dumps(sources) if sources is not None else None

        cursor.execute("""
            INSERT INTO conversations (session_id, role, content, category, priority, tool_called, tool_result, sources)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (session_id, role, content, category, priority, tool_called, tool_res_str, sources_str))
        conn.commit()
        return cursor.lastrowid


def get_conversation_history(session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Retrieves conversation history for a given session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, session_id, role, content, category, priority, tool_called, tool_result, sources, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY id ASC
            LIMIT ?
        """, (session_id, limit))
        rows = cursor.fetchall()

        history = []
        for r in rows:
            history.append({
                "id": r["id"],
                "session_id": r["session_id"],
                "role": r["role"],
                "content": r["content"],
                "category": r["category"],
                "priority": r["priority"],
                "tool_called": r["tool_called"],
                "tool_result": json.loads(r["tool_result"]) if r["tool_result"] else None,
                "sources": json.loads(r["sources"]) if r["sources"] else [],
                "timestamp": r["timestamp"]
            })
        return history


def clear_conversation(session_id: str) -> None:
    """Deletes conversation history for a given session."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM conversations WHERE session_id = ?", (session_id,))
        conn.commit()


# =====================================================================
# Support Ticket Management
# =====================================================================

def generate_ticket_id() -> str:
    """Generates a sequential ticket ID (e.g. TICK-1006)."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM tickets")
        count = cursor.fetchone()[0]
        return f"TICK-{1001 + count}"


def create_ticket(
    user_name: str,
    email: str,
    title: str,
    description: str,
    category: str,
    priority: str,
    status: str = "Open"
) -> str:
    """Creates a new support ticket and returns the generated ticket_id."""
    ticket_id = generate_ticket_id()
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tickets (ticket_id, user_name, email, title, description, category, priority, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ticket_id, user_name, email, title, description, category, priority, status, now_str, now_str))
        conn.commit()
    return ticket_id


def get_all_tickets(
    status_filter: Optional[str] = None,
    category_filter: Optional[str] = None,
    priority_filter: Optional[str] = None,
    search_term: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Retrieves tickets with flexible filtering options."""
    query = "SELECT * FROM tickets WHERE 1=1"
    params = []

    if status_filter and status_filter != "All":
        query += " AND status = ?"
        params.append(status_filter)
    if category_filter and category_filter != "All":
        query += " AND category = ?"
        params.append(category_filter)
    if priority_filter and priority_filter != "All":
        query += " AND priority = ?"
        params.append(priority_filter)
    if search_term:
        query += " AND (title LIKE ? OR description LIKE ? OR user_name LIKE ? OR ticket_id LIKE ?)"
        wildcard = f"%{search_term}%"
        params.extend([wildcard, wildcard, wildcard, wildcard])

    query += " ORDER BY created_at DESC"

    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute(query, params)
        rows = cursor.fetchall()
        return [dict(r) for r in rows]


def get_ticket(ticket_id: str) -> Optional[Dict[str, Any]]:
    """Fetches a single ticket by ticket_id."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tickets WHERE ticket_id = ?", (ticket_id,))
        row = cursor.fetchone()
        return dict(row) if row else None


def update_ticket_status(ticket_id: str, new_status: str, notes: Optional[str] = None) -> bool:
    """Updates a ticket's status and optional resolution notes."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        if notes:
            cursor.execute("""
                UPDATE tickets
                SET status = ?, resolution_notes = ?, updated_at = ?
                WHERE ticket_id = ?
            """, (new_status, notes, now_str, ticket_id))
        else:
            cursor.execute("""
                UPDATE tickets
                SET status = ?, updated_at = ?
                WHERE ticket_id = ?
            """, (new_status, now_str, ticket_id))
        conn.commit()
        return cursor.rowcount > 0


# =====================================================================
# Document Tracking
# =====================================================================

def record_document(filename: str, file_type: str, chunk_count: int, filesize_kb: float) -> None:
    """Inserts or updates document record in the database."""
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO knowledge_docs (filename, file_type, chunk_count, filesize_kb, uploaded_at)
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(filename) DO UPDATE SET
                chunk_count = excluded.chunk_count,
                filesize_kb = excluded.filesize_kb,
                uploaded_at = excluded.uploaded_at
        """, (filename, file_type, chunk_count, filesize_kb, now_str))
        conn.commit()


def get_indexed_documents() -> List[Dict[str, Any]]:
    """Lists all indexed knowledge base documents."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM knowledge_docs ORDER BY uploaded_at DESC")
        return [dict(r) for r in cursor.fetchall()]


def delete_document_record(filename: str) -> bool:
    """Removes a document record."""
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("DELETE FROM knowledge_docs WHERE filename = ?", (filename,))
        conn.commit()
        return cursor.rowcount > 0


# =====================================================================
# Dashboard Analytics
# =====================================================================

def get_dashboard_metrics() -> Dict[str, Any]:
    """Aggregates all key KPIs for the dashboard."""
    with get_connection() as conn:
        cursor = conn.cursor()

        # Conversations count
        cursor.execute("SELECT COUNT(DISTINCT session_id) FROM conversations")
        total_conversations = cursor.fetchone()[0]

        # Ticket counts by status
        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Open'")
        open_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'In Progress'")
        in_progress_tickets = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM tickets WHERE status = 'Resolved'")
        resolved_tickets = cursor.fetchone()[0]

        # Total documents & total chunks
        cursor.execute("SELECT COUNT(*), COALESCE(SUM(chunk_count), 0) FROM knowledge_docs")
        doc_row = cursor.fetchone()
        total_docs = doc_row[0]
        total_chunks = doc_row[1]

        # Category distribution for tickets
        cursor.execute("SELECT category, COUNT(*) as count FROM tickets GROUP BY category ORDER BY count DESC")
        ticket_categories = [dict(r) for r in cursor.fetchall()]

        # Priority distribution for tickets
        cursor.execute("SELECT priority, COUNT(*) as count FROM tickets GROUP BY priority")
        ticket_priorities = [dict(r) for r in cursor.fetchall()]

        # Recent tickets
        cursor.execute("SELECT * FROM tickets ORDER BY created_at DESC LIMIT 5")
        recent_tickets = [dict(r) for r in cursor.fetchall()]

        # Recent conversation turns
        cursor.execute("""
            SELECT session_id, role, content, category, priority, timestamp
            FROM conversations
            WHERE role = 'user'
            ORDER BY timestamp DESC
            LIMIT 5
        """)
        recent_chats = [dict(r) for r in cursor.fetchall()]

        return {
            "total_conversations": total_conversations,
            "open_tickets": open_tickets,
            "in_progress_tickets": in_progress_tickets,
            "resolved_tickets": resolved_tickets,
            "total_docs": total_docs,
            "total_chunks": total_chunks,
            "ticket_categories": ticket_categories,
            "ticket_priorities": ticket_priorities,
            "recent_tickets": recent_tickets,
            "recent_chats": recent_chats
        }


# Initialize tables when imported
init_db()
