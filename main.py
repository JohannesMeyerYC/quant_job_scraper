import asyncio
from playwright.async_api import async_playwright, TimeoutError
import logging
from typing import List, Dict, Any
import pandas as pd
import requests
from bs4 import BeautifulSoup
import csv
import random

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

JobData = Dict[str, str]

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
}

PLAYWRIGHT_CONFIGS = {
    "Renaissance Technologies": {
        "url": "https://www.rentec.com/Careers.html",
        "job_card_selector": "a[href*='job-details']",
        "title_selector": "text", 
        "location_selector": None 
    },
    "Two Sigma": {
        "url": "https://www.twosigma.com/careers/open-roles/",
        "job_card_selector": "div.role-card-container", 
        "title_selector": "h3",
        "location_selector": "div.location-text"
    },
    "Citadel": {
        "url": "https://www.citadel.com/careers/open-opportunities/",
        "job_card_selector": "div[data-ph-id*='job-listing-item']", 
        "title_selector": "h2",
        "location_selector": "div:text('Location')" 
    },
    "Optiver": {
        "url": "https://www.optiver.com/working-at-optiver/career-opportunities",
        "job_card_selector": "a[href*='/job/']",
        "title_selector": "h3",
        "location_selector": "span[data-label='location']"
    },
    "Flow Traders": {
        "url": "https://www.flowtraders.com/careers/jobs",
        "job_card_selector": "a[href*='/vacancy/']",
        "title_selector": "h3",
        "location_selector": "div.location" 
    },
    "WorldQuant": {
        "url": "https://www.worldquant.com/careers/open-roles",
        "job_card_selector": "a[href*='/job/']",
        "title_selector": "h2",
        "location_selector": "div.location-text" 
    },
    "UBS": {
        "url": "https://www.ubs.com/global/en/careers",
        "job_card_selector": "a[data-ph-id*='job-card']",
        "title_selector": "h3",
        "location_selector": "span.location-label"
    },
    "Coinbase": {
        "url": "https://www.coinbase.com/careers/open-roles",
        "job_card_selector": "a[href*='/careers/job/']",
        "title_selector": "h4",
        "location_selector": "div.location" 
    },
    "Squarepoint Capital": {
        "url": "https://www.squarepoint-capital.com/careers",
        "job_card_selector": "a.job-listing",
        "title_selector": "h3",
        "location_selector": "span.location" 
    }
}

async def scrape_firm_playwright(
    firm_name: str, 
    url: str, 
    job_card_selector: str, 
    title_selector: str,
    location_selector: str | None,
    page: Any
) -> List[JobData]:
    is_fallback = firm_name not in [f for f in PLAYWRIGHT_CONFIGS]
    log_prefix = "FALLBACK" if is_fallback else "Playwright"
    logging.info(f"--- Starting scrape for {firm_name} (Type: {log_prefix}) ---")
    
    scraped_jobs: List[JobData] = []
    
    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=15000) 
        
        logging.info(f"Waiting for selector: '{job_card_selector}' to be visible...")
        
        await page.wait_for_selector(job_card_selector, state="visible", timeout=15000) 
        
        job_card_locators = await page.locator(job_card_selector).all()
        
        if not job_card_locators:
            logging.warning(f"No job cards found using selector '{job_card_selector}' for {firm_name}.")
            return []

        logging.info(f"Found {len(job_card_locators)} potential job listings for {firm_name}.")

        for i, card_locator in enumerate(job_card_locators):
            try:
                if title_selector == "text":
                    title = await card_locator.inner_text()
                else:
                    title_element = card_locator.locator(title_selector)
                    title = await title_element.inner_text()
                
                job_url = "URL not found on card."
                if await card_locator.evaluate("el => el.tagName === 'A'"):
                    job_url = await card_locator.get_attribute("href")
                else:
                    try:
                        job_link = card_locator.locator("a").first
                        job_url = await job_link.get_attribute("href")
                    except Exception:
                        pass

                location = "N/A"
                if location_selector:
                    try:
                        location_element = card_locator.locator(location_selector).first
                        location_text = await location_element.inner_text()
                        location = location_text.strip()
                    except Exception:
                        pass

                link = url.split('/careers')[0] + job_url if job_url and job_url.startswith('/') else job_url
                
                scraped_jobs.append({
                    "firm": firm_name,
                    "title": title.strip().replace('\n', ' '),
                    "location": location.strip(),
                    "link": link
                })
            
            except Exception as e:
                logging.error(f"Error processing job card {i} for {firm_name}: {e}")
                continue
            
    except TimeoutError:
        logging.error(f"Timeout occurred while loading or waiting for elements on {firm_name} ({url}). The site took too long to render.")
    except Exception as e:
        logging.error(f"An unexpected error occurred during scraping {firm_name}: {e}")
        
    logging.info(f"--- Finished scrape for {firm_name} with {len(scraped_jobs)} jobs found ---")
    return scraped_jobs


