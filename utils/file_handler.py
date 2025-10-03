import csv
import pandas as pd
import logging
import os
from typing import List, Dict, Any
from openpyxl.utils.dataframe import dataframe_to_rows
from openpyxl import Workbook
from openpyxl.styles import Font, Border, Side, Alignment
from datetime import datetime

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
                logging.error(f"Error: CSV file '{csv_filename}' is missing required columns. Found: {reader.fieldnames}. Required: {required_cols}.")
                return []
            
            for row in reader:
                firm_name = row.get('firm_name', '').strip()
                url = row.get('url', '').strip()
                platform_type = row.get('platform_type', '').strip().lower()
                
                if firm_name and url and platform_type:
                    clean_type = platform_type.replace('_standard', '').replace('_custom', '')
                    
                    firms.append({
                        'firm': firm_name,
                        'url': url,
                        'type': clean_type
                    })
                else:
                    logging.warning(f"Skipping row due to missing data: {row}")

        logging.info(f"Successfully loaded {len(firms)} valid firm(s) from {csv_filename}.")
        return firms
        
    except UnicodeDecodeError:
        logging.error(f"Error: Failed to read '{csv_filename}'. Check that the encoding is UTF-8.")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while reading the firm CSV: {e}")
        return []

def export_to_excel(jobs_data: List[JobData], filename: str = "output/jobs.xlsx"):
    if not jobs_data:
        logging.warning("No job data collected. Skipping Excel export.")
        return
    
    try:
        output_dir = os.path.dirname(filename)
        if output_dir and not os.path.exists(output_dir):
            os.makedirs(output_dir)
            logging.info(f"Created output directory: {output_dir}")

        df = pd.DataFrame(jobs_data)
        
        if 'location' in df.columns:
            if (df['location'].isin(['N/A', ''])).all():
                 df = df.drop(columns=['location'])
            else:
                 df['location'] = df['location'].replace({'N/A': ''})
        
        if 'firm' in df.columns and 'title' in df.columns and 'link' in df.columns:
            column_order = ['firm', 'title', 'location', 'link']
            df = df[[col for col in column_order if col in df.columns]]
            df.columns = ['Firm', 'Job Title', 'Location', 'Link']
        
        df = df.sort_values(by=['Firm', 'Job Title']).reset_index(drop=True)
        
        
        wb = Workbook()
        ws = wb.active
        ws.title = "Scraped Jobs"
        
        for r_idx, row in enumerate(dataframe_to_rows(df, header=True, index=False)):
            ws.append(row)

            if r_idx == 0:
                bold_font = Font(bold=True, size=12)
                for cell in ws[1]:
                    cell.font = bold_font
                    cell.alignment = Alignment(horizontal='center', vertical='center')

        for col in ws.columns:
            max_length = 0
            column = col[0].column_letter
            for cell in col:
                try:
                    if cell.value and column == 'D':
                        cell.hyperlink = cell.value
                        cell.style = "Hyperlink"
                        cell.font = Font(color='0000FF', underline='single') 
                        
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except Exception as e:
                    logging.debug(f"Styling error: {e}")
                    
            adjusted_width = (max_length + 2)
            if column == 'D': 
                adjusted_width = 75
            elif column == 'B': 
                adjusted_width = 60
                
            ws.column_dimensions[column].width = adjusted_width

        meta_ws = wb.create_sheet(title="Metadata")
        meta_ws['A1'] = "Scrape Date"
        meta_ws['B1'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        meta_ws['A2'] = "Total Jobs Found"
        meta_ws['B2'] = len(df)
        meta_ws['A1'].font = Font(bold=True)
        meta_ws['A2'].font = Font(bold=True)
        meta_ws.column_dimensions['A'].width = 20
        
        wb.save(filename)
        logging.info(f"Successfully exported {len(df)} jobs to {filename}")

    except Exception as e:
        logging.error(f"A critical error occurred during Excel export: {e}")