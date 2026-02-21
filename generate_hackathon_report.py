"""
AIVA - Hackathon Project Report Generator
=========================================
Generates a formal, high-impact PDF project report for the AIVA project.
"""

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch, mm
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_JUSTIFY
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    PageBreak, HRFlowable, Image
)
from reportlab.graphics.shapes import Drawing, Rect as GRect, String
from datetime import datetime
import os

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "AIVA_Hackathon_Report.pdf")

# --- Color Palette ---
BRAND_BLUE = colors.HexColor("#0A2647")
BRAND_ACCENT = colors.HexColor("#2C74B3")
BRAND_LIGHT = colors.HexColor("#E8F0FE")
BRAND_GREEN = colors.HexColor("#2ECC71")
BRAND_YELLOW = colors.HexColor("#F1C40F")
BRAND_RED = colors.HexColor("#E74C3C")
BRAND_GRAY = colors.HexColor("#7F8C8D")
WHITE = colors.white
BLACK = colors.black
DARK_TEXT = colors.HexColor("#1A1A2E")
LIGHT_GRAY = colors.HexColor("#ECF0F1")
MEDIUM_GRAY = colors.HexColor("#BDC3C7")

# --- Styles ---
styles = getSampleStyleSheet()

styles.add(ParagraphStyle(
    name='ReportTitle', fontName='Helvetica-Bold', fontSize=26,
    textColor=WHITE, alignment=TA_CENTER, spaceAfter=10, leading=30
))
styles.add(ParagraphStyle(
    name='ReportSubtitle', fontName='Helvetica', fontSize=14,
    textColor=BRAND_LIGHT, alignment=TA_CENTER, spaceAfter=4,
))
styles.add(ParagraphStyle(
    name='SectionHeader', fontName='Helvetica-Bold', fontSize=16,
    textColor=BRAND_BLUE, spaceBefore=20, spaceAfter=10,
    borderPadding=(0, 0, 4, 0),
))
styles.add(ParagraphStyle(
    name='SubHeader', fontName='Helvetica-Bold', fontSize=12,
    textColor=BRAND_ACCENT, spaceBefore=12, spaceAfter=6,
))
styles.add(ParagraphStyle(
    name='ReportBody', fontName='Helvetica', fontSize=11,
    textColor=DARK_TEXT, leading=16, spaceAfter=8, alignment=TA_JUSTIFY,
))
styles.add(ParagraphStyle(
    name='BulletText', fontName='Helvetica', fontSize=11,
    textColor=DARK_TEXT, leading=16, spaceAfter=6, leftIndent=20,
    bulletIndent=8,
))
styles.add(ParagraphStyle(
    name='Emphasis', fontName='Helvetica-BoldOblique', fontSize=11,
    textColor=BRAND_BLUE, leading=16, spaceAfter=8, alignment=TA_JUSTIFY,
))
styles.add(ParagraphStyle(
    name='TableHeader', fontName='Helvetica-Bold', fontSize=10,
    textColor=WHITE, alignment=TA_CENTER,
))
styles.add(ParagraphStyle(
    name='TableCell', fontName='Helvetica', fontSize=10,
    textColor=DARK_TEXT, alignment=TA_LEFT, leading=14
))
styles.add(ParagraphStyle(
    name='FooterText', fontName='Helvetica', fontSize=8,
    textColor=BRAND_GRAY, alignment=TA_CENTER
))

def build_header_block():
    """Build the branded title header."""
    header_data = [[
        Paragraph("AIVA: AI Vision Assistant", styles['ReportTitle']),
    ], [
        Paragraph("Technical Project Report & System Architecture", styles['ReportSubtitle']),
    ], [
        Paragraph(f"Hackathon Submission  |  {datetime.now().strftime('%B %Y')}", styles['ReportSubtitle']),
    ]]
    header_table = Table(header_data, colWidths=[480])
    header_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), BRAND_BLUE),
        ('TOPPADDING', (0, 0), (0, 0), 24),
        ('BOTTOMPADDING', (0, -1), (0, -1), 24),
        ('LEFTPADDING', (0, 0), (-1, -1), 20),
        ('RIGHTPADDING', (0, 0), (-1, -1), 20),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('ROUNDEDCORNERS', [10, 10, 10, 10]),
    ]))
    return header_table

