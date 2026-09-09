import os
import sys
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, HRFlowable
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
            self.drawString(54, 750, "TriNetraAI — System Integration Report: Subsystem Junction Audits & Fixes")
            self.drawRightString(612 - 54, 750, "SIH 2026 / Confidential")
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

def build_pdf(filename="TriNetraAI_Complete_Junction_Audit.pdf"):
    doc = SimpleDocTemplate(
        filename,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=60,
        bottomMargin=55
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor("#0F172A"),
        spaceAfter=4
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor("#475569"),
        spaceAfter=10
    )

    h1_style = ParagraphStyle(
        'Heading1_Custom',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=12,
        leading=16,
        textColor=colors.HexColor("#1E3A8A"),
        spaceBefore=10,
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

    code_style = ParagraphStyle(
        'Code_Custom',
        parent=styles['Normal'],
        fontName='Courier',
        fontSize=7.5,
        leading=10,
        textColor=colors.HexColor("#0F172A")
    )

    story = []

    # Title Banner
    story.append(Paragraph("TriNetraAI — Subsystem Junction Audit & Resolution Report", title_style))
    story.append(Paragraph("Comprehensive Architectural Analysis & Fixes: <b>Person 1 &harr; Person 2</b> and <b>Person 4 &harr; Person 3</b>", subtitle_style))
    story.append(HRFlowable(width="100%", thickness=1.5, color=colors.HexColor("#2563EB"), spaceAfter=8))

    # Meta table
    meta_data = [
        [
            Paragraph("<b>Subsystem Junction 1:</b> Person 1 (Ingest) &harr; Person 2 (Semantic)", body_style),
            Paragraph("<b>Subsystem Junction 2:</b> Person 4 (QA Filter) &harr; Person 3 (Detective)", body_style),
        ],
        [
            Paragraph("<b>Audit Status:</b> All 9 Loopholes Formally Fixed", body_style),
            Paragraph("<b>Target Branch:</b> <code>integrated-trinetra-ai</code>", body_style)
        ]
    ]
    meta_table = Table(meta_data, colWidths=[250, 254])
    meta_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor("#F8FAFC")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ]))
    story.append(meta_table)
    story.append(Spacer(1, 8))

    # SECTION 1: Person 1 & Person 2
    story.append(Paragraph("1. Junction Audit: Person 1 (Data Ingestion) &harr; Person 2 (Semantic AI)", h1_style))
    
    p1_p2_loopholes = [
        ("Loophole 1: Subdirectory Traversal Mismatch", "Person 1 outputs tiles in <code>data/tiles/&lt;scene&gt;/</code>. Person 2 used shallow <code>iterdir()</code>, yielding an empty list <code>[]</code> and <code>FileNotFoundError</code>.", "<b>Fix:</b> Upgraded to recursive <code>rglob('*')</code> with automatic fallback to <code>tiles_metadata.csv</code> registry."),
        ("Loophole 2: Multi-Band & 16-Bit Radiometric Incompatibility", "Person 1 writes 16-bit GeoTIFFs (4–13 bands). Person 2 used PIL <code>Image.open().convert('RGB')</code>, which crashes on >4 bands and corrupts 16-bit reflectances into pitch-black arrays.", "<b>Fix:</b> Integrated <code>rasterio</code> reader with 2%–98% percentile contrast normalization, matching RemoteCLIP expectations."),
        ("Loophole 3: Ingestion Contract Bypass", "Person 2 ignored Person 1's SQLite/CSV spatial provenance registry and re-scanned disk manually.", "<b>Fix:</b> Bound embedding generation directly to consume <code>data/tiles_metadata.csv</code> as single source of truth."),
        ("Loophole 4: Hardcoded Remote Qdrant Host", "Hardcoded <code>http://localhost:6333</code> crashed on air-gapped field laptops without Docker.", "<b>Fix:</b> Enabled embedded local storage fallback (<code>QdrantClient(path='data/qdrant_local')</code>).")
    ]

    for title, desc, fix in p1_p2_loopholes:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", body_style))
        story.append(Paragraph(f"&nbsp;&nbsp;↳ {fix}", body_style))

    story.append(Spacer(1, 6))

    # SECTION 2: Person 4 & Person 3
    story.append(Paragraph("2. Junction Audit: Person 4 (QA False-Alarm Filter) &harr; Person 3 (Temporal Detective)", h1_style))
    
    p4_p3_loopholes = [
        ("Loophole 1: Fixed SCL Band Assumption (Band 5 Crash)", "<code>get_quality_mask_s2</code> hardcoded <code>scl_band_index=4</code>. On 3-band optical or 4-band Landsat imagery, this triggered <code>IndexError</code> and silently disabled QA filtering.", "<b>Fix:</b> Implemented dynamic band inspection via <code>rasterio</code>. If bands < 5, automatically activates optical brightness/cloud thresholding."),
        ("Loophole 2: Excessive Cloud Cover Compute Waste & False Semantic Alerts", "When a tile had >85% monsoon cloud cover, Person 3 still ran expensive BIT Transformer inference. Residual eroded cloud slivers were misclassified by RemoteCLIP as 'Water/Flood'.", "<b>Fix:</b> Added <b>Early-Exit Occlusion Gate</b> in <code>compare_tiles()</code>: If valid ground < 15%, skips BIT inference immediately and returns <code>skipped_excessive_cloud_cover</code>."),
        ("Loophole 3: Array Coordinate & Channel Orientation Mismatch", "Person 4 used <code>tifffile</code> while Person 3 used <code>rasterio</code>, risking transposed axis ordering.", "<b>Fix:</b> Standardized both modules onto <code>rasterio</code> for unified CRS and spatial array alignment."),
        ("Loophole 4: Fixed 2-Pixel Halo Erosion Radius", "A fixed 2-px erosion allowed semi-transparent cirrus halos to bleed past masks on high-resolution tiles.", "<b>Fix:</b> Replaced with adaptive kernel scaling: <code>erode_pixels = max(2, min(H, W) // 128)</code>."),
        ("Loophole 5: Bypassed Sensor-Agnostic Interface Router", "<code>detective_api.py</code> hardcoded direct imports rather than routing through Person 4's sensor adapter.", "<b>Fix:</b> Routed all QA calls through <code>get_quality_mask(sensor_type='auto', ...)</code> supporting Sentinel-2, Landsat, and offline <code>.npy</code> masks.")
    ]

    for title, desc, fix in p4_p3_loopholes:
        story.append(Paragraph(f"• <b>{title}:</b> {desc}", body_style))
        story.append(Paragraph(f"&nbsp;&nbsp;↳ {fix}", body_style))

    story.append(Spacer(1, 8))

    # SECTION 3: Summary Table
    story.append(Paragraph("3. Master Remediation Matrix", h1_style))
    summary_data = [
        [Paragraph("<b>Subsystem Junction</b>", body_style), Paragraph("<b>Identified Loophole</b>", body_style), Paragraph("<b>Severity</b>", body_style), Paragraph("<b>Verification Status</b>", body_style)],
        [Paragraph("Person 1 &harr; Person 2", body_style), Paragraph("Subdirectory scan & 16-bit PIL crash", body_style), Paragraph("<font color='#DC2626'>CRITICAL</font>", body_style), Paragraph("<font color='#16A34A'><b>RESOLVED & PUSHED</b></font>", body_style)],
        [Paragraph("Person 1 &harr; Person 2", body_style), Paragraph("Contract bypass & Qdrant HTTP crash", body_style), Paragraph("<font color='#D97706'>MEDIUM</font>", body_style), Paragraph("<font color='#16A34A'><b>RESOLVED & PUSHED</b></font>", body_style)],
        [Paragraph("Person 4 &harr; Person 3", body_style), Paragraph("Fixed SCL index 4 crash on 3/4-band TIFs", body_style), Paragraph("<font color='#DC2626'>CRITICAL</font>", body_style), Paragraph("<font color='#16A34A'><b>RESOLVED & PUSHED</b></font>", body_style)],
        [Paragraph("Person 4 &harr; Person 3", body_style), Paragraph("Excessive cloud cover compute & false alerts", body_style), Paragraph("<font color='#DC2626'>HIGH</font>", body_style), Paragraph("<font color='#16A34A'><b>RESOLVED & PUSHED</b></font>", body_style)],
        [Paragraph("Person 4 &harr; Person 3", body_style), Paragraph("Array alignment & adaptive halo erosion", body_style), Paragraph("<font color='#D97706'>MEDIUM</font>", body_style), Paragraph("<font color='#16A34A'><b>RESOLVED & PUSHED</b></font>", body_style)],
    ]
    summary_table = Table(summary_data, colWidths=[110, 184, 80, 130])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1E293B")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.HexColor("#FFFFFF")),
        ('BOX', (0, 0), (-1, -1), 0.5, colors.HexColor("#CBD5E1")),
        ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#E2E8F0")),
        ('TOPPADDING', (0, 0), (-1, -1), 4),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ('LEFTPADDING', (0, 0), (-1, -1), 5),
        ('RIGHTPADDING', (0, 0), (-1, -1), 5),
    ]))
    for r in range(1, len(summary_data)):
        if r % 2 == 1:
            summary_table.setStyle(TableStyle([('BACKGROUND', (0, r), (-1, r), colors.HexColor("#F8FAFC"))]))
    story.append(summary_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print(f"Successfully generated master PDF audit: {filename}")

if __name__ == "__main__":
    out_pdf = "TriNetraAI_Complete_Junction_Audit.pdf"
    if len(sys.argv) > 1:
        out_pdf = sys.argv[1]
    build_pdf(out_pdf)
