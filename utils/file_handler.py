import csv
import pandas as pd
import logging
import os
from typing import List, Dict
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

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

        # DataFrame setup
        df = pd.DataFrame(jobs_data)
        for col in ['firm', 'title', 'location', 'link']:
            if col not in df.columns:
                df[col] = ''
        df = df[['firm', 'title', 'location', 'link']]
        df.columns = ['Firm', 'Job Title', 'Location', 'Link']
        df = df.sort_values(by=['Firm', 'Job Title']).reset_index(drop=True)

        # --- Excel export ---
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

        # --- PDF export ---
        pdf_filename = filename.replace('.xlsx', '.pdf')
        doc = SimpleDocTemplate(pdf_filename, pagesize=letter)
        elements = []

        styles = getSampleStyleSheet()
        link_style = ParagraphStyle(
            name='LinkStyle',
            parent=styles['BodyText'],
            fontName='Helvetica',
            fontSize=10,
            textColor=colors.blue,
            underline=True
        )

        elements.append(Paragraph("Scraped Job Listings", styles['Title']))
        elements.append(Spacer(1, 12))

        pdf_data = [df.columns.tolist()]
        for _, row in df.iterrows():
            pdf_row = []
            for col_name in df.columns:
                val = str(row[col_name]) if row[col_name] else ''
                if col_name == 'Link' and val.startswith(('http://', 'https://')):
                    pdf_row.append(Paragraph(f'<a href="{val}">{val}</a>', link_style))
                else:
                    pdf_row.append(Paragraph(val, styles['BodyText']))
            pdf_data.append(pdf_row)

        table = Table(pdf_data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black)
        ]))

        elements.append(table)
        doc.build(elements)
        logging.info(f"PDF exported to {pdf_filename}")

    except Exception as e:
        logging.error(f"Critical error during Excel/PDF export: {e}")