def build_report():
    """Build the complete AIVA hackathon report."""
    doc = SimpleDocTemplate(
        OUTPUT_PATH, pagesize=A4,
        topMargin=40, bottomMargin=40, leftMargin=50, rightMargin=50,
        title="AIVA Project Report",
        author="Junaid Pasha",
    )

    story = []

    # ========== HEADER ==========
    story.append(build_header_block())
    story.append(Spacer(1, 25))

    # ========== 1. EXECUTIVE SUMMARY ==========
    story.append(Paragraph("1. Executive Summary & Abstract", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph(
        "<b>AIVA (AI Vision Assistant)</b> is a groundbreaking assistive technology platform designed to restore "
        "spatial autonomy to visually impaired individuals. Addressing the critical gap between expensive, proprietary "
        "hardware and basic smartphone apps, AIVA leverages a <b>hybrid edge-cloud architecture</b> to deliver "
        "real-time environmental perception.",
        styles['ReportBody']
    ))
    story.append(Paragraph(
        "By fusing <b>Computer Vision (YOLOv8, MiDaS)</b> and <b>Generative AI (Google Gemini)</b>, "
        "AIVA converts visual data into actionable audio insights. The system provides instantaneous obstacle warnings, "
        "reads text via OCR, identifies people, and offers rich scene descriptions—all through a low-latency "
        "Android interface. This project demonstrates that high-fidelity assistive AI can be accessible, "
        "scalable, and privacy-preserving.",
        styles['Emphasis']
    ))
    story.append(Spacer(1, 10))

    # ========== 2. PROBLEM & OBJECTIVES ==========
    story.append(Paragraph("2. Problem Statement & Objectives", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph("<b>The Societal Challenge:</b>", styles['SubHeader']))
    story.append(Paragraph(
        "Over 2.2 billion people globally suffer from vision impairment. Current solutions force a compromise: "
        "specialized hardware is cost-prohibitive ($3,000+), while mobile apps often suffer from high latency, "
        "reliance on consistent internet, and poor privacy practices.",
        styles['ReportBody']
    ))

    story.append(Paragraph("<b>Primary Objectives:</b>", styles['SubHeader']))
    objectives = [
        "<b>Real-Time Spatial Awareness:</b> Detect hazards (vehicles, stairs, obstacles) with <500ms latency to ensure user safety.",
        "<b>Fault-Tolerant Architecture:</b> Ensure critical features (SOS, Location) function even without active server connection.",
        "<b>Accessible & Intuitive UX:</b> Design for 'Eyes-Free' operation using high-contrast UI, Haptic feedback, and TalkBack integration.",
        "<b>Privacy-First Design:</b> Process sensitive visual data on user-controlled hardware, minimizing third-party data exposure."
    ]
    for obj in objectives:
        story.append(Paragraph(f"• {obj}", styles['BulletText']))
    
    story.append(Spacer(1, 10))

    # ========== 3. SYSTEM ARCHITECTURE ==========
    story.append(Paragraph("3. System Architecture & Data Flow", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph(
        "The system employs a tightly coupled <b>Client-Server architecture</b> communicating via a bidirectional "
        "WebSocket protocol over a secure local or reverse-tunneled connection.",
        styles['ReportBody']
    ))

    # Architecture Table
    arch_data = [
        [Paragraph("<b>Component</b>", styles['TableHeader']),
         Paragraph("<b>Role & Responsibilities</b>", styles['TableHeader'])],
        [Paragraph("<b>Android Client</b><br/>(The Sensor)", styles['TableCell']),
         Paragraph(
             "• <b>CameraX</b>: Captures 640x480 YUV frames @ 30FPS.<br/>"
             "• <b>Packetizer</b>: Compresses frames + timestamp headers.<br/>"
             "• <b>Sensors</b>: FusedLocationProvider for GPS, Accelerometer.<br/>"
             "• <b>Interaction</b>: TTS (Text-to-Speech) output, SOS triggers.",
             styles['TableCell'])],
        [Paragraph("<b>Transmission Layer</b><br/>(The Bridge)", styles['TableCell']),
         Paragraph(
             "• <b>Protocol</b>: Custom binary protocol (Byte-aligned headers).<br/>"
             "• <b>Transport</b>: Async WebSocket (WSS) with JWT Authentication.<br/>"
             "• <b>Optimization</b>: Sliding window flow control to prevent lag.",
             styles['TableCell'])],
        [Paragraph("<b>Python Backend</b><br/>(The Brain)", styles['TableCell']),
         Paragraph(
             "• <b>Orchestrator</b>: Routes frames to specialized AI engines.<br/>"
             "• <b>Inference</b>: YOLOv8 (Objects), MiDaS (Depth), dlib (Face).<br/>"
             "• <b>NLP Router</b>: Distinguishes 'Help me' from 'Describe scene'.",
             styles['TableCell'])],
    ]
    t = Table(arch_data, colWidths=[120, 320])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t)
    story.append(Spacer(1, 10))

    # ========== 4. TECH STACK ==========
    story.append(PageBreak())
    story.append(Paragraph("4. Core Technology Stack & Implementation", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph("<b>Frontend (Android Native):</b>", styles['SubHeader']))
    story.append(Paragraph(
        "Built with <b>Kotlin</b> and <b>Jetpack Compose</b>. Leverages <b>Hilt</b> for dependency injection, "
        "<b>Coroutines</b> for concurrency, and <b>LifecycleService</b> for robust background execution.",
        styles['ReportBody']
    ))

    story.append(Paragraph("<b>Backend & AI (Python):</b>", styles['SubHeader']))
    stack_data = [
        [Paragraph("<b>Module</b>", styles['TableHeader']),
         Paragraph("<b>Technology / Model</b>", styles['TableHeader']),
         Paragraph("<b>Purpose</b>", styles['TableHeader'])],
        [Paragraph("Object Detection", styles['TableCell']),
         Paragraph("YOLOv8 Nano (Ultralytics)", styles['TableCell']),
         Paragraph("Real-time identification of 80+ classes (Person, Car, Chair).", styles['TableCell'])],
        [Paragraph("Depth Perception", styles['TableCell']),
         Paragraph("MiDaS Small (Intel)", styles['TableCell']),
         Paragraph("Monocular depth estimation to gauge distance to obstacles.", styles['TableCell'])],
        [Paragraph("Face Recognition", styles['TableCell']),
         Paragraph("dlib / OpenCV LBPH", styles['TableCell']),
         Paragraph("Identifying known individuals (Privacy-compliant).", styles['TableCell'])],
        [Paragraph("Scene Intelligence", styles['TableCell']),
         Paragraph("Google Gemini 2.0 Flash", styles['TableCell']),
         Paragraph("Generative description of complex scenarios and VQA.", styles['TableCell'])],
        [Paragraph("OCR", styles['TableCell']),
         Paragraph("EasyOCR (PyTorch)", styles['TableCell']),
         Paragraph("Reading signboards, documents, and labels.", styles['TableCell'])],
    ]
    t2 = Table(stack_data, colWidths=[100, 140, 200])
    t2.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), BRAND_BLUE),
        ('TEXTCOLOR', (0, 0), (-1, 0), WHITE),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [WHITE, BRAND_LIGHT]),
        ('GRID', (0, 0), (-1, -1), 0.5, MEDIUM_GRAY),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(t2)
    story.append(Spacer(1, 10))

    story.append(Paragraph("<b>Implementation Phases:</b>", styles['SubHeader']))
    phases = [
        "<b>Phase 1: Foundation.</b> Setup of WebSocket pipeline, core YOLO inference, and Android CameraX.",
        "<b>Phase 2: Visual Intelligence.</b> Integration of MiDaS Depth, Face Rec, and OCR engines.",
        "<b>Phase 3: Safety Nets.</b> Implementation of NLP Intent Routing, GPS Location, and Emergency SOS SMS.",
        "<b>Phase 4: Production.</b> Latency optimization, Dockerization, and Play Store compliance.",
    ]
    for p in phases:
        story.append(Paragraph(f"• {p}", styles['BulletText']))

    # ========== 5. OPTIMIZATION & CHALLENGES ==========
    story.append(Paragraph("5. Performance & Challenges Solved", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph(
        "<b>1. Bypassing Android Background Limits:</b><br/>"
        "Android 14 restricts background camera usage. We solved this by implementing a <b>Foreground Service</b> "
        "of type `location` and `camera`, bound to the `LifecycleService`. This ensures AIVA 'sees' even "
        "when the phone is in the user's pocket.",
        styles['ReportBody']
    ))
    story.append(Paragraph(
        "<b>2. Latency Engineering:</b><br/>"
        "To achieve <500ms response time, we optimized the network payload by compressing frames to JPEG Q75 "
        "and implementing a 'Drop-Oldest' backpressure strategy in the WebSocket buffer. This prevents lag accumulation.",
        styles['ReportBody']
    ))
    story.append(Paragraph(
        "<b>3. Cross-Platform Compatibility:</b><br/>"
        "The `dlib` library caused critical crashes on Windows. We engineered a fallback mechanism using "
        "<b>OpenCV's LBPH Face Recognizer</b>, ensuring the system remains functional across different server OS environments.",
        styles['ReportBody']
    ))
    story.append(Spacer(1, 10))

    # ========== 6. GO-TO-MARKET ==========
    story.append(PageBreak())
    story.append(Paragraph("6. Launch Strategy & Future Scope", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))

    story.append(Paragraph("<b>Beta Launch Strategy:</b>", styles['SubHeader']))
    story.append(Paragraph(
        "The application is prepared for a closed Alpha release via the <b>Google Play Console Internal Testing</b> track. "
        "We have implemented strict Data Safety protocols (Privacy Policy, encrypted storage) to meet Store compliance requirements. "
        "Initial rollout targets a focus group of 50 visually impaired users.",
        styles['ReportBody']
    ))

    story.append(Paragraph("<b>Future Roadmap:</b>", styles['SubHeader']))
    roadmap = [
        "<b>Edge AI Migration:</b> Porting YOLO and MiDaS to TensorFlow Lite for completely offline inference.",
        "<b>Wearable Integration:</b> Logic to support smart glasses (e.g., Ray-Ban Meta) as input devices.",
        "<b>Haptic Navigation:</b> Integrating vibration patterns to guide users left/right without audio overload."
    ]
    for item in roadmap:
        story.append(Paragraph(f"➜ {item}", styles['BulletText']))

    story.append(Spacer(1, 15))

    # ========== 7. CONCLUSION ==========
    story.append(Paragraph("7. Conclusion", styles['SectionHeader']))
    story.append(HRFlowable(width="100%", thickness=1.5, color=BRAND_ACCENT, spaceAfter=12))
    
    story.append(Paragraph(
        "AIVA represents a paradigm shift in accessible technology. By decoupling the 'Brain' (High-power compute) "
        "from the 'Sensor' (Smartphone), we have created a system that is powerful, affordable, and continuously improving. "
        "This project is not just a technical demonstration; it is a step towards a world where technology acts as a "
        "genuine equalizer, granting independence and dignity to millions.",
        styles['Emphasis']
    ))

    # ========== BUILD ==========
    doc.build(story)
    print(f"\n✅ Hackathon Report generated: {OUTPUT_PATH}")

if __name__ == "__main__":
    build_report()
