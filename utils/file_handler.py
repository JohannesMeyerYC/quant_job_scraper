import csv
import pandas as pd
import logging
import os
from typing import List, Dict
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from datetime import datetime
from reportlab.lib.pagesizes import letter, A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch

JobData = Dict[str, str]
FirmConfig = Dict[str, str]

def get_firm_list(csv_filename: str = 'firms.csv') -> List[FirmConfig]:
    firms: List[FirmConfig] = []

    if not os.path.exists(csv_filename):
        logging.error(f"Error: The configuration file '{csv_filename}' was not found.")
        return []

    try:
        with open(csv_filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file)
            required_cols = ['firm_name', 'url', 'platform_type']
            if not all(col in reader.fieldnames for col in required_cols):
                logging.error(f"CSV missing required columns. Found: {reader.fieldnames}")
                return []

            for row in reader:
                firm_name = row.get('firm_name', '').strip()
                url = row.get('url', '').strip()
                platform_type = row.get('platform_type', '').strip().lower()

                if firm_name and url and platform_type:
                    clean_type = platform_type.replace('_standard', '').replace('_custom', '')
                    firms.append({'firm': firm_name, 'url': url, 'type': clean_type})
                else:
                    logging.warning(f"Skipping row due to missing data: {row}")

        logging.info(f"Successfully loaded {len(firms)} valid firm(s) from {csv_filename}.")
        return firms

    except Exception as e:
        logging.error(f"Unexpected error reading firm CSV: {e}")
        return []


def validate_job_data(jobs_data: List[JobData]) -> List[JobData]:
    valid_jobs: List[JobData] = []
    unique_jobs = set()
    dropped_count = 0

    for job in jobs_data:
        firm = job.get('firm', '').strip()
        title = job.get('title', '').strip()
        location = job.get('location', '').strip()
        link = job.get('link', '').strip()

        if not (firm and title and link):
            logging.warning(f"Dropping job (missing fields): {job}")
            dropped_count += 1
            continue

        if not link.startswith(('http://', 'https://')):
            logging.warning(f"Dropping job (invalid link): {link}")
            dropped_count += 1
            continue

        key = (firm.lower(), title.lower(), location.lower())
        if key in unique_jobs:
            dropped_count += 1
            continue

        valid_jobs.append({
            "firm": firm,
            "title": title,
            "location": location or "N/A",
            "link": link
        })
        unique_jobs.add(key)

    if dropped_count:
        logging.info(f"Validation complete. Dropped {dropped_count} jobs.")
    return valid_jobs


def export_to_excel(jobs_data: List[JobData], filename: str = "output/jobs.xlsx"):
    if not jobs_data:
        logging.warning("No job data collected. Skipping Excel/PDF export.")
        return

    try:
        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)

        df = pd.DataFrame(jobs_data)
        for col in ['firm', 'title', 'location', 'link']:
            if col not in df.columns:
                df[col] = ''
        df = df[['firm', 'title', 'location', 'link']]
        df.columns = ['Firm', 'Job Title', 'Location', 'Link']
        df = df.sort_values(by=['Firm', 'Job Title']).reset_index(drop=True)

        wb = Workbook()
        ws = wb.active
        ws.title = "Scraped Jobs"

        for r_idx, row in enumerate(dataframe_to_rows(df, header=True, index=False)):
            ws.append(row)
            if r_idx == 0:
                for cell in ws[1]:
                    cell.font = Font(bold=True, size=12)
                    cell.alignment = Alignment(horizontal='center', vertical='center')

        for col in ws.columns:
            max_len = max(len(str(c.value)) if c.value else 0 for c in col)
            col_letter = col[0].column_letter
            ws.column_dimensions[col_letter].width = min(max_len + 5, 75)
            if col[0].value == 'Link':
                for cell in col[1:]:
                    if cell.value.startswith(('http://', 'https://')):
                        cell.hyperlink = cell.value
                        cell.font = Font(color='0000FF', underline='single')

        wb.save(filename)
        logging.info(f"Excel exported to {filename}")

        pdf_filename = filename.replace('.xlsx', '.pdf')
        
        PAGE_WIDTH, PAGE_HEIGHT = A4
        LEFT_MARGIN = 0.5 * inch
        RIGHT_MARGIN = 0.5 * inch
        TABLE_WIDTH = PAGE_WIDTH - LEFT_MARGIN - RIGHT_MARGIN

        doc = SimpleDocTemplate(
            pdf_filename, 
            pagesize=A4, 
            leftMargin=LEFT_MARGIN,
            rightMargin=RIGHT_MARGIN
        )
        elements = []

        styles = getSampleStyleSheet()
        cell_style = ParagraphStyle(
            name='CellText',
            parent=styles['Normal'],
            fontName='Helvetica',
            fontSize=8,
            leading=10,
        )
        link_style = ParagraphStyle(
            name='LinkStyle',
            parent=cell_style,
            textColor=colors.blue,
            underline=False
        )
        title_style = styles['Title']
        title_style.alignment = 1

        elements.append(Paragraph("Scraped Job Listings", title_style))
        elements.append(Paragraph(f"Report Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}", styles['Normal']))
        elements.append(Spacer(1, 18))

        col_widths = [
            TABLE_WIDTH * 0.15, 
            TABLE_WIDTH * 0.35, 
            TABLE_WIDTH * 0.20, 
            TABLE_WIDTH * 0.30
        ]
        
        PDF_COLUMNS = ['Firm', 'Job Title', 'Location', 'Link']
        
        pdf_data = [PDF_COLUMNS] 
        for _, row in df[PDF_COLUMNS].iterrows(): 
            pdf_row = []
            for col_name in PDF_COLUMNS: 
                val = str(row[col_name]) if row[col_name] else ''
                if col_name == 'Link' and val.startswith(('http://', 'https://')):
                    paragraph = Paragraph(f'<a href="{val}">{val}</a>', link_style)
                    pdf_row.append(paragraph)
                else:
                    pdf_row.append(Paragraph(val, cell_style))
            pdf_data.append(pdf_row)

        table = Table(pdf_data, colWidths=col_widths, repeatRows=1) 
        
        style_commands = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#2a4f6d')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#dddddd')),
        ]

        for i in range(1, len(pdf_data)):
            if i % 2 == 0:
                style_commands.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#f5f5f5')))

        table.setStyle(TableStyle(style_commands))

        elements.append(table)
        doc.build(elements)
        logging.info(f"PDF exported to {pdf_filename}")

    except Exception as e:
        logging.error(f"Critical error during Excel/PDF export: {e}")
