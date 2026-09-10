"""
AI IT Helpdesk Agent - Conversation Memory Module
Manages multi-turn conversation sessions, context windows, and persistence.
"""

import uuid
from typing import List, Dict, Any, Optional
from database import save_message, get_conversation_history, clear_conversation


class ConversationMemory:
    """Session-based conversation memory with SQLite backing."""

    def __init__(self, session_id: Optional[str] = None):
        self.session_id = session_id or str(uuid.uuid4())

    def add_user_message(self, content: str) -> None:
        """Records a user prompt in the session history."""
        save_message(
            session_id=self.session_id,
            role="user",
            content=content
        )

    def add_assistant_message(
        self,
        content: str,
        category: Optional[str] = None,
        priority: Optional[str] = None,
        tool_called: Optional[str] = None,
        tool_result: Optional[Any] = None,
        sources: Optional[List[str]] = None
    ) -> None:
        """Records an AI agent response turn."""
        save_message(
            session_id=self.session_id,
            role="assistant",
            content=content,
            category=category,
            priority=priority,
            tool_called=tool_called,
            tool_result=tool_result,
            sources=sources or []
        )

    def get_messages(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves ordered conversation history for the current session."""
        return get_conversation_history(self.session_id, limit=limit)

    def clear(self) -> None:
        """Clears memory for this session."""
        clear_conversation(self.session_id)

    def export_as_markdown(self) -> str:
        """Exports the transcript as readable markdown for support ticket attachment."""
        messages = self.get_messages(limit=100)
        if not messages:
            return "No conversation history recorded."

        lines = [f"# IT Helpdesk Conversation Transcript\nSession ID: `{self.session_id}`\n"]
        for m in messages:
            role_title = "👤 **User**" if m["role"] == "user" else "🤖 **AI IT Agent**"
            ts = m.get("timestamp", "")
            lines.append(f"### {role_title} ({ts})")
            if m.get("category"):
                lines.append(f"*Category: {m['category']} | Priority: {m.get('priority', 'N/A')}*")
            lines.append(f"\n{m['content']}\n")
            if m.get("tool_called"):
                lines.append(f"> ⚙️ Diagnostic Tool Executed: `{m['tool_called']}`\n")
            if m.get("sources"):
                lines.append(f"> 📚 Sources: {', '.join(m['sources'])}\n")
            lines.append("---\n")
        return "\n".join(lines)
