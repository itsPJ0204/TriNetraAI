import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable, KeepTogether
)
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_page_decorations(num_pages)
            super().showPage()
        super().save()

    def draw_page_decorations(self, page_count):
        self.saveState()
        self.setFont("Helvetica-Bold", 8)
        self.setFillColor(colors.HexColor("#475569"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "TRINETRA AI — TACTICAL EARTH OBSERVATION INTELLIGENCE ENGINE")
            self.drawRightString(612 - 54, 750, "INDIAN DEFENSE & SIH 2026 EDITION")
            self.setStrokeColor(colors.HexColor("#D4AF37"))  # Gold border
            self.setLineWidth(0.8)
            self.line(54, 742, 612 - 54, 742)

        # Footer
        self.setStrokeColor(colors.HexColor("#334155"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.setFont("Helvetica", 8)
        self.drawString(54, 32, "TriNetraAI — Project Dossier & 3D Tactical Web Development Prompt")
        self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf(filename="TriNetraAI_Project_Flow_and_3D_Defense_Prompt.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=50,
        rightMargin=50,
        topMargin=58,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    # Custom Typography Styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=3
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#1E3A8A"),
        spaceAfter=8
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11.5,
        leading=15,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=8,
        spaceAfter=4
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=6,
        spaceAfter=3
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#334155"),
        spaceAfter=4
    )

    body_bold = ParagraphStyle(
        'Body_Bold',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor("#0F172A")
    )

    prompt_style = ParagraphStyle(
        'Prompt_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.2,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # ==========================================
    # TITLE BANNER & METADATA
    # ==========================================
    story.append(Paragraph("TRINETRA AI — PROJECT DOSSIER & 3D TACTICAL PROMPT", title_style))
    story.append(Paragraph("<b>Complete Project Flow & Military-Grade 3D Command Web Development Specification</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#D4AF37"), spaceAfter=6))

    # Meta Table
    meta_data = [
        [
            Paragraph("<b>Project:</b> TriNetraAI (Smart India Hackathon 2026)", body_style),
            Paragraph("<b>Domain:</b> Defense & Geospatial Intelligence (GEOINT)", body_style)
        ],
        [
            Paragraph("<b>Theme:</b> Indian Army / Tactical C4ISR Surveillance", body_style),
            Paragraph("<b>Core Capabilities:</b> Natural Lang Search + JIT QA + BIT Change AI", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[256, 256])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 3),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 3),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 6))

    # ==========================================
    # SECTION 1: EXECUTIVE OVERVIEW
    # ==========================================
    story.append(Paragraph("1. Executive Summary & Defense Problem Statement", h1_style))
    story.append(Paragraph(
        "<b>The Operational Challenge:</b> Conventional military GIS systems require analysts to know exact GPS coordinates before querying gigabyte-scale satellite archives. Furthermore, standard pixel-difference algorithms produce <b>80%+ false alarm rates</b> due to monsoon cloud cover, shifting sun azimuths, and seasonal foliage changes. Ground reconnaissance teams in remote or air-gapped border outposts lack continuous cloud connectivity.",
        body_style
    ))
    story.append(Paragraph(
        "<b>The TriNetraAI Solution:</b> An on-premises, zero-internet AI engine that enables defense commanders to search satellite scenes using free-form natural language (<i>\"airstrip near border valley\"</i>), dynamically suppresses cloud/shadow false positives via Just-In-Time (JIT) quality gating, and uses Deep Learning <b>BIT Transformers</b> to detect physical construction and classify tactical transitions (e.g. <i>Vegetation &rarr; Military Outpost / Runway</i>).",
        body_style
    ))
    story.append(Spacer(1, 4))

    # ==========================================
    # SECTION 2: COMPLETE 5-LAYER PROJECT FLOW
    # ==========================================
    story.append(Paragraph("2. Complete End-to-End Project Workflow & Architectural Pipeline", h1_style))
    
    flow_steps = [
        ("Layer 1: Data Ingestion & Spatial Provenance (Role 1 — Md Huzaifa Hayat)",
         "• Slices multi-sensor GeoTIFFs (Sentinel-2, Landsat-9, Drone) into 512&times;512 geographic patches without loading full gigabytes into RAM.<br/>"
         "• Generates SQLite spatial database (bounds, transform, timestamps, CRS EPSG:4326/UTM).<br/>"
         "• Exports authoritative provenance registry <code>data/tiles_metadata.csv</code> (Single Source of Truth)."),

        ("Layer 2: Semantic AI Vector Retrieval (Role 2 — Rahim)",
         "• Encodes satellite tiles into 512-D L2-normalized vectors via <b>RemoteCLIP (ViT-B/32)</b>.<br/>"
         "• Indexes embeddings in local <b>Qdrant Vector DB</b> with cosine similarity and 2D bounding box filters.<br/>"
         "• Employs military domain Query Expansion (e.g., <i>\"tarmac\" &rarr; [\"airfield\", \"runway\", \"landing strip\"]</i>).<br/>"
         "• Benchmark: Proven <b>0.9333 MRR</b> and <b>86.7% Top-1 Accuracy</b> across human-verified ground truth."),

        ("Layer 3: Just-In-Time (JIT) QA False-Alarm Suppression (Role 4 — Piyush)",
         "• <b>Execution Gate:</b> Triggered on-demand when comparing bitemporal pair (t1, t2).<br/>"
         "• Scene Classification Layer (SCL) Filter: Zeroes out Class 3 (Shadows), Classes 8–10 (Clouds), Class 11 (Snow).<br/>"
         "• Adaptive Halo Erosion: Scaled kernel removes cloud edge penumbra artifacts.<br/>"
         "• Offline Edge Node: Deploys <code>s2cloudless</code> LightGBM model on edge CPU hardware.<br/>"
         "• Output: Joint Valid Ground Mask: <code>M_valid = QA(t1) &cap; QA(t2)</code>."),

        ("Layer 4: Temporal Detective & Semantic Transition Classifier (Role 3 — Krishna)",
         "• <b>Early-Exit Occlusion Guard:</b> If valid ground visible &lt; 15%, skips heavy inference immediately.<br/>"
         "• <b>Dual-Engine Change Detection:</b> Primary Deep Learning <b>BIT Transformer</b> with high-speed Classical CV fallback.<br/>"
         "• <b>Cleansing:</b> <code>Clean_Change = Raw_BIT_Change &cap; QA(t1) &cap; QA(t2)</code>.<br/>"
         "• <b>Zero-Shot Semantic Transition Matrix:</b> Classifies <i>WHAT</i> changed (e.g. <i>Vegetation &rarr; New Construction</i>, <i>Open Land &rarr; Road</i>).<br/>"
         "• Produces sub-pixel contour bounding boxes $(x, y, w, h)$, surface %, and 40% red overlay."),

        ("Layer 5: Tactical Command Dashboard & Review Queue (Role 5 — Full-Stack)",
         "• Unified FastAPI REST backend (<code>/api/search</code>, <code>/api/changes</code>, <code>/api/similar</code>).<br/>"
         "• Interactive Leaflet.js before/after split-slider with polygon overlay toggles.<br/>"
         "• 1-Click Approve / Reject verification audit log satisfying military intelligence provenance.")
    ]

    for title, desc in flow_steps:
        story.append(Paragraph(f"• <b>{title}</b>", h2_style))
        story.append(Paragraph(desc, body_style))

    story.append(Spacer(1, 6))

    # ==========================================
    # SECTION 3: 3D WEB DEVELOPMENT PROMPT (INDIAN ARMY THEME)
    # ==========================================
    story.append(PageBreak())
    story.append(Paragraph("3. Production-Ready Master Prompt for 3D Web Development", h1_style))
    story.append(Paragraph("<b>Theme:</b> Indian Army / Tactical Defense Command Operations Center (C4ISR HUD)", subtitle_style))
    story.append(Paragraph(
        "Copy and paste the complete, highly detailed prompt below into your 3D development workflow (e.g., Antigravity, Claude, ChatGPT, or Cursor) to build the 3D web application with Three.js / React Three Fiber.",
        body_style
    ))
    story.append(Spacer(1, 4))

    # The Prompt Box
    prompt_text = """
====================================================================================================
MASTER PROMPT: 3D TACTICAL DEFENSE COMMAND WEB APPLICATION (THEME: INDIAN ARMY C4ISR)
====================================================================================================

You are an elite Senior 3D Creative Developer and Frontend Architect specializing in Three.js, React Three Fiber (R3F), WebGL GLSL Shaders, Tailwind CSS, and military tactical HUD interfaces.

Your mission is to build a state-of-the-art, hyper-immersive, production-grade 3D Web Application for "TRINETRA AI" — an Earth Observation Satellite Intelligence & Change Detective System tailored for the INDIAN ARMY and Strategic Border Command.

----------------------------------------------------------------------------------------------------
1. CORE VISUAL THEME & AESTHETIC GUIDELINES (INDIAN ARMY C4ISR)
----------------------------------------------------------------------------------------------------
- Primary Palette:
  * Tactical Olive Drab & Camo Green: #1B4332, #2D6A4F, #081C15
  * Indian Army Gold / Brass Accents: #D4AF37, #F59E0B
  * Target Reticle & Radar Cyan: #00E5FF, #38BDF8
  * Threat / Alert Crimson Red: #E63946, #EF4444
  * Deep Night Ops Background: #050811, #0B1120
- Design Mood: Military-grade C4ISR tactical war room, holographic globe, HUD reticles, Topographical contour wireframes, real-time satellite orbital tracks, scanlines, and telemetry audio feedback.
- Typography: 'Space Grotesk', 'Orbitron', or 'JetBrains Mono' for monospaced coordinates, timestamps (IST UTC+05:30), and elevation metrics.

----------------------------------------------------------------------------------------------------
2. KEY 3D SCENE COMPONENTS (THREE.JS / REACT THREE FIBER)
----------------------------------------------------------------------------------------------------
A. Holographic 3D Earth & Tactical Globe:
   - 3D interactive globe with realistic topography, night-lights shader, atmospheric glow, and coordinate latitude/longitude grid rings.
   - Highlight the Northern and North-Eastern Indian Border Sectors with golden glowing border polylines and strategic tactical pins (Ladakh, Arunachal, Siliguri Corridor, Coastal Hubs).
   - Animated satellite orbital path (Sentinel-2 / Cartosat) with real-time ground footprint scan cones.

B. Bitemporal Spyglass & 3D Split-Tile Scanner:
   - Interactive 3D floating tile canvas comparing Time 1 (Before - 2024) vs Time 2 (After - 2026).
   - Interactive 3D wiper plane / spyglass lens revealing detected changes underneath.
   - Dynamic 3D bounding boxes rising from the surface on detected changes with glowing red pulsed wireframes.
   - Holographic floating callout badges displaying transition labels:
     [ TARGET DETECTED: Vegetation -> New Military Runway | Confidence: 89.2% | Area: 6,912 m² ]

C. Just-In-Time QA Cloud/Shadow Suppression Shader:
   - Visual toggle showing raw cloud occlusion vs suppressed cloud mask (SCL 2-px halo erosion).
   - Dynamic particle sweep wiping away cloud layers to reveal the underlying ground terrain.

D. Tactical HUD & Reticle System (Canvas 2D / SVG Overlay):
   - Interactive crosshair target reticle with coordinate tracking (Lat, Lon, Alt, Heading).
   - Animated Radar Sweep widget in top-right corner with blips for detected surface anomalies.
   - Live Telemetry status bar: [ SYSTEM: AIR-GAPPED | QDRANT: EMBEDDED | BIT ENGINE: ACTIVE ].

----------------------------------------------------------------------------------------------------
3. CORE INTERACTIVE SCREENS & UI MODES
----------------------------------------------------------------------------------------------------
Screen 1: "TACTICAL GLOBAL SURVEILLANCE"
  - Rotating 3D Globe with heatmaps of high-change border sectors.
  - Natural Language Search Bar: Type "border airfield", "encroachment near valley", or "bunkers".
  - Floating 3D query vector alignment visualization connecting text query to top matched tiles.

Screen 2: "BITEMPORAL DETECTIVE INSPECTOR"
  - 3D side-by-side tile inspection with depth map extrusion.
  - Interactive split slider reveals BIT Transformer change mask in glowing 40% red overlay.
  - Semantic Transition Matrix panel: [ Vegetation -> Concrete | Confidence: 91.4% ].

Screen 3: "AIR-GAPPED EDGE NODE MONITOR"
  - 3D representation of field rugged laptop / Raspberry Pi node processing offline s2cloudless trees.
  - Zero-Cloud telemetry graphs: CPU load, RAM usage, and offline inference time (<1.2s).

Screen 4: "COMMAND REVIEW & AUDIT LOG"
  - 1-Click "APPROVE TARGET" or "DISMISS FALSE ALARM" decision buttons with military stamp animations.
  - Export cryptographic audit report with SHA-256 provenance hash for intelligence archives.

----------------------------------------------------------------------------------------------------
4. TECHNICAL STACK & IMPLEMENTATION REQUIREMENTS
----------------------------------------------------------------------------------------------------
- Framework: React (Next.js or Vite) + React Three Fiber + @react-three/drei + Tailwind CSS.
- Shaders: Custom GLSL vertex/fragment shaders for atmospheric glow, radar sweep, and change mask blending.
- Animations: Framer Motion for tactical HUD panels; GSAP or Three.js clock for smooth camera fly-throughs.
- Audio (Optional): Subtle tactical audio clicks, radar pings, and scan hums on user interactions.
- Performance: 60 FPS guaranteed on laptops using pre-instanced meshes, low-poly wireframes, and frustum culling.

Build this complete, stunning 3D application with zero placeholders, full interactivity, and an awe-inspiring military aesthetic.
====================================================================================================
"""
    story.append(Paragraph("<font face='Courier' size='7'>" + prompt_text.replace("\n", "<br/>").replace(" ", "&nbsp;") + "</font>", prompt_style))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated master project dossier and 3D prompt PDF: {filename}")

if __name__ == "__main__":
    out_pdf = "TriNetraAI_Project_Flow_and_3D_Defense_Prompt.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
