"""Four independently art-directed A4 layouts based on the user's references."""
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from xml.sax.saxutils import escape

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import Flowable, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

LABELS = {'summary': 'GIỚI THIỆU', 'skills': 'KỸ NĂNG', 'education': 'HỌC VẤN',
          'experience': 'KINH NGHIỆM', 'projects': 'DỰ ÁN', 'languages': 'NGÔN NGỮ',
          'certifications': 'CHỨNG CHỈ', 'interests': 'SỞ THÍCH'}
ALIASES = {'forest': 'monochrome', 'portrait': 'gradient'}


@lru_cache(maxsize=1)
def display_font(fallback):
    path = Path('C:/Windows/Fonts/ARIALNB.TTF')
    if path.is_file():
        font = TTFont('CVCondensedBold', str(path))
        # Many Arial Narrow builds lack the precomposed Vietnamese glyphs.
        if all(code in font.face.charToGlyph for code in range(0x1EA0, 0x1EFA)):
            pdfmetrics.registerFont(font)
            return 'CVCondensedBold'
    return fallback


class SectionTitle(Flowable):
    def __init__(self, text, variant, side, font):
        super().__init__()
        self.text, self.variant, self.side, self.font = text, variant, side, font
        self.height = 35 if variant in ('lavender', 'gradient') else 31
        self.keepWithNext = True

    def wrap(self, available_width, available_height):
        self.width = available_width
        return self.width, self.height

    def draw(self):
        c = self.canv
        variant, side, width = self.variant, self.side, self.width
        c.saveState()
        if variant == 'monochrome' and not side:
            label_width = min(width, max(115, pdfmetrics.stringWidth(self.text, self.font, 10) + 30))
            x = width - label_width
            c.setFillColor(colors.HexColor('#111111'))
            path = c.beginPath()
            path.moveTo(x, 13); path.lineTo(x + 10, 23); path.lineTo(width, 23)
            path.lineTo(width, 3); path.lineTo(x + 10, 3); path.close()
            c.drawPath(path, fill=1, stroke=0)
            c.setFillColor(colors.white)
            c.setFont(self.font, 10)
            c.drawCentredString(x + label_width / 2 + 4, 10, self.text)
        elif variant == 'lavender':
            c.setFillColor(colors.HexColor('#7477A3'))
            # Keep the accent completely above the Vietnamese glyphs, including
            # their upper diacritics, rather than crossing the heading's cap height.
            c.rect(0, 28, min(44, width * .35), 4, fill=1, stroke=0)
            c.setFillColor(colors.HexColor('#15151B'))
            size = 12.5 if side else 15
            size = min(size, (width - 2) / max(pdfmetrics.stringWidth(self.text, self.font, 1), 1))
            c.setFont(self.font, size)
            c.drawString(0, 7, self.text)
        elif variant == 'editorial':
            c.setStrokeColor(colors.HexColor('#A8A8A8'))
            c.setLineWidth(.7)
            c.line(0, 29, width, 29)
            c.setFont(self.font, 15)
            c.setFillColor(colors.HexColor('#3C3C3C'))
            c.drawString(0, 8, self.text)
        elif variant == 'gradient':
            c.setFont(self.font, 13 if side else 16)
            c.setFillColor(colors.white if side else colors.HexColor('#536587'))
            c.drawString(0, 9, self.text)
        else:
            c.setFont(self.font, 8.8)
            c.setFillColor(colors.white)
            c.drawString(0, 10, self.text)
        c.restoreState()


class SectionStart(Flowable):
    """Keep a section label with its first line during column pagination."""
    def __init__(self, heading, first):
        super().__init__()
        self.heading, self.first = heading, first

    def wrap(self, width, height):
        self.width = width
        self.heading_height = self.heading.wrap(width, height)[1]
        self.first_height = self.first.wrap(width, height)[1]
        self.height = self.heading_height + self.first_height + self.first.getSpaceAfter()
        return width, self.height

    def draw(self):
        self.heading.drawOn(self.canv, 0, self.first_height + self.first.getSpaceAfter())
        self.first.drawOn(self.canv, 0, self.first.getSpaceAfter())

    def split(self, width, height):
        heading_height = self.heading.wrap(width, height)[1]
        available = height - heading_height - self.first.getSpaceAfter()
        if available <= 0:
            return []
        parts = self.first.split(width, available)
        if not parts:
            return []
        return [SectionStart(self.heading, parts[0]), *parts[1:]]


