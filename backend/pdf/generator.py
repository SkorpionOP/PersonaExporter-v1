from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
from reportlab.lib.styles import getSampleStyleSheet
import io
import base64

def generate_persona_pdf(persona_data: dict, chart_base64: str = None) -> bytes:
    """Generates a PDF report for the persona and returns it as bytes."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=letter)
    
    styles = getSampleStyleSheet()
    story = []
    
    # Title
    story.append(Paragraph("PersonaForge - Personality Report", styles['Title']))
    story.append(Spacer(1, 12))
    
    # Overview
    overview_text = persona_data.get('personality', {}).get('overview', 'No overview available.')
    story.append(Paragraph("Overview", styles['Heading2']))
    story.append(Paragraph(overview_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Stats
    stats = persona_data.get('statistics', {})
    story.append(Paragraph("Statistics", styles['Heading2']))
    stats_text = f"Total Messages: {stats.get('total_messages', 0)}<br/>"
    stats_text += f"Total Words: {stats.get('total_words', 0)}"
    story.append(Paragraph(stats_text, styles['Normal']))
    story.append(Spacer(1, 12))
    
    # Chart (if available)
    if chart_base64:
        try:
            imgdata = base64.b64decode(chart_base64)
            img_io = io.BytesIO(imgdata)
            img = Image(img_io, width=400, height=200)
            story.append(img)
            story.append(Spacer(1, 12))
        except Exception:
            pass
            
    doc.build(story)
    
    buf.seek(0)
    return buf.read()
