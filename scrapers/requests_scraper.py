import requests
from bs4 import BeautifulSoup
import logging
from typing import List, Dict
import time
from urllib.parse import urljoin, urlparse
from config import HEADERS

JobData = Dict[str, str]

def scrape_greenhouse_standard(firm_name: str, url: str) -> List[JobData]:
    logging.info(f"-> Starting scrape for {firm_name} (Type: greenhouse_standard)")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    jobs_list: List[JobData] = []
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error {response.status_code} fetching {url}: {e}")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Connection Error fetching {url}: {e}")
        return []
    
    soup = BeautifulSoup(response.content, 'html.parser')
    job_elements = soup.find_all('div', class_='opening')
    
    if not job_elements:
        logging.warning(f"No job elements found for {firm_name}. Structure may be different or page is empty.")
        return []

    for job_element in job_elements:
        title_element = job_element.find('a')
        location_element = job_element.find('span', class_='location')
        
        if title_element:
            try:
                title = title_element.get_text(strip=True)
                relative_link = title_element.get('href', '')
                location = location_element.get_text(strip=True) if location_element else "N/A"
                
                link = urljoin(url, relative_link)
                
                if not all([title, link, title.strip(), urlparse(link).scheme in ('http', 'https')]):
                    continue
                
                jobs_list.append({
                    'firm': firm_name.capitalize(),
                    'title': title,
                    'link': link,
                    'location': location
                })
            except Exception as e:
                logging.error(f"Error processing job element for {firm_name}: {e}")
                continue
            
    logging.info(f"Found {len(jobs_list)} jobs for {firm_name}.")
    return jobs_list

def scrape_custom_site_generic(firm_name: str, url: str) -> List[JobData]:
    logging.info(f"-> Starting scrape for {firm_name} (Type: custom_site - Generic Scraper Attempt)")
    
    session = requests.Session()
    session.headers.update(HEADERS)
    
    jobs_list: List[JobData] = []
    
    try:
        response = session.get(url, timeout=15)
        response.raise_for_status()
    except requests.exceptions.HTTPError as e:
        logging.error(f"HTTP Error {response.status_code} fetching {url}: {e}. Returning 0 jobs for potential fallback.")
        return []
    except requests.exceptions.RequestException as e:
        logging.error(f"Connection Error fetching {url}: {e}. Returning 0 jobs for potential fallback.")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    potential_job_elements = (
        soup.select('a[href*="job"]') + soup.select('a[href*="careers"]') +
        soup.select('a[href*="role"]') + soup.select('div.job-listing') +
        soup.select('li.job-item') + soup.select('div.role-item') +
        soup.select('a[class*="job"]') + soup.select('div[class*="job"]')
    )

    unique_jobs = set()

    for element in potential_job_elements:
        link = None
        title = None
        
        try:
            if element.name == 'a':
                link = element.get('href')
                title = element.get_text(strip=True)
            else:
                link_tag = element.find('a', href=True)
                if link_tag:
                    link = link_tag.get('href')
                    title = ' '.join(element.get_text(strip=True).split())
                else:
                    continue
    
            if not (title and link):
                continue

            full_link = urljoin(url, link)

            title = title.strip()
            if not (5 < len(title) < 100):
                continue
            
            if any(keyword in title.lower() for keyword in ['open role', 'career', 'alert', 'view all', 'view all jobs']):
                continue
            
            # Final link validation
            if urlparse(full_link).scheme not in ('http', 'https'):
                continue
            
            job_key = (title, full_link)
    
            if job_key not in unique_jobs:
                jobs_list.append({
                    'firm': firm_name.capitalize(),
                    'title': title,
                    'link': full_link,
                    'location': 'N/A'
                })
                unique_jobs.add(job_key)
        
        except Exception as e:
            logging.debug(f"Error processing generic element for {firm_name}: {e}")
            continue

    if not jobs_list:
        logging.warning(f"No jobs found using generic selectors for {firm_name}. (Returning 0 for potential fallback.)")
    else:
        logging.info(f"Found {len(jobs_list)} jobs for {firm_name}.")

    import random
    time.sleep(random.uniform(0.5, 1.5)) 
    
    return jobs_list