def render_reference_pdf(document, template_id, photo, fonts):
    variant = ALIASES.get(template_id, template_id)
    if variant not in ('monochrome', 'lavender', 'editorial', 'gradient'):
        raise ValueError('Unknown CV template')
    if variant in ('lavender', 'gradient') and not photo:
        raise ValueError('This template requires a portrait')
    regular, bold = fonts
    condensed = display_font(bold)
    page_width, page_height = A4
    margin = 26 if variant in ('monochrome', 'editorial') else 0
    total = page_width - 2 * margin
    side_width = {'monochrome': 180, 'lavender': 215, 'editorial': 221, 'gradient': 220}[variant]
    main_width = total - side_width
    header_height = {'monochrome': 112, 'lavender': 205, 'editorial': 190, 'gradient': 28}[variant]
    top = margin + header_height
    side_pad = 27 if variant != 'lavender' else 19
    right_pad = 25
    dark_side = variant in ('monochrome', 'gradient')
    text_color = '#FFFFFF' if dark_side else '#38383D'
    body_size = 9.3 if variant != 'lavender' else 9.8
    body = ParagraphStyle('ReferenceBody', fontName=regular, fontSize=body_size,
                          leading=13.4, spaceAfter=2.5, textColor=colors.HexColor('#323238'),
                          splitLongWords=True, allowWidows=0, allowOrphans=0)
    side = ParagraphStyle('ReferenceSide', parent=body, fontSize=9.1, leading=13.8,
                          textColor=colors.HexColor(text_color))
    entry = ParagraphStyle('ReferenceEntry', parent=body, fontName=bold, spaceBefore=3, spaceAfter=4)
    name_style = ParagraphStyle('ReferenceName', parent=body,
                               fontName=condensed if variant == 'editorial' else bold,
                               fontSize=28 if variant == 'lavender' else 25,
                               leading=31, spaceAfter=8,
                               textColor=colors.HexColor('#343646') if variant == 'lavender' else colors.white)
    role_style = ParagraphStyle('ReferenceRole', parent=body, fontName=bold, fontSize=11,
                               leading=16, textColor=colors.HexColor('#181820') if variant == 'lavender' else colors.white)
    name_p = Paragraph(escape(document.full_name), name_style)
    role_p = Paragraph(escape(document.title), role_style) if document.title else None
    if variant != 'gradient':
        header_text_width = total - 165 if variant == 'editorial' else main_width - 44
        if not photo and variant in ('monochrome', 'editorial'):
            header_text_width = total - 54
        name_h = name_p.wrap(header_text_width, page_height)[1]
        role_h = role_p.wrap(header_text_width, page_height)[1] if role_p else 0
        header_height = max(header_height, name_h + role_h + (105 if variant in ('lavender', 'editorial') else 36))
        if variant in ('lavender', 'editorial'):
            contact_style = ParagraphStyle('HeaderContact', parent=body, fontSize=8.7, leading=13, spaceAfter=3)
            contact_height = sum(Paragraph(escape(value), contact_style).wrap(header_text_width, page_height)[1] + 3
                                 for value in (document.phone, document.email, document.address) if value)
            banner_height = max(98, name_h + role_h + 42)
            header_height = max(header_height, (banner_height + 22 if variant == 'editorial' else 37 + name_h + role_h + 20) + contact_height + 16)
        top = margin + header_height
    else:
        name_h = role_h = 0
    left, right = [], []

    def add_text(destination, text, style):
        # Blank lines separate entries. Only explicit entry headers get bold type.
        for block in text.split('\n\n'):
            lines = [line.strip() for line in block.splitlines() if line.strip()]
            for index, line in enumerate(lines):
                selected = entry if style is body and index == 0 and ('|' in line or len(lines) > 2) else style
                if line.startswith(('- ', '• ')):
                    destination.append(Paragraph(escape(line[2:]), selected, bulletText='•'))
                else:
                    destination.append(Paragraph(escape(line), selected))
            if lines:
                destination.append(Spacer(1, 5))

    def add_section(destination, field, is_side):
        value = getattr(document, field, '')
        if not value:
            return
        heading = SectionTitle(LABELS[field], variant, is_side, condensed if variant == 'editorial' else bold)
        content = []
        add_text(content, value, side if is_side else body)
        destination.append(SectionStart(heading, content[0]))
        destination.extend(content[1:])
        destination.append(Spacer(1, 12 if is_side else 6))

    def add_contacts(destination):
        contacts = [('EMAIL', document.email), ('ĐIỆN THOẠI', document.phone), ('ĐỊA CHỈ', document.address)]
        if not any(value for _, value in contacts):
            return
        if variant == 'monochrome':
            destination.append(SectionTitle('LIÊN HỆ', variant, True, bold))
        tiny = ParagraphStyle('ContactCaption', parent=side, fontName=bold, fontSize=7, leading=10, spaceAfter=3)
        for label, value in contacts:
            if value:
                destination.append(Paragraph(label, tiny))
                add_text(destination, value, side)
                destination.append(Spacer(1, 6))
        destination.append(Spacer(1, 17))

    if variant == 'gradient':
        left += [Spacer(1, 188), name_p]
        if role_p:
            left.append(role_p)
        left.append(Spacer(1, 15))
        if document.summary:
            add_text(left, document.summary, side)
            left.append(Spacer(1, 22))
        add_contacts(left)
        for field in ('languages', 'interests'):
            add_section(left, field, True)
        for field in ('experience', 'education', 'skills', 'projects', 'certifications'):
            add_section(right, field, False)
    elif variant == 'monochrome':
        add_section(left, 'summary', True)
        add_contacts(left)
        for field in ('languages', 'interests', 'certifications'):
            add_section(left, field, True)
        for field in ('experience', 'skills', 'education', 'projects'):
            add_section(right, field, False)
    elif variant == 'lavender':
        for field in ('summary', 'skills', 'languages', 'interests'):
            add_section(left, field, True)
        for field in ('experience', 'education', 'projects', 'certifications'):
            add_section(right, field, False)
    else:
        for field in ('summary', 'skills', 'certifications', 'interests', 'languages'):
            add_section(left, field, True)
        for field in ('education', 'experience', 'projects'):
            add_section(right, field, False)

    # A splittable row lets the two columns continue independently on new pages.
    columns = Table([[left or [Spacer(1, 1)], right or [Spacer(1, 1)]]],
                    colWidths=[side_width, main_width], splitByRow=0, splitInRow=1,
                    style=TableStyle([
                        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                        ('LEFTPADDING', (0, 0), (0, 0), side_pad),
                        ('RIGHTPADDING', (0, 0), (0, 0), side_pad + (14 if variant == 'lavender' else 0)),
                        ('LEFTPADDING', (1, 0), (1, 0), right_pad),
                        ('RIGHTPADDING', (1, 0), (1, 0), right_pad),
                        ('TOPPADDING', (0, 0), (-1, -1), 0),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
                    ]))

    def image_on(canvas, x, y, size, shape):
        if not photo:
            return
        canvas.saveState()
        clip = canvas.beginPath()
        if shape == 'circle':
            clip.circle(x + size / 2, y + size / 2, size / 2)
        elif shape == 'rounded':
            clip.roundRect(x, y, size, size, 20)
        else:
            clip.rect(x, y, size, size)
        canvas.clipPath(clip, stroke=0)
        canvas.drawImage(ImageReader(BytesIO(photo)), x, y, width=size, height=size, mask='auto')
        canvas.restoreState()
        if shape in ('circle', 'square'):
            canvas.setLineWidth(2.5)
            canvas.setStrokeColor(colors.white if shape == 'circle' else colors.HexColor('#777777'))
            if shape == 'circle': canvas.circle(x + size / 2, y + size / 2, size / 2, stroke=1, fill=0)
            else: canvas.rect(x - 4, y - 4, size + 8, size + 8, stroke=1, fill=0)

    def draw_header(canvas, doc):
        canvas.saveState()
        if variant == 'monochrome':
            canvas.setFillColor(colors.HexColor('#111111'))
            canvas.rect(margin, 28, side_width, page_height - margin - 28, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor('#858585'))
            canvas.rect(margin + side_width, page_height - top, main_width, header_height, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor('#B8B8B8' if photo else '#858585'))
            canvas.rect(margin, page_height - top, side_width, header_height, fill=1, stroke=0)
            image_on(canvas, margin + (side_width - 77) / 2, page_height - margin - 94, 77, 'circle')
        elif variant == 'lavender':
            canvas.setFillColor(colors.HexColor('#DEDEE5'))
            canvas.rect(0, 0, page_width, page_height, fill=1, stroke=0)
            canvas.setFillColor(colors.HexColor('#686C96'))
            canvas.rect(side_width - 24, 0, 24, page_height - top, fill=1, stroke=0)
            canvas.setFillColor(colors.white)
            canvas.rect(side_width - 30, 0, 6, page_height, fill=1, stroke=0)
            image_on(canvas, 8, page_height - 192, 180, 'rounded')
        elif variant == 'editorial':
            canvas.setFillColor(colors.HexColor('#505050'))
            canvas.rect(margin, page_height - margin - banner_height, total, banner_height - 17, fill=1, stroke=0)
            if photo:
                canvas.setFillColor(colors.white)
                canvas.rect(margin + 12, page_height - margin - 118, 124, 124, fill=1, stroke=0)
                image_on(canvas, margin + 20, page_height - margin - 110, 108, 'square')
            canvas.setStrokeColor(colors.HexColor('#AAAAAA'))
            canvas.setLineWidth(.7)
            canvas.line(margin + side_width, 32, margin + side_width, page_height - top + 6)
        else:
            canvas.saveState()
            clip = canvas.beginPath()
            clip.rect(0, 0, side_width, page_height)
            canvas.clipPath(clip, stroke=0)
            canvas.linearGradient(0, page_height, 0, 0,
                                  [colors.HexColor('#186382'), colors.HexColor('#7C439B')])
            canvas.restoreState()
            # Photo only on the first page; following pages continue the text column.
            if doc.page == 1:
                image_on(canvas, (side_width - 178) / 2, page_height - 205, 178, 'circle')
        if variant != 'gradient':
            x = margin + 145 if variant == 'editorial' else margin + side_width + right_pad
            if not photo and variant in ('monochrome', 'editorial'):
                x = margin + 27
            y = page_height - margin - (37 if variant != 'editorial' else 29)
            name_p.drawOn(canvas, x, y - name_h)
            if role_p:
                role_p.drawOn(canvas, x, y - name_h - role_h - 5)
            if variant in ('lavender', 'editorial'):
                contact_style = ParagraphStyle('HeaderContact', parent=body, fontSize=8.7, leading=13, spaceAfter=3)
                contact_y = page_height - margin - banner_height - 17 if variant == 'editorial' else y - name_h - role_h - 20
                for value in (document.phone, document.email, document.address):
                    if value:
                        p = Paragraph(escape(value), contact_style)
                        height = p.wrap(header_text_width, page_height)[1]
                        p.drawOn(canvas, x, contact_y - height)
                        contact_y -= height + 3
        canvas.setFont(regular, 7)
        canvas.setFillColor(colors.HexColor('#72727C'))
        canvas.drawRightString(page_width - 24, 13, f'Trang {doc.page}')
        canvas.restoreState()

    output = BytesIO()
    pdf = SimpleDocTemplate(output, pagesize=A4, leftMargin=margin, rightMargin=margin,
                            topMargin=top, bottomMargin=30, title=f'CV {document.full_name}', author=document.full_name)
    pdf.build([columns], onFirstPage=draw_header, onLaterPages=draw_header)
    return output.getvalue()
