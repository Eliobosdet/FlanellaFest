import io  # <-- QUESTO È IL MANCANTE!
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm

def generate_membership_pdf(participant):
    """
    Genera un PDF in memoria (BytesIO) del Verbale di Ammissione Socio.
    """
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=2*cm,
        leftMargin=2*cm,
        topMargin=2*cm,
        bottomMargin=2*cm
    )

    styles = getSampleStyleSheet()
    
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontSize=16,
        leading=20,
        alignment=1, # Centrato
        textColor=colors.HexColor("#1A1A1A"),
        spaceAfter=15,
        fontName="Helvetica-Bold"
    )
    
    header_right_style = ParagraphStyle(
        'HeaderRight',
        parent=styles['Normal'],
        fontSize=9,
        leading=12,
        alignment=2, # Allineato a destra
        textColor=colors.HexColor("#4A4A4A")
    )
    
    body_style = ParagraphStyle(
        'BodyTextCustom',
        parent=styles['Normal'],
        fontSize=10,
        leading=15,
        textColor=colors.HexColor("#2C2C2C"),
        alignment=4 # Giustificato
    )

    story = []

    # 1. Intestazione Associazione
    header_text = """
    <b>ASSOCIAZIONE FLANELLA</b><br/>
    Via del Castello 33/D<br/>
    41042 Fiorano Modenese (MO)<br/>
    C.F.: 94237310365<br/>
    Email: flanellafest@gmail.com
    """
    story.append(Paragraph(header_text, header_right_style))
    story.append(Spacer(1, 15))
    story.append(HRFlowable(width="100%", thickness=1, color=colors.HexColor("#CCCCCC"), spaceAfter=20))

    # 2. Titolo del Documento
    story.append(Paragraph("VERBALE DI AMMISSIONE SOCIO", title_style))
    story.append(Spacer(1, 10))

    # 3. Data e Ora di iscrizione
    created_at = getattr(participant, 'created_at', datetime.now())
    data_ora_str = created_at.strftime("%d/%m/%Y alle ore %H:%M")
    
    story.append(Paragraph(f"<b>Data e Ora Registrazione:</b> {data_ora_str}", body_style))
    story.append(Spacer(1, 15))

    # Fallback per i nomi dei campi (inglese / italiano)
    b_place = getattr(participant, 'birth_place', None) or getattr(participant, 'luogo_di_nascita', '-')
    b_date = getattr(participant, 'birth_date', None) or getattr(participant, 'data_di_nascita', None)
    b_date_str = b_date.strftime('%d/%m/%Y') if (b_date and hasattr(b_date, 'strftime')) else '-'
    
    addr = getattr(participant, 'address', None) or getattr(participant, 'indirizzo', '')
    cap_val = getattr(participant, 'zip_code', None) or getattr(participant, 'cap', '')
    city_val = getattr(participant, 'city', None) or getattr(participant, 'citta', '')
    prov_val = getattr(participant, 'province', None) or getattr(participant, 'provincia', '')
    cf_val = getattr(participant, 'fiscal_code', None) or getattr(participant, 'codice_fiscale', '-')

    # 4. Tabella Dati Personali del Socio (Senza tag <code> non supportati)
    data_socio = [
        [Paragraph("<b>Nominativo:</b>", body_style), Paragraph(f"{participant.first_name} {participant.last_name}", body_style)],
        [Paragraph("<b>Nato/a a:</b>", body_style), Paragraph(f"{b_place} il {b_date_str}", body_style)],
        [Paragraph("<b>Residente in:</b>", body_style), Paragraph(f"{addr}, {cap_val} {city_val} ({prov_val})", body_style)],
        [Paragraph("<b>Codice Fiscale:</b>", body_style), Paragraph(f"<font name='Courier'><b>{str(cf_val).upper()}</b></font>", body_style)],
    ]

    table = Table(data_socio, colWidths=[4*cm, 13*cm])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor("#F9F9F9")),
        ('PADDING', (0,0), (-1,-1), 8),
        ('VALIGN', (0,0), (-1,-1), 'MIDDLE'),
        ('GRID', (0,0), (-1,-1), 0.5, colors.HexColor("#E0E0E0")),
    ]))
    story.append(table)
    story.append(Spacer(1, 20))

    # 5. Testo del Verbale
    p1 = """
    Si certifica che il Consiglio Direttivo dell'Associazione Flanella ha esaminato la domanda di tesseramento
    presentata dal sopra citato richiedente. Riscontrata la regolarità dei dati forniti, il possesso dei requisiti
    statutari e il versamento della quota associativa prevista per l'anno in corso, si delibera formale
    <strong>ammissione del richiedente in qualità di Socio dell'Associazione Flanella</strong>.
    """
    story.append(Paragraph(p1, body_style))
    story.append(Spacer(1, 12))

    p2 = """
    Con l'ammissione, il Socio dichiara di aver preso visione e di accettare integralmente lo Statuto dell'Associazione,
    il Regolamento interno e l'Informativa sul trattamento dei dati personali (GDPR).
    """
    story.append(Paragraph(p2, body_style))
    story.append(Spacer(1, 35))

    # 6. Firma dell'Associazione
    firma_data = [
        [Paragraph("<b>Il Consiglio Direttivo</b><br/>Associazione Flanella", body_style), Paragraph("<b>Firma del Socio</b><br/><i>(Confermata telematicamente)</i>", body_style)]
    ]
    firma_table = Table(firma_data, colWidths=[8.5*cm, 8.5*cm])
    firma_table.setStyle(TableStyle([
        ('ALIGN', (0,0), (-1,-1), 'CENTER'),
        ('VALIGN', (0,0), (-1,-1), 'TOP'),
    ]))
    story.append(firma_table)

    # Costruzione del PDF
    doc.build(story)
    
    pdf_bytes = buffer.getvalue()
    buffer.close()
    return pdf_bytes