async def scrape_playwright_firms_async(firms_to_run: List[Dict[str, Any]]) -> List[JobData]:
    all_results: List[JobData] = []
    
    if not firms_to_run:
        return all_results

    firms_with_config = []
    firms_without_config = []
    
    for firm_data in firms_to_run:
        if firm_data['firm'] in PLAYWRIGHT_CONFIGS:
            firms_with_config.append(firm_data)
        else:
            firms_without_config.append(firm_data)

    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()

        for firm_data in firms_with_config:
            firm_name = firm_data['firm']
            config = PLAYWRIGHT_CONFIGS.get(firm_name)
            
            if config:
                jobs = await scrape_firm_playwright(
                    firm_name=firm_name,
                    url=config["url"], 
                    job_card_selector=config["job_card_selector"],
                    title_selector=config["title_selector"],
                    location_selector=config["location_selector"],
                    page=page
                )
                all_results.extend(jobs)
            else:
                logging.warning(f"Error: Playwright firm '{firm_name}' had a configuration issue. Skipping.")
                
            if firm_data != firms_with_config[-1]:
                delay = random.uniform(3, 7)
                logging.info(f"Pausing for {delay:.2f} seconds before next firm...")
                await asyncio.sleep(delay)

        for firm_data in firms_without_config:
            firm_name = firm_data['firm']
            config = PLAYWRIGHT_CONFIGS.get(firm_name)
            
            if config:
                jobs = await scrape_firm_playwright(
                    firm_name=firm_name,
                    url=config["url"], 
                    job_card_selector=config["job_card_selector"],
                    title_selector=config["title_selector"],
                    location_selector=config["location_selector"],
                    page=page
                )
                all_results.extend(jobs)
            else:
                logging.warning(f"Fallback firm '{firm_name}' could not find a Playwright configuration. Skipping.")
                
            if firm_data != firms_without_config[-1]:
                delay = random.uniform(3, 7)
                logging.info(f"Pausing for {delay:.2f} seconds before next firm...")
                await asyncio.sleep(delay)


        await browser.close()
    
    return all_results

def scrape_greenhouse_standard(firm_name, url):
    print(f"-> Starting scrape for {firm_name} (Type: greenhouse_standard)")
    try:
        response = requests.get(url, headers=HEADERS)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f" 	 Error fetching {url}: {e}")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    jobs_list = []
    job_elements = soup.find_all('div', class_='opening')
    
    if not job_elements:
        print(f" 	 No job elements found for {firm_name}. Structure may be different or page is empty.")
        return []

    for job_element in job_elements:
        title_element = job_element.find('a')
        location_element = job_element.find('span', class_='location')
        
        if title_element:
            title = title_element.get_text(strip=True)
            relative_link = title_element.get('href', '')
            location = location_element.get_text(strip=True) if location_element else "N/A"
            
            if relative_link.startswith('/'):
                base_domain = url.split('.io')[0] + '.io'
                link = base_domain + relative_link
            else:
                link = relative_link
            
            jobs_list.append({
                'firm': firm_name.capitalize(),
                'title': title,
                'link': link,
                'location': location
            })
            
    print(f" 	 Found {len(jobs_list)} jobs for {firm_name}.")
    return jobs_list


def scrape_custom_site_generic(firm_name, url):
    print(f"-> Starting scrape for {firm_name} (Type: custom_site - Generic Scraper Attempt)")
    
    jobs_list = []
    base_url = url.split('//')[0] + '//' + url.split('//')[1].split('/')[0]

    try:
        response = requests.get(url, headers=HEADERS, timeout=5)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"   Error fetching {url}: {e}. Returning 0 jobs for potential fallback.")
        return []

    soup = BeautifulSoup(response.content, 'html.parser')
    
    potential_job_elements = (
        soup.select('a[href*="job"]') +
        soup.select('a[href*="careers"]') +
        soup.select('a[href*="role"]') +
        soup.select('div.job-listing') +
        soup.select('li.job-item') +
        soup.select('div.role-item') +
        soup.select('a[class*="job"]') +
        soup.select('div[class*="job"]')
    )

    unique_jobs = set()

    for element in potential_job_elements:
        link = None
        title = None

        if element.name == 'a':
            link = element.get('href')
            title = element.get_text(strip=True)
        else:
            link_tag = element.find('a', href=True)
            if link_tag:
                link = link_tag.get('href')
                title = element.get_text(strip=True).split('\n')[0] 
            else:
                continue

        if title and link:
            title = title.strip()
            if len(title) > 100 or len(title) < 5:
                continue
                
            if 'open role' in title.lower() or 'career' in title.lower() or 'alert' in title.lower() or 'view all' in title.lower():
                continue

            if link.startswith('/'):
                link = base_url + link
            elif not link.startswith('http'):
                continue
            
            job_key = (title, link)

            if job_key not in unique_jobs:
                jobs_list.append({
                    'firm': firm_name.capitalize(),
                    'title': title,
                    'link': link,
                    'location': 'N/A'
                })
                unique_jobs.add(job_key)
    
    if not jobs_list and len(potential_job_elements) > 0:
        print(f"   Warning: Generic scraper found elements but filtered all results for {firm_name}. (0 jobs found)")
    elif not jobs_list:
        print(f"   No jobs found using generic selectors for {firm_name}. (0 jobs found)")
    else:
        print(f"   Found {len(jobs_list)} jobs for {firm_name}.")

    return jobs_list

