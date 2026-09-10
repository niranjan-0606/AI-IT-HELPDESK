"""
AI IT Helpdesk Agent - System Verification Script
Executes automated tests on database, tools, RAG, memory, and agent orchestration.
"""

import sys
import io
from pathlib import Path

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

def test_database():
    print("\n--- [1/5] Testing Database Layer ---")
    from database import (
        init_db,
        save_message,
        get_conversation_history,
        create_ticket,
        get_all_tickets,
        get_dashboard_metrics
    )
    init_db()
    
    # Test conversation insert & retrieval
    test_session = "test_verify_session"
    save_message(test_session, "user", "Test problem message", category="Network", priority="Medium")
    save_message(test_session, "assistant", "Test answer", category="Network", priority="Medium")
    history = get_conversation_history(test_session)
    assert len(history) >= 2, f"Expected at least 2 messages, got {len(history)}"
    print("✅ Conversation memory persistence verified.")

    # Test ticket creation
    tid = create_ticket(
        user_name="Test Student",
        email="student@college.edu",
        title="Automated Test Issue",
        description="Testing ticket creation pipeline",
        category="Software",
        priority="Low"
    )
    assert tid.startswith("TICK-"), f"Unexpected ticket id format: {tid}"
    print(f"✅ Ticket creation verified (Generated ID: {tid}).")

    # Test dashboard metrics
    metrics = get_dashboard_metrics()
    assert "total_conversations" in metrics
    assert "open_tickets" in metrics
    print("✅ Dashboard KPI metrics retrieval verified.")


def test_diagnostic_tools():
    print("\n--- [2/5] Testing Diagnostic Tools ---")
    from tools import (
        check_internet,
        get_ip_address,
        ping_server,
        check_disk_space,
        system_information,
        network_information,
        is_safe_host
    )

    # 1. Internet Check
    net_res = check_internet()
    print(f"✅ Internet check: status={net_res.get('status')}, connected={net_res.get('connected')}")

    # 2. IP Address
    ip_res = get_ip_address()
    assert "local_ip" in ip_res
    print(f"✅ IP Address: local={ip_res.get('local_ip')}, hostname={ip_res.get('hostname')}")

    # 3. Disk Space
    disk_res = check_disk_space()
    assert "total_gb" in disk_res
    print(f"✅ Disk Space: total={disk_res.get('total_gb')}GB, free={disk_res.get('free_gb')}GB ({disk_res.get('percent_used')}%)")

    # 4. System Specs
    sys_res = system_information()
    assert "os" in sys_res
    print(f"✅ System Specs: OS={sys_res.get('os')} {sys_res.get('os_release')}, arch={sys_res.get('architecture')}")

    # 5. Network info
    nw_res = network_information()
    assert "local_ip" in nw_res
    print(f"✅ Network Info: {nw_res.get('message')}")

    # 6. Ping tool & Injection Security
    safe_ping = ping_server("8.8.8.8")
    print(f"✅ Ping 8.8.8.8: success={safe_ping.get('success')}, packet_loss={safe_ping.get('packet_loss_pct')}%")

    # Command injection test
    assert not is_safe_host("8.8.8.8; cat /etc/passwd")
    assert not is_safe_host("google.com & dir")
    malicious_ping = ping_server("8.8.8.8; rm -rf /")
    assert "Invalid host" in malicious_ping.get("error", "")
    print("✅ Host input validation and command injection prevention verified.")


def test_rag_system():
    print("\n--- [3/5] Testing RAG & FAISS Vectorstore ---")
    from rag import rebuild_knowledge_base, similarity_search, get_knowledge_base_stats

    # Rebuild vector database
    rebuild_res = rebuild_knowledge_base()
    print(f"✅ Knowledge Base rebuilt: {rebuild_res['documents_count']} docs, {rebuild_res['chunks_count']} chunks.")

    # Similarity search on printer offline
    chunks = similarity_search("How do I fix a printer that is offline?", top_k=2)
    assert len(chunks) > 0, "Expected at least 1 retrieved chunk"
    print(f"✅ RAG Search for 'printer offline' matched: source={chunks[0].get('source')}, score={chunks[0].get('score')}")

    # Check stats
    stats = get_knowledge_base_stats()
    assert stats["is_indexed"] is True
    print(f"✅ Knowledge Base stats verified: {stats['total_chunks']} chunks indexed.")


def test_agent():
    print("\n--- [4/5] Testing AI Agent Orchestration ---")
    from agent import AITTHelpdeskAgent

    agent = AITTHelpdeskAgent()

    # Test 1: Tool-calling query
    res_tool = agent.process_query("Check my internet connection")
    assert res_tool["tool_called"] == "check_internet"
    assert "### 🔍 Diagnosis" in res_tool["response"]
    assert "### 🛠️ Troubleshooting Steps" in res_tool["response"]
    assert "### ✅ Diagnostic Result" in res_tool["response"]
    assert "### 📚 Knowledge Source" in res_tool["response"]
    assert "### 🎫 Escalation" in res_tool["response"]
    print("✅ Agent correctly called 'check_internet' and formatted 5-section response.")

    # Test 2: RAG-calling query
    res_rag = agent.process_query("How do I fix a printer that is offline?")
    assert res_rag["category"] == "Printer"
    assert len(res_rag["sources"]) > 0
    print(f"✅ Agent correctly classified 'Printer' and cited knowledge sources: {res_rag['sources']}")

    # Test 3: System spec tool query
    res_sys = agent.process_query("What are my system specs and OS version?")
    assert res_sys["tool_called"] == "system_information"
    print("✅ Agent correctly called 'system_information'.")


def main():
    print("==================================================")
    print("AI IT Helpdesk Agent - Automated Verification Test")
    print("==================================================")
    try:
        test_database()
        test_diagnostic_tools()
        test_rag_system()
        test_agent()
        print("\n🎉 ALL TESTS PASSED SUCCESSFULLY! The system is fully operational.\n")
    except Exception as e:
        print(f"\n❌ TEST FAILED with error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
