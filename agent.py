"""
AI IT Helpdesk Agent - Core Agent Module
Coordinates user intent detection, IT diagnostic tool calling,
RAG retrieval from FAISS, Gemini LLM generation, and offline simulation fallback.
"""

import os
import re
import json
from typing import Dict, Any, List, Optional, Tuple

from config import GOOGLE_API_KEY, DEFAULT_MODEL, CATEGORIES, PRIORITIES
from tools import execute_tool, TOOL_DEFINITIONS, is_safe_host
from rag import similarity_search
from prompts import SYSTEM_PROMPT, CLASSIFICATION_PROMPT, INTENT_AND_TOOL_PROMPT, build_synthesis_prompt


class AITTHelpdeskAgent:
    """Intelligent IT Helpdesk Agent with Tool Calling and RAG."""

    def __init__(self, api_key: Optional[str] = None, model_name: Optional[str] = None):
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY", "")
        self.model_name = model_name or DEFAULT_MODEL
        self._init_gemini_client()

    def _init_gemini_client(self) -> None:
        """Initializes Gemini API client if key is configured."""
        self.client = None
        self.using_new_sdk = False

        if not self.api_key or self.api_key == "your_gemini_api_key_here":
            return

        # Attempt modern google-genai SDK
        try:
            from google import genai
            self.client = genai.Client(api_key=self.api_key)
            self.using_new_sdk = True
            return
        except ImportError:
            pass
        except Exception as e:
            print(f"[Agent] Notice loading google.genai: {e}")

        # Fallback to google-generativeai SDK
        try:
            import google.generativeai as genai_legacy
            genai_legacy.configure(api_key=self.api_key)
            self.client = genai_legacy
            self.using_new_sdk = False
        except Exception as e:
            print(f"[Agent] Notice loading google.generativeai: {e}")

    def update_credentials(self, api_key: str, model_name: Optional[str] = None) -> None:
        """Updates the API credentials at runtime."""
        self.api_key = api_key
        if model_name:
            self.model_name = model_name
        self._init_gemini_client()

    # =================================================================
    # Issue Classification (Category & Priority)
    # =================================================================

    def classify_issue(self, query: str) -> Tuple[str, str]:
        """
        Classifies user query into Category and Priority.
        Uses Gemini if available, else sophisticated keyword heuristic.
        """
        if self.client:
            try:
                prompt = CLASSIFICATION_PROMPT.format(query=query)
                raw_resp = self._call_llm_simple(prompt)
                # Parse JSON
                json_match = re.search(r"\{.*?\}", raw_resp, re.DOTALL)
                if json_match:
                    data = json.loads(json_match.group(0))
                    cat = data.get("category", "Other")
                    prio = data.get("priority", "Medium")
                    if cat in CATEGORIES and prio in PRIORITIES:
                        return cat, prio
            except Exception as e:
                print(f"[Agent] LLM classification error: {e}")

        # Heuristic Rule-Based Classifier
        q = query.lower()

        # Priority rules
        if any(w in q for w in ["crash", "emergency", "fatal", "outage", "entire campus", "critical", "compromised", "hacked"]):
            prio = "Critical"
        elif any(w in q for w in ["exam", "cannot work", "deadline", "locked out", "urgent", "not working at all"]):
            prio = "High"
        elif any(w in q for w in ["slow", "disconnect", "issue", "problem", "error", "offline", "spooler"]):
            prio = "Medium"
        else:
            prio = "Low"

        # Category rules
        if any(w in q for w in ["printer", "print", "spooler", "paper", "toner", "laserjet", "queue"]):
            cat = "Printer"
        elif any(w in q for w in ["wifi", "wi-fi", "internet", "dns", "ping", "router", "ip", "ethernet", "network", "connect"]):
            cat = "Network"
        elif any(w in q for w in ["password", "sso", "login", "account", "mfa", "2fa", "canvas", "portal"]):
            cat = "Account"
        elif any(w in q for w in ["phish", "hacked", "virus", "malware", "security", "breach"]):
            cat = "Security"
        elif any(w in q for w in ["disk", "storage", "c drive", "hard drive", "ram", "memory", "processor", "hardware", "cpu", "laptop"]):
            cat = "Hardware"
        elif any(w in q for w in ["matlab", "autocad", "office", "word", "install", "app", "application", "software", "license"]):
            cat = "Software"
        else:
            cat = "Other"

        return cat, prio

    # =================================================================
    # Tool Intent Detection
    # =================================================================

    def detect_and_execute_tools(self, query: str) -> Tuple[Optional[str], Optional[Dict[str, Any]]]:
        """
        Determines whether any diagnostic tools should be triggered and runs them.
        """
        q = query.lower()

        # 1. IP Address
        if any(phrase in q for phrase in ["my ip", "ip address", "what is my ip", "show ip", "local ip", "public ip", "hostname"]):
            return "get_ip_address", execute_tool("get_ip_address")

        # 2. Disk Space
        if any(phrase in q for phrase in ["disk space", "storage", "c drive", "hard drive space", "how much disk", "free space", "space left"]):
            return "check_disk_space", execute_tool("check_disk_space")

        # 3. System Specs
        if any(phrase in q for phrase in ["system info", "specs", "specifications", "processor", "cpu core", "windows version", "os version"]):
            return "system_information", execute_tool("system_information")

        # 4. Ping Server
        if "ping" in q:
            # Extract target host if mentioned
            match = re.search(r"ping\s+([a-zA-Z0-9.-]+)", q)
            host = match.group(1) if match and is_safe_host(match.group(1)) else "8.8.8.8"
            return "ping_server", execute_tool("ping_server", host=host)

        # 5. Network Information
        if any(phrase in q for phrase in ["network info", "adapters", "network configuration", "adapter status"]):
            return "network_information", execute_tool("network_information")

        # 6. Internet Check
        if any(phrase in q for phrase in ["internet", "wifi", "wi-fi", "online", "connectivity", "connection", "no net"]):
            return "check_internet", execute_tool("check_internet")

        return None, None

    # =================================================================
    # LLM Calling Helper
    # =================================================================

    def _call_llm_simple(self, prompt: str) -> str:
        """Dispatches prompt to Gemini client."""
        if not self.client:
            return ""

        if self.using_new_sdk:
            response = self.client.models.generate_content(
                model=self.model_name,
                contents=prompt
            )
            return response.text
        else:
            model = self.client.GenerativeModel(self.model_name)
            response = model.generate_content(prompt)
            return response.text

    # =================================================================
    # Offline Intelligent Fallback Response Builder
    # =================================================================

    def _generate_fallback_response(
        self,
        query: str,
        category: str,
        priority: str,
        tool_name: Optional[str],
        tool_result: Optional[Dict[str, Any]],
        retrieved_chunks: List[Dict[str, Any]]
    ) -> str:
        """
        Generates a complete, helpful, structured IT response when Gemini API
        is offline or key is not provided, ensuring seamless college demo presentations.
        """
        # Diagnosis
        if tool_name == "check_internet" and tool_result and not tool_result.get("connected"):
            diagnosis = "Your local machine currently has no active route to external internet gateways. The wireless or Ethernet adapter is not receiving network traffic."
        elif tool_name == "check_disk_space" and tool_result and tool_result.get("percent_used", 0) > 85:
            diagnosis = f"Your primary system drive is critically low on space ({tool_result.get('free_gb')} GB remaining), which can stall updates and trigger application freezes."
        elif category == "Network":
            diagnosis = "The issue appears to be related to local network lease expiration, DNS resolution timeout, or campus Wi-Fi authentication handshake."
        elif category == "Printer":
            diagnosis = "The print queue or Windows Print Spooler service appears to have stalled, or the target printer is disconnected from the local subnet."
        elif category == "Account":
            diagnosis = "Your campus Single Sign-On (SSO) account credentials may have expired or triggered a temporary lockout following multiple login attempts."
        elif category == "Software":
            diagnosis = "The software is experiencing startup failure, likely caused by missing Microsoft C++ redistributables or insufficient execution permissions."
        else:
            diagnosis = f"Based on your report regarding '{query}', this is categorized as a {priority}-priority {category} support issue."

        # Troubleshooting Steps based on RAG chunks or knowledge base
        steps = []
        if category == "Network":
            steps = [
                "Open Command Prompt as Administrator and run `ipconfig /flushdns` to clear outdated domain caches.",
                "Execute `ipconfig /release` followed by `ipconfig /renew` to request a fresh DHCP IP address from the campus gateway.",
                "If on campus wireless, forget the network in Windows Wi-Fi settings, reboot the wireless adapter, and re-authenticate using `username@college.edu`."
            ]
        elif category == "Printer":
            steps = [
                "Verify the printer is powered on and both the power and network Ethernet LEDs show solid activity.",
                "Press Win + R, type `services.msc`, locate 'Print Spooler', right-click and click 'Restart'.",
                "Clear stuck printer documents by navigating to Control Panel > Devices & Printers and canceling pending jobs.",
                "If printing from home or dorm Wi-Fi, ensure your device is connected to the Campus GlobalProtect VPN."
            ]
        elif category == "Account":
            steps = [
                "Navigate to the University Self-Service portal at `https://account.college.edu/reset`.",
                "Request an SMS or email OTP verification code to reset your account credentials.",
                "Ensure your new password meets complexity rules: at least 12 characters including uppercase, lowercase, numbers, and special symbols.",
                "If your account was temporarily locked out due to 5 failed attempts, wait 30 minutes for the automatic security freeze to expire."
            ]
        elif category == "Software":
            steps = [
                "Right-click the application executable and select 'Run as Administrator'.",
                "Install the Microsoft Visual C++ 2015-2022 Redistributable bundle (x64 and x86) to address missing DLL errors.",
                "Check Task Manager (Ctrl + Shift + Esc) and ensure no zombie instances of the application are hung in background processes."
            ]
        else:
            steps = [
                "Perform a clean system reboot to clear transient memory locks and caches.",
                "Check Windows Event Viewer (eventvwr.msc) for application error codes and event IDs.",
                "Verify that your system meets the recommended memory and disk space requirements."
            ]

        # Diagnostic Explanation
        if tool_name and tool_result:
            if tool_name == "check_internet":
                diag_text = f"Executed Internet Connectivity Check. Status: **{tool_result.get('status')}** (Latency: {tool_result.get('latency_ms')} ms, DNS Resolving: {tool_result.get('dns_resolving')})."
            elif tool_name == "get_ip_address":
                diag_text = f"Local Device Address: `{tool_result.get('local_ip')}` | Hostname: `{tool_result.get('hostname')}` | Public IP: `{tool_result.get('public_ip')}`."
            elif tool_name == "ping_server":
                diag_text = f"Pinged host `{tool_result.get('host')}`: Success: {tool_result.get('success')}, Avg Latency: {tool_result.get('latency_ms')} ms, Packet Loss: {tool_result.get('packet_loss_pct')}%."
            elif tool_name == "check_disk_space":
                diag_text = f"Drive `{tool_result.get('path')}`: {tool_result.get('free_gb')} GB free of {tool_result.get('total_gb')} GB ({tool_result.get('percent_used')}% used). Status: {tool_result.get('health_status')}."
            elif tool_name == "system_information":
                diag_text = f"System Specs: {tool_result.get('os')} {tool_result.get('os_release')} ({tool_result.get('architecture')}) on {tool_result.get('cpu_cores')} CPU cores."
            elif tool_name == "network_information":
                diag_text = f"Network status: {tool_result.get('message')} with local IP `{tool_result.get('local_ip')}`."
            else:
                diag_text = f"Executed diagnostic tool `{tool_name}`: {tool_result}"
        else:
            diag_text = "No local diagnostic tool was necessary for this inquiry."

        # Knowledge Source
        sources = [c.get("source", "sample_it_guide.pdf") for c in retrieved_chunks] if retrieved_chunks else ["sample_it_guide.pdf"]
        unique_sources = list(dict.fromkeys(sources))
        source_text = f"Institutional Knowledge Base: {', '.join(unique_sources)}"

        # Escalation
        escalation = (
            f"If the problem persists after following these steps, click **'🎫 Create Support Ticket'** below to escalate to tier-2 campus IT technicians. "
            f"Please attach any diagnostic logs and mention Priority: **{priority}**."
        )

        # Assemble final 5-section response
        formatted_steps = "\n".join([f"{i+1}. {step}" for i, step in enumerate(steps)])
        response = f"""### 🔍 Diagnosis
{diagnosis}

### 🛠️ Troubleshooting Steps
{formatted_steps}

### ✅ Diagnostic Result
{diag_text}

### 📚 Knowledge Source
{source_text}

### 🎫 Escalation
{escalation}"""
        return response

    # =================================================================
    # Main Agent Process Method
    # =================================================================

    def process_query(
        self,
        query: str,
        conversation_history: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """
        Full agent execution pipeline:
        1. Classifies category & priority.
        2. Detects and executes safe diagnostic tools.
        3. Performs RAG similarity search on FAISS vectorstore.
        4. Synthesizes structured response using Gemini LLM (or robust fallback).
        """
        conversation_history = conversation_history or []

        # 1. Classification
        category, priority = self.classify_issue(query)

        # 2. Tool execution
        tool_name, tool_result = self.detect_and_execute_tools(query)

        # 3. RAG Retrieval
        retrieved_chunks = similarity_search(query, top_k=3)
        sources = list(dict.fromkeys([c.get("source", "") for c in retrieved_chunks if c.get("source")]))

        # 4. Response Synthesis
        response_text = ""
        is_offline = True

        if self.client:
            try:
                prompt = build_synthesis_prompt(
                    user_query=query,
                    conversation_history=conversation_history,
                    retrieved_chunks=retrieved_chunks,
                    tool_name=tool_name,
                    tool_result=tool_result,
                    category=category,
                    priority=priority
                )

                if self.using_new_sdk:
                    resp = self.client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config={"system_instruction": SYSTEM_PROMPT}
                    )
                    response_text = resp.text
                    is_offline = False
                else:
                    model = self.client.GenerativeModel(
                        model_name=self.model_name,
                        system_instruction=SYSTEM_PROMPT
                    )
                    resp = model.generate_content(prompt)
                    response_text = resp.text
                    is_offline = False
            except Exception as e:
                print(f"[Agent] Gemini generation error (falling back to local engine): {e}")

        if not response_text:
            response_text = self._generate_fallback_response(
                query=query,
                category=category,
                priority=priority,
                tool_name=tool_name,
                tool_result=tool_result,
                retrieved_chunks=retrieved_chunks
            )

        return {
            "response": response_text,
            "category": category,
            "priority": priority,
            "tool_called": tool_name,
            "tool_result": tool_result,
            "sources": sources,
            "is_offline_mode": is_offline
        }