def get_firm_list(csv_filename='firms.csv'):
    firms = []
    try:
        with open(csv_filename, mode='r', encoding='utf-8') as file:
            reader = csv.DictReader(file) 
            for row in reader:
                if all(row.get(col) for col in ['firm_name', 'url', 'platform_type']):
                    firms.append({
                        'firm': row['firm_name'].strip(),
                        'url': row['url'].strip(),
                        'type': row['platform_type'].strip().lower().replace('_custom', '')
                    })
        print(f"Read {len(firms)} firm(s) from {csv_filename}.")
        return firms
    except FileNotFoundError:
        print(f"Error: The file {csv_filename} was not found. Please create it with columns: firm_name,url,platform_type.")
        return []
    except Exception as e:
        print(f"An error occurred reading the CSV: {e}")
        return []

async def run_scrapers_async(firm_list: List[Dict[str, str]]):
    all_jobs = []
    
    sync_tasks = []
    sync_firm_map = {}
    initial_async_firms = []

    for firm_data in firm_list:
        firm_name = firm_data['firm']
        platform_type = firm_data['type']
        url = firm_data['url']

        if platform_type == 'greenhouse_standard':
            task = asyncio.to_thread(scrape_greenhouse_standard, firm_name, url)
            sync_tasks.append(task)
            sync_firm_map[len(sync_tasks) - 1] = firm_data
            
        elif platform_type == 'custom_site':
            task = asyncio.to_thread(scrape_custom_site_generic, firm_name, url)
            sync_tasks.append(task)
            sync_firm_map[len(sync_tasks) - 1] = firm_data
            
        elif platform_type == 'playwright':
            if firm_name in PLAYWRIGHT_CONFIGS:
                initial_async_firms.append(firm_data)
            else:
                logging.warning(f"-> Skipping {firm_name}: Playwright requested but config missing in PLAYWRIGHT_CONFIGS.")
        
        else:
            logging.warning(f"-> Skipping {firm_name}: Unknown platform_type '{platform_type}'.")

    print("\nScheduling synchronous scrapers (Greenhouse/Generic)...")
    fallback_async_firms = []
    
    if sync_tasks:
        sync_results = await asyncio.gather(*sync_tasks, return_exceptions=True)
        
        for i, result in enumerate(sync_results):
            firm_data = sync_firm_map.get(i)
            firm_name = firm_data['firm']
            platform_type = firm_data['type']
            
            if isinstance(result, Exception):
                logging.error(f"Error in synchronous scraper task for {firm_name}: {result}")
                
                if platform_type == 'custom_site' and firm_name in PLAYWRIGHT_CONFIGS:
                    logging.info(f"FALLBACK: Triggering Playwright for {firm_name} due to synchronous error.")
                    fallback_async_firms.append(firm_data)
                
            elif not result and platform_type == 'custom_site' and firm_name in PLAYWRIGHT_CONFIGS:
                logging.info(f"FALLBACK: Triggering Playwright for {firm_name}. Generic scraper found 0 jobs.")
                fallback_async_firms.append(firm_data)

            elif result:
                all_jobs.extend(result)
            
    final_async_firms = initial_async_firms + fallback_async_firms
    
    print(f"\nScheduling asynchronous Playwright scrapers ({len(initial_async_firms)} initial, {len(fallback_async_firms)} fallbacks)...")
    
    if final_async_firms:
        try:
            async_results = await scrape_playwright_firms_async(final_async_firms)
            all_jobs.extend(async_results)
        except Exception as e:
            logging.error(f"Critical failure in Playwright main task: {e}")
            
    total_jobs_found = len(all_jobs)
    
    return all_jobs, total_jobs_found

def export_to_excel(jobs_data, filename="output/jobs.xlsx"):
    if not jobs_data:
        print("No data to export to Excel.")
        return
        
    df = pd.DataFrame(jobs_data)
    if 'location' in df.columns:
        df = df.drop(columns=['location'])
        
    df = df.sort_values(by=['firm', 'title']).reset_index(drop=True)
    df.to_excel(filename, index=False)
    print(f"\nSuccessfully exported {len(df)} jobs to {filename}")

if __name__ == "__main__": 
    
    async def main():
        firms_to_scrape = get_firm_list()
        
        if not firms_to_scrape:
            print("No firms to scrape. Exiting.")
        else:
            all_jobs, total_found = await run_scrapers_async(firms_to_scrape)
            
            if all_jobs:
                print(f"\nScraping finished. Found a total of {total_found} jobs.")
                export_to_excel(all_jobs)
            else:
                print("\nScraping finished with no results.")

    asyncio.run(main())