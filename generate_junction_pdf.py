import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
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
        self.setFont("Helvetica", 8)
        self.setFillColor(colors.HexColor("#64748B"))
        
        # Header (pages > 1)
        if self._pageNumber > 1:
            self.drawString(54, 750, "TriNetraAI — Technical Report: Person 1 & Person 2 Junction Analysis")
            self.drawRightString(612 - 54, 750, "Confidential / SIH 2026")
            self.setStrokeColor(colors.HexColor("#CBD5E1"))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)

        # Footer
        self.setStrokeColor(colors.HexColor("#CBD5E1"))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, "TriNetraAI Geospatial Intelligence Engine — Smart India Hackathon 2026")
        self.drawRightString(612 - 54, 32, f"Page {self._pageNumber} of {page_count}")
        self.restoreState()

def build_pdf(filename="Junction_Analysis_Person1_Person2.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=6
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor("#475569"),
        spaceAfter=14
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=12,
        spaceAfter=6
    )

    h2_style = ParagraphStyle(
        'Heading2_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor("#0F172A"),
        spaceBefore=8,
        spaceAfter=4
    )

    body_style = ParagraphStyle(
        'Body_Custom',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13.5,
        textColor=colors.HexColor("#334155"),
        spaceAfter=6
    )

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor("#0F172A")
    )

    badge_style = ParagraphStyle(
        'Badge',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor("#FFFFFF"),
        alignment=1
    )

    story = []

    # Title Banner
    story.append(Paragraph("TriNetraAI — System Integration Technical Report", title_style))
    story.append(Paragraph("<strong>Subsystem Junction Audit:</strong> Person 1 (Data Ingestion) &harr; Person 2 (Semantic Search)", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=12))

    # Meta table
    meta_data = [
        [
            Paragraph("<b>Target Subsystems:</b> Ingestion & Vector Search", body_style),
            Paragraph("<b>Date:</b> September 2026", body_style),
        ],
        [
            Paragraph("<b>Role 1 Lead:</b> Md Huzaifa Hayat (Data Engineering)", body_style),
            Paragraph("<b>Role 2 Lead:</b> Rahim (Semantic AI)", body_style),
        ],
        [
            Paragraph("<b>Audit Status:</b> 4 Loopholes Identified & Resolved", body_style),
            Paragraph("<b>Classification:</b> Internal Engineering Review", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 10))

    # Section 1: Overview
    story.append(Paragraph("1. Executive Summary & Junction Architecture", h1_style))
    story.append(Paragraph(
        "In the TriNetraAI pipeline, <b>Person 1 (Data Engineering)</b> acts as the system's librarian—slicing raw multi-gigabyte satellite scenes into 512&times;512 co-registered patches and cataloging their spatial provenance. <b>Person 2 (Semantic AI)</b> acts as the translator—ingesting those patches, generating 512-dimensional multimodal embeddings using RemoteCLIP (ViT-B/32), and indexing them in Qdrant Vector DB for natural language search. The stability of the entire pipeline depends on a flawless contract between these two layers.",
        body_style
    ))
    story.append(Paragraph(
        "A rigorous line-by-line audit of <code>ingestion/</code> and <code>semantic_search/</code> revealed <b>four critical vulnerabilities/loopholes</b> where runtime failures, data silent-dropping, and embedding degradation occur. Below is the full technical breakdown.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Section 2: Detailed Vulnerabilities
    story.append(Paragraph("2. Deep-Dive: Identified Loopholes & Failure Modes", h1_style))

    # Loophole 1
    story.append(Paragraph("🔴 Loophole 1: Filesystem Blindness (Subdirectory Traversal Mismatch)", h2_style))
    story.append(Paragraph(
        "<b>Root Cause:</b> In <code>ingestion/tiling.py</code> (lines 30&ndash;49), Person 1 organizes tiles into structured subdirectories partitioned by scene name: <code>data/tiles/&lt;scene_name&gt;/&lt;tile_id&gt;.tif</code>. However, in <code>semantic_search/embeddings.py</code> (lines 27&ndash;43), Person 2 uses a shallow iterator <code>TILES_DIRECTORY.iterdir()</code> which only inspects the immediate root folder.",
        body_style
    ))
    l1_data = [
        [Paragraph("<b>Person 1 Producer Code (ingestion/tiling.py)</b>", body_style), Paragraph("<b>Person 2 Consumer Code (semantic_search/embeddings.py)</b>", body_style)],
        [
            Paragraph("<font face='Courier' size='7.5'>image_dir = root / path.stem<br/>tile_path = image_dir / f\"{tile_id}.tif\"<br/># Writes into data/tiles/delhi_2024/tile_001.tif</font>", code_style),
            Paragraph("<font face='Courier' size='7.5'>def find_satellite_tiles():<br/>&nbsp;&nbsp;return sorted(p for p in TILES_DIR.iterdir()<br/>&nbsp;&nbsp;&nbsp;&nbsp;if p.is_file() and p.suffix == '.tif')<br/># FAILS: iterdir() does NOT recurse subfolders!</font>", code_style)
        ]
    ]
    l1_table = Table(l1_data, colWidths=[250, 254])
    l1_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.HexColor("#EFF6FF")),
        ('BACKGROUND', (1, 0), (1, -1), colors.HexColor("#FEF2F2")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(l1_table)
    story.append(Paragraph(
        "<b>Impact:</b> Person 2's tile discovery returns an empty list <code>[]</code>, raising an unhandled <code>FileNotFoundError: No satellite tiles were found</code> and halting vector generation.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Loophole 2
    story.append(Paragraph("🔴 Loophole 2: Radiometric & Multi-Band Incompatibility (PIL vs Rasterio)", h2_style))
    story.append(Paragraph(
        "<b>Root Cause:</b> Person 1 outputs native remote sensing GeoTIFFs containing 16-bit reflectances (<code>uint16</code> values up to 10,000) across 4 to 13 bands (e.g. RGB + NIR + SCL). In <code>semantic_search/embeddings.py</code> (line 59), Person 2 attempts to read these files using standard PIL <code>Image.open(path).convert('RGB')</code>.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Impact:</b><br/>"
        "1. <i>Multi-Band Crash:</i> PIL cannot parse $>4$ band GeoTIFFs (like 13-band Sentinel-2), triggering <code>OSError: cannot identify image file</code>.<br/>"
        "2. <i>Dynamic Range Collapse:</i> PIL improperly converts 16-bit reflectances, outputting completely black or clipped images. Passing pitch-black arrays into RemoteCLIP corrupts the 512-D vector space, destroying search MRR accuracy.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Loophole 3
    story.append(Paragraph("🔴 Loophole 3: Ingestion Contract Bypass (CSV & DB Ignored)", h2_style))
    story.append(Paragraph(
        "<b>Root Cause:</b> Person 1 engineered an official export contract (<code>export_metadata_csv()</code> producing <code>data/tiles_metadata.csv</code> and maintaining SQLite <code>tiles</code> table with exact coordinates, CRS, resolution, and timestamps). Person 2 bypasses this registry entirely, attempting manual filesystem discovery and re-extracting bounding boxes via secondary rasterio reads.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Impact:</b> Bypassing the central database breaks provenance tracking, duplicates I/O, and causes desynchronization if tiles are renamed or re-tiled.",
        body_style
    ))
    story.append(Spacer(1, 6))

    # Loophole 4
    story.append(Paragraph("🔴 Loophole 4: Hardcoded Remote Qdrant Host vs Air-Gapped Operation", h2_style))
    story.append(Paragraph(
        "<b>Root Cause:</b> <code>semantic_search/vector_store.py</code> hardcodes <code>QDRANT_URL = 'http://localhost:6333'</code> without a fallback.",
        body_style
    ))
    story.append(Paragraph(
        "<b>Impact:</b> In field/air-gapped deployments where external Docker containers are unavailable, vector search crashes immediately on <code>ConnectionRefusedError</code> rather than leveraging Qdrant's embedded in-memory/disk mode (<code>QdrantClient(path='...')</code>).",
        body_style
    ))
    story.append(Spacer(1, 8))

    # Section 3: Remediation Matrix
    story.append(Paragraph("3. Architectural Resolution & Remediation Matrix", h1_style))
    
    remedy_data = [
        [
            Paragraph("<b>Identified Loophole</b>", body_style),
            Paragraph("<b>Severity</b>", body_style),
            Paragraph("<b>Engineering Fix Implemented</b>", body_style),
            Paragraph("<b>Status</b>", body_style)
        ],
        [
            Paragraph("1. Subdirectory Traversal", body_style),
            Paragraph("<font color='#DC2626'><b>HIGH</b></font>", body_style),
            Paragraph("Switch <code>iterdir()</code> to recursive <code>rglob('*.tif*')</code> and ingest directly from <code>data/tiles_metadata.csv</code>.", body_style),
            Paragraph("<font color='#16A34A'><b>RESOLVED</b></font>", body_style)
        ],
        [
            Paragraph("2. 16-Bit / Multi-Band PIL", body_style),
            Paragraph("<font color='#DC2626'><b>CRITICAL</b></font>", body_style),
            Paragraph("Adopt <code>rasterio</code> reader with 2%–98% percentile contrast normalization (shared from Role 3 preprocessor).", body_style),
            Paragraph("<font color='#16A34A'><b>RESOLVED</b></font>", body_style)
        ],
        [
            Paragraph("3. Ingestion Contract Bypass", body_style),
            Paragraph("<font color='#D97706'><b>MEDIUM</b></font>", body_style),
            Paragraph("Bind Person 2's embedding pipeline to consume <code>tiles_metadata.csv</code> as single source of truth.", body_style),
            Paragraph("<font color='#16A34A'><b>RESOLVED</b></font>", body_style)
        ],
        [
            Paragraph("4. Qdrant HTTP Dependency", body_style),
            Paragraph("<font color='#D97706'><b>MEDIUM</b></font>", body_style),
            Paragraph("Implement auto-fallback to embedded local storage <code>QdrantClient(path='data/qdrant_local')</code>.", body_style),
            Paragraph("<font color='#16A34A'><b>RESOLVED</b></font>", body_style)
        ],
    ]
    remedy_table = Table(remedy_data, colWidths=[120, 60, 244, 80])
    remedy_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 5),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    for row in range(len(remedy_data)):
        if row > 0 and row % 2 == 1:
            remedy_table.setStyle(TableStyle([('BACKGROUND', (0, row), (-1, row), colors.HexColor("#F8FAFC"))]))
    story.append(remedy_table)
    story.append(Spacer(1, 14))

    # Section 4: Architecture Conclusion
    story.append(Paragraph("4. Final Integration Verdict", h1_style))
    story.append(Paragraph(
        "By aligning the tile discovery logic, sharing the 16-bit percentile preprocessor, and enforcing the CSV metadata registry as the unified contract, the junction between Person 1 and Person 2 is now <b>100% airtight, resilient to nested directory layouts, and completely air-gapped ready</b>.",
        body_style
    ))

    # Build the document
    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated technical PDF report: {filename}")

if __name__ == "__main__":
    out_pdf = "Junction_Analysis_Person1_Person2.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
