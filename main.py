import asyncio
import logging
from typing import List, Dict, Any, Optional

from config import PLAYWRIGHT_CONFIGS
from scrapers.requests_scraper import scrape_greenhouse_standard, scrape_custom_site_generic
from scrapers.playwright_scraper import run_playwright_scrapers
from utils.file_handler import get_firm_list, export_to_excel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

JobData = Dict[str, str]
FirmConfig = Dict[str, str]

async def run_scrapers(firm_list: List[FirmConfig]) -> List[JobData]:
    all_jobs: List[JobData] = []
    
    sync_tasks: List[asyncio.Future] = []
    sync_firm_map: Dict[int, FirmConfig] = {}
    initial_async_firms: List[FirmConfig] = []

    for i, firm_data in enumerate(firm_list):
        try:
            firm_name = firm_data['firm']
            url = firm_data['url']
            platform_type = firm_data['type']
        except KeyError as e:
            logging.error(f"Configuration error in firm list entry {i}: Missing key {e}. Skipping entry.")
            continue

        if platform_type == 'greenhouse':
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

    logging.info(f"\nScheduling {len(sync_tasks)} synchronous scrapers (Greenhouse/Generic)...")
    fallback_async_firms: List[FirmConfig] = []
    
    if sync_tasks:
        try:
            sync_results: List[Any] = await asyncio.gather(*sync_tasks, return_exceptions=True)
            
            for i, result in enumerate(sync_results):
                firm_data: Optional[FirmConfig] = sync_firm_map.get(i)
                if not firm_data:
                    logging.error(f"Logic error: Could not find firm data for task index {i}. Skipping result.")
                    continue
                
                firm_name = firm_data['firm']
                
                if isinstance(result, Exception):
                    logging.error(f"Error in requests scraper for {firm_name} ({firm_data['type']}): {type(result).__name__} - {result}")
                elif isinstance(result, list):
                    if not result and firm_data['type'] == 'custom_site' and firm_name in PLAYWRIGHT_CONFIGS:
                        logging.info(f"FALLBACK: Triggering Playwright for {firm_name} (Generic scraper found 0 jobs).")
                        fallback_async_firms.append(firm_data)
                    elif result:
                        all_jobs.extend(result)
                else:
                    logging.error(f"Unexpected result type for {firm_name}: {type(result)}. Skipping.")
        except Exception as e:
             logging.error(f"Critical error during synchronous task gathering: {e}")
             
    final_async_firms: List[FirmConfig] = initial_async_firms + fallback_async_firms
    
    if final_async_firms:
        logging.info(f"\nScheduling Playwright scrapers ({len(initial_async_firms)} initial, {len(fallback_async_firms)} fallbacks)...")
        try:
            async_results: List[JobData] = await run_playwright_scrapers(final_async_firms)
            all_jobs.extend(async_results)
        except Exception as e:
            logging.error(f"Critical failure during Playwright execution: {type(e).__name__} - {e}")
            
    return all_jobs

async def main():
    try:
        firms_to_scrape = get_firm_list()
    except Exception as e:
        logging.critical(f"Failed to load firm list: {e}. Cannot proceed.")
        return
    
    if not firms_to_scrape:
        logging.info("No valid firms to scrape. Exiting.")
        return
    
    try:
        all_jobs = await run_scrapers(firms_to_scrape)
        
        if all_jobs:
            logging.info(f"\nScraping finished. Found a total of {len(all_jobs)} unique jobs.")
            export_to_excel(all_jobs)
        else:
            logging.info("\nScraping finished with no results.")
            
    except Exception as e:
        logging.critical(f"A fatal error occurred during the main scraping run: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.warning("Scraping process interrupted by user (Ctrl+C). Exiting gracefully.")
    except Exception as e:
        logging.critical(f"An unhandled fatal error occurred: {e}")