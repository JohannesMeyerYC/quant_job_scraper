import asyncio
import logging
from typing import List, Dict, Any, Optional

from config import PLAYWRIGHT_CONFIGS
from scrapers.requests_scraper import scrape_greenhouse_standard, scrape_custom_site_generic
from scrapers.playwright_scraper import run_playwright_scrapers
from utils.file_handler import get_firm_list, export_to_excel

BOLD = '\033[1m'
GREEN = '\033[92m'
BLUE = '\033[94m'
YELLOW = '\033[93m'
CYAN = '\033[96m'
RED = '\033[91m'
ENDC = '\033[0m'

logging.basicConfig(level=logging.INFO, format=f'{YELLOW}[%(levelname)s]{ENDC} %(message)s')

JobData = Dict[str, str]
FirmConfig = Dict[str, str]

async def run_scrapers(firm_list: List[FirmConfig], use_playwright: bool) -> List[JobData]:
    all_jobs: List[JobData] = []

    sync_tasks: List[asyncio.Future] = []
    sync_firm_map: Dict[int, FirmConfig] = {}
    initial_async_firms: List[Dict[str, str]] = []

    for i, firm_data in enumerate(firm_list):
        try:
            firm_name = firm_data['firm']
            url = firm_data['url']
            platform_type = firm_data['type']
        except KeyError as e:
            logging.error(f"Configuration error in firm list entry {i}: Missing key {e}. Skipping entry.")
            continue

        playwright_data = {'firm': firm_name}

        if platform_type == 'greenhouse':
            task = asyncio.to_thread(scrape_greenhouse_standard, firm_name, url)
            sync_tasks.append(task)
            sync_firm_map[len(sync_tasks) - 1] = firm_data
        elif platform_type == 'custom_site':
            task = asyncio.to_thread(scrape_custom_site_generic, firm_name, url)
            sync_tasks.append(task)
            sync_firm_map[len(sync_tasks) - 1] = firm_data
        elif platform_type == 'playwright':
            if use_playwright:
                if firm_name in PLAYWRIGHT_CONFIGS:
                    initial_async_firms.append(playwright_data)
                else:
                    logging.warning(f"-> Skipping {firm_name}: Playwright requested but config missing in PLAYWRIGHT_CONFIGS.")
            else:
                logging.info(f"-> Skipping {firm_name}: Playwright requested but user chose HTML-only mode.")
        else:
            logging.warning(f"-> Skipping {firm_name}: Unknown platform_type '{platform_type}'.")

    logging.info(f"\n{BOLD}SCHEDULE:{ENDC} Scheduling {len(sync_tasks)} synchronous scrapers (Greenhouse/Generic)...")
    fallback_async_firms: List[Dict[str, str]] = []

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
                    if use_playwright and not result and firm_data['type'] == 'custom_site' and firm_name in PLAYWRIGHT_CONFIGS:
                        logging.info(f"{YELLOW}FALLBACK:{ENDC} Triggering Playwright for {firm_name} (Generic scraper found 0 jobs).")
                        fallback_async_firms.append({'firm': firm_name})
                    elif result:
                        all_jobs.extend(result)
                else:
                    logging.error(f"Unexpected result type for {firm_name}: {type(result)}. Skipping.")
        except Exception as e:
             logging.error(f"Critical error during synchronous task gathering: {e}")

    if use_playwright:
        de_duplicated_initial_firms = list({firm['firm']: firm for firm in initial_async_firms}.values())

        final_async_firms_dict = {firm['firm']: firm for firm in de_duplicated_initial_firms + fallback_async_firms}

        final_async_firms = list(final_async_firms_dict.values())


        if final_async_firms:
            logging.info(f"\n{BOLD}SCHEDULE:{ENDC} Scheduling {len(final_async_firms)} Playwright scrapers ({len(de_duplicated_initial_firms)} initial, {len(fallback_async_firms)} fallbacks)...")
            try:
                async_results: List[JobData] = await run_playwright_scrapers(final_async_firms)
                all_jobs.extend(async_results)
            except Exception as e:
                logging.error(f"Critical failure during Playwright execution: {type(e).__name__} - {e}")
    else:
        logging.info("\n{BLUE}INFO:{ENDC} Skipping Playwright scraping as per user's request (HTML-only mode).")

    return all_jobs


