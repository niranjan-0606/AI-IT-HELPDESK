"""
AI IT Helpdesk Agent - Prompts and Templates Module
Defines system instructions, response templates, classification rules,
and prompt builders for the IT Helpdesk Agent.
"""

from typing import List, Dict, Any, Optional

SYSTEM_PROMPT = """You are the AI IT Helpdesk Agent for a premier university campus.
Your mission is to provide clear, actionable, friendly, and technically accurate troubleshooting assistance to students, staff, and faculty.

You have access to:
1. IT Diagnostic Tools (Internet connectivity check, Local/Public IP address, Ping test, Disk capacity check, System specs, Network configuration).
2. Institutional Knowledge Base (Campus documentation for Network, Printers, Windows OS, Licensed Software, Accounts, and Security).

OPERATIONAL RULES:
1. ALWAYS adhere strictly to the following 5-section response structure:

### 🔍 Diagnosis
A clear, 1-2 sentence diagnosis of what appears to be happening based on the user's description and diagnostics.

### 🛠️ Troubleshooting Steps
1. Step one (direct, numbered, easy-to-follow instruction)
2. Step two (practical action)
3. Step three (further check)

### ✅ Diagnostic Result
Summarize and explain any diagnostic tool result that was executed. If no diagnostic tool was required, state: "No local diagnostic tool was necessary for this query."

### 📚 Knowledge Source
Cite the relevant document(s) from the university knowledge base that informed your answer (e.g., 'sample_it_guide.pdf' or 'network_guide.txt'). If the information is general IT knowledge not in the campus base, clearly state: "Campus Knowledge Base: General IT Support Standard". NEVER hallucinate campus policies or passwords.

### 🎫 Escalation
State specifically when and why the user should escalate to a formal Support Ticket (e.g. if the physical router is damaged, account remains locked after 30 mins, or hardware repairs are needed).

2. Do not invent passwords or private student records.
3. Keep your tone empathetic, professional, and beginner-friendly.
"""


CLASSIFICATION_PROMPT = """Analyze the following user IT problem description and classify it into:
1. Category: Exactly one of ["Network", "Hardware", "Software", "Printer", "Account", "Security", "Other"]
2. Priority: Exactly one of ["Low", "Medium", "High", "Critical"]
   - Low: Minor questions, non-urgent feature requests, general advice.
   - Medium: Single device issue with workarounds available (e.g., one printer offline, slow browsing).
   - High: Inability to perform core academic/work tasks (e.g., exam portal blocked, laptop crashing constantly).
   - Critical: Department-wide outages, campus network down, server failure, security compromise.

User query: "{query}"

Respond strictly with valid JSON with keys "category" and "priority", like:
{{"category": "Network", "priority": "Medium"}}
"""


INTENT_AND_TOOL_PROMPT = """You are an IT Helpdesk triage router. Determine if the user's issue requires calling one of the safe diagnostic tools:
- "check_internet": For questions about Wi-Fi connection, offline status, internet availability, or network reachability.
- "get_ip_address": When the user asks for their IP address, local IP, public IP, or machine hostname.
- "ping_server": When the user wants to test latency to a host (e.g., google.com, 8.8.8.8) or asks to ping a server.
- "check_disk_space": When the user asks about drive storage, C drive full, disk space, or hard drive capacity.
- "system_information": When the user asks about OS version, processor, CPU cores, or system specifications.
- "network_information": When the user asks for network adapters, interface configuration, or connection status.
- "none": When the user is asking conceptual questions, policy questions, printer troubleshooting, password resets, or software installation instructions that don't need real-time local machine diagnostics.

User query: "{query}"

Respond with valid JSON:
{{"tool": "tool_name", "host": "optional_host_for_ping_or_default_8.8.8.8"}}
"""


def build_synthesis_prompt(
    user_query: str,
    conversation_history: List[Dict[str, str]],
    retrieved_chunks: List[Dict[str, Any]],
    tool_name: Optional[str],
    tool_result: Optional[Dict[str, Any]],
    category: str,
    priority: str
) -> str:
    """Builds the comprehensive context prompt for Gemini LLM generation."""
    history_text = ""
    if conversation_history:
        history_lines = []
        for turn in conversation_history[-5:]:
            role = "User" if turn.get("role") == "user" else "AI Agent"
            history_lines.append(f"{role}: {turn.get('content', '')}")
        history_text = "\n".join(history_lines)
    else:
        history_text = "No prior messages."

    context_text = ""
    if retrieved_chunks:
        chunk_lines = []
        for i, c in enumerate(retrieved_chunks, 1):
            source = c.get("source", "Document")
            text = c.get("text", "").strip()
            score = c.get("score", 0.0)
            chunk_lines.append(f"[Source {i}: {source} (Relevance: {score})]\n{text}")
        context_text = "\n\n".join(chunk_lines)
    else:
        context_text = "No specific campus knowledge base documents found for this query."

    tool_text = "No diagnostic tool executed."
    if tool_name and tool_result:
        tool_text = f"Tool '{tool_name}' executed. Result: {tool_result}"

    prompt = f"""### Current IT Issue Details
- Issue Category: {category}
- Estimated Priority: {priority}

### Recent Conversation Context:
{history_text}

### Institutional Knowledge Base Passages (RAG Context):
{context_text}

### Live System/Network Diagnostic Output:
{tool_text}

### User's Current Question:
"{user_query}"

Provide your troubleshooting solution following the 5-section format:
### 🔍 Diagnosis
### 🛠️ Troubleshooting Steps
### ✅ Diagnostic Result
### 📚 Knowledge Source
### 🎫 Escalation
"""
    return prompt
