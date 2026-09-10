"""
Generates sample_it_guide.pdf in knowledge_base/
Using ReportLab to create a structured college IT helpdesk guide.
"""

from pathlib import Path
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

BASE_DIR = Path(__file__).resolve().parent
PDF_PATH = BASE_DIR / "knowledge_base" / "sample_it_guide.pdf"

def generate_pdf():
    doc = SimpleDocTemplate(
        str(PDF_PATH),
        pagesize=letter,
        rightMargin=54,
        leftMargin=54,
        topMargin=54,
        bottomMargin=54
    )
    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=22,
        leading=26,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=10
    )

    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        leading=16,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=20
    )

    h1_style = ParagraphStyle(
        'H1',
        parent=styles['Heading2'],
        fontSize=15,
        leading=19,
        textColor=colors.HexColor('#1D4ED8'),
        spaceBefore=14,
        spaceAfter=6
    )

    body_style = ParagraphStyle(
        'Body',
        parent=styles['BodyText'],
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=8
    )

    story = []

    # Title & Subtitle
    story.append(Paragraph("UNIVERSITY IT HELPDESK STANDARD OPERATING PROCEDURES", title_style))
    story.append(Paragraph("Official Campus Technology Reference Manual & Troubleshooting Protocols", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=15))

    # Section 1: Campus Network & Connectivity
    story.append(Paragraph("1. Campus Network & Wi-Fi Operations", h1_style))
    story.append(Paragraph(
        "The university operates two primary wireless SSIDs across all academic, residential, and administrative buildings: "
        "<b>Campus-WiFi</b> (for registered student/faculty devices) and <b>eduroam</b> (for secure international inter-institutional access). "
        "If a device shows connected status but cannot browse websites, first check whether authentication was recently rejected due to an expired password. "
        "Students experiencing IP address assignment failures (169.254.x.x APIPA addresses) should release and renew their DHCP leases via 'ipconfig /renew' or reboot their wireless adapter. "
        "The campus DNS servers are configured to filter known malware domains. If DNS resolution fails with NXDOMAIN errors, verify primary DNS points to 1.1.1.1 or 8.8.8.8.",
        body_style
    ))

    # Section 2: Laboratory & Departmental Printing
    story.append(Paragraph("2. Network Printers and Spooler Diagnostics", h1_style))
    story.append(Paragraph(
        "All departmental and library printing stations utilize centralized Windows Print Queues. "
        "When a network printer displays an <b>Offline</b> state, verify whether the Windows Print Spooler service has stalled. "
        "To remediate, restart the 'Print Spooler' service in services.msc and clear temporary spool files located at C:\\Windows\\System32\\spool\\PRINTERS. "
        "If the printer outputs random symbols, raw ASCII characters, or blank pages, this indicates a corrupted PostScript driver. "
        "Remove the generic printer device and reinstall the HP/Canon Universal PCL6 driver from the campus software repository. "
        "Note: Remote printing from dormitory Wi-Fi requires an active Campus VPN tunnel.",
        body_style
    ))

    # Section 3: Operating System & Hardware Maintenance
    story.append(Paragraph("3. Windows OS & Workstation Health", h1_style))
    story.append(Paragraph(
        "Laboratory computers that crash on startup or experience application freezes (such as MATLAB, CAD, or Python IDEs) "
        "frequently suffer from low primary partition storage or missing runtime libraries. "
        "The campus IT standard requires at least 15GB of free space on Drive C: to allow page file allocation and Windows Update staging. "
        "For application crashes displaying error code 0xC0000005, deploy the Microsoft Visual C++ 2015-2022 Redistributable bundle. "
        "If persistent Blue Screen (BSOD) crashes occur, run System File Checker ('sfc /scannow') and inspect memory integrity via Windows Memory Diagnostic.",
        body_style
    ))

    # Section 4: Accounts, Identity & Security Policy
    story.append(Paragraph("4. User Accounts, Password Resets & MFA Policies", h1_style))
    story.append(Paragraph(
        "University accounts lock automatically for 30 minutes following 5 consecutive failed login attempts to safeguard against brute-force attacks. "
        "Students may initiate an automated self-service password reset at <i>https://account.college.edu/reset</i> using their registered phone number or alternate email. "
        "Passwords must meet institutional complexity requirements: minimum 12 characters, including uppercase, lowercase, numbers, and symbols. "
        "For Two-Factor Authentication (Duo / MFA) device replacement or lost phones, contact the IT Service Desk in the Student Union with official photo identification.",
        body_style
    ))

    # Section 5: IT Support Escalation Matrix
    story.append(Paragraph("5. Support Ticket Escalation Matrix", h1_style))
    story.append(Paragraph(
        "When front-line AI troubleshooting or self-service steps do not resolve an issue, users should open a formal Support Ticket. "
        "<b>Priority Guidelines:</b><br/>"
        "• <b>Low:</b> General software questions, non-urgent feature requests.<br/>"
        "• <b>Medium:</b> Single user printer offline, local application freeze with workarounds.<br/>"
        "• <b>High:</b> Classroom podium AV failure, lab network outage affecting multiple students.<br/>"
        "• <b>Critical:</b> Campus-wide network outage, security breach, server hardware failure.",
        body_style
    ))

    doc.build(story)
    print(f"[PDF] Successfully generated {PDF_PATH}")

if __name__ == "__main__":
    generate_pdf()