async def main():
    print(f"\n{BOLD}{CYAN}╔═══════════════════════════════════════════╗{ENDC}")
    print(f"{CYAN}║{ENDC}      {BOLD}🚀 Job Scraper - Initialization{ENDC}      {CYAN}║{ENDC}")
    print(f"{CYAN}╚═══════════════════════════════════════════╝{ENDC}\n")

    try:
        firms_to_scrape = get_firm_list()
        total_firms = len(firms_to_scrape)
        print(f"{BLUE}✅ Configuration loaded!{ENDC} Found {BOLD}{total_firms}{ENDC} firms to check.")
    except Exception as e:
        print(f"{RED}❌ CRITICAL ERROR:{ENDC} Failed to load firm list. Cannot proceed.")
        logging.critical(f"Failed to load firm list: {e}. Cannot proceed.")
        return

    if not firms_to_scrape:
        print(f"{YELLOW}⚠️ WARNING:{ENDC} No valid firms to scrape. Exiting.")
        return

    use_playwright_mode = False
    print(f"\n{BOLD}--- MODE SELECTION ---{ENDC}")
    while True:
        choice = input(
            f"{BOLD}Choose a Scraping Mode:{ENDC}\n"
            f"  {BOLD}1. HTML-only{ENDC} (Fast, basic Request scrapers)\n"
            f"  {BOLD}{GREEN}2. Playwright-enabled (Recommended){ENDC} (Includes browser rendering for modern sites like Citadel/IMC)\n"
            f"{BOLD}Enter your choice (default is 2):{ENDC} "
        ).strip() or '2'

        if choice == '2':
            print(f"{CYAN}⚙️ MODE SET:{ENDC} Running in {BOLD}Playwright-enabled{ENDC} mode.")
            use_playwright_mode = True
            break
        elif choice == '1':
            print(f"{CYAN}⚙️ MODE SET:{ENDC} Running in {BOLD}HTML-only{ENDC} mode.")
            use_playwright_mode = False
            break
        else:
            print(f"{RED}🚫 Invalid choice.{ENDC} Please enter '1' for HTML-only or '2' for Playwright-enabled.")
            
    print(f"\n{BOLD}{CYAN}═" * 45 + ENDC)
    print(f"{BOLD}STARTING SCRAPING PROCESS...{ENDC}")
    print(f"{BOLD}{CYAN}═" * 45 + ENDC)

    try:
        all_jobs = await run_scrapers(firms_to_scrape, use_playwright_mode)
        
        print(f"\n{BOLD}{GREEN}╔═══════════════════════════════════════════╗{ENDC}")
        if all_jobs:
            job_count = len(all_jobs)
            print(f"{GREEN}║{ENDC}  {BOLD}🎉 Scraping Finished Successfully!{ENDC}  {GREEN}║{ENDC}")
            print(f"{GREEN}║{ENDC}  Total Jobs Found: {BOLD}{job_count:<20}{ENDC}{GREEN}║{ENDC}")
            print(f"{GREEN}║{ENDC}  Data Exported to: {BOLD}jobs_data.xlsx{ENDC}{GREEN}║{ENDC}")
            export_to_excel(all_jobs)
        else:
            print(f"{YELLOW}║{ENDC}  {BOLD}⚠️ Scraping Finished: No Jobs Found.{ENDC} {YELLOW}║{ENDC}")
        print(f"{BOLD}{GREEN}╚═══════════════════════════════════════════╝{ENDC}\n")


    except Exception as e:
        print(f"\n{RED}❌ CRITICAL FAILURE:{ENDC} A fatal error occurred during the main scraping run.")
        logging.critical(f"A fatal error occurred during the main scraping run: {e}")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n{YELLOW}⚠️ Interrupted by user (Ctrl+C). Exiting gracefully.{ENDC}")
    except Exception as e:
        print(f"\n{RED}❌ UNHANDLED FATAL ERROR:{ENDC} Check logs for details.")
        logging.critical(f"An unhandled fatal error occurred: {e}")