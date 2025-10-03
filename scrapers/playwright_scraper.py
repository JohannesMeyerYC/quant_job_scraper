import asyncio
from playwright.async_api import async_playwright, TimeoutError, Error as PlaywrightError
import logging
from typing import List, Dict, Any
import random
from urllib.parse import urljoin, urlparse

PLAYWRIGHT_CONFIGS = {}

JobData = Dict[str, str]

async def __create_browser_page(p, stealth_options=None):
    browser_type = random.choice([p.chromium, p.firefox])

    context = await browser_type.launch(
        headless=True,
        args=[
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-gpu',
            '--window-size=1920,1080',
            '--blink-settings=imagesEnabled=false'
        ]
    )

    page = await context.new_page()
    await page.set_viewport_size({"width": 1920, "height": 1080})

    return context, page

async def scrape_firm_playwright(
    firm_name: str,
    url: str,
    job_card_selector: str,
    title_selector: str,
    location_selector: str | None,
    p: Any
) -> List[JobData]:
    context = None
    scraped_jobs: List[JobData] = []
    is_fallback = firm_name not in PLAYWRIGHT_CONFIGS
    log_prefix = "FALLBACK" if is_fallback else "Playwright"
    logging.info(f"--- Starting concurrent scrape for {firm_name} (Type: {log_prefix}) ---")

    try:
        context, page = await __create_browser_page(p)

        await page.goto(url, wait_until="load", timeout=30000)
        await asyncio.sleep(random.uniform(2, 4))

        await page.wait_for_selector(job_card_selector, state="visible", timeout=10000)

        job_card_locators = await page.locator(job_card_selector).all()

        if not job_card_locators:
            logging.warning(f"No job cards found using selector '{job_card_selector}' for {firm_name}.")
            return []

        logging.info(f"Found {len(job_card_locators)} potential job listings for {firm_name}.")

        for i, card_locator in enumerate(job_card_locators):
            await asyncio.sleep(random.uniform(0.1, 0.5))
            try:
                title = await (card_locator.inner_text() if title_selector == "text" else card_locator.locator(title_selector).inner_text())

                job_url = None

                if await card_locator.evaluate("el => el.tagName === 'A'"):
                    job_url = await card_locator.get_attribute("href")

                if not job_url:
                    job_link = card_locator.locator("a").first
                    if job_link:
                        job_url = await job_link.get_attribute("href")

                if not job_url:
                    logging.warning(f"Job link missing for job card {i} on {firm_name}. Skipping.")
                    continue

                location = "N/A"
                if location_selector:
                    try:
                        location_element = card_locator.locator(location_selector).first
                        location = (await location_element.inner_text()).strip()
                    except PlaywrightError:
                        pass

                link = urljoin(url, job_url)

                title_clean = title.strip().replace('\n', ' ')

                if not (5 < len(title_clean) < 100 and urlparse(link).scheme in ('http', 'https')):
                    logging.debug(f"Skipping job on {firm_name} due to invalid title or link: {title_clean}")
                    continue

                scraped_jobs.append({
                    "firm": firm_name.capitalize(),
                    "title": title_clean,
                    "location": location.strip(),
                    "link": link
                })

            except Exception as e:
                logging.error(f"Error processing job card {i} for {firm_name}: {e}")
                continue

    except TimeoutError:
        logging.error(f"Timeout occurred while loading or waiting for elements on {firm_name} ({url}).")
    except PlaywrightError as e:
        if "net::ERR_ABORTED" in str(e):
             logging.error(f"Network error (e.g., failed to connect) on {firm_name} ({url}): {e}")
        else:
             logging.error(f"Playwright error during scrape of {firm_name}: {e}")
    except Exception as e:
        logging.error(f"An unexpected critical error occurred during scraping {firm_name}: {e}")

    finally:
        if context:
            await context.close()

    logging.info(f"--- Finished scrape for {firm_name} with {len(scraped_jobs)} jobs found ---")

    return scraped_jobs


async def run_playwright_scrapers(firms_to_run: List[Dict[str, Any]]) -> List[JobData]:
    all_results: List[JobData] = []

    if not firms_to_run:
        return all_results

    async with async_playwright() as p:
        tasks = []
        for firm_data in firms_to_run:
            firm_name = firm_data['firm']
            config = PLAYWRIGHT_CONFIGS.get(firm_name)

            if config:
                task = scrape_firm_playwright(
                    firm_name=firm_name,
                    url=config.get("url", firm_data.get("url")),
                    job_card_selector=config["job_card_selector"],
                    title_selector=config["title_selector"],
                    location_selector=config["location_selector"],
                    p=p
                )
                tasks.append(task)
            else:
                logging.warning(f"Error: Playwright firm '{firm_name}' had a configuration issue. Skipping.")

        logging.info(f"Running {len(tasks)} Playwright scraping tasks concurrently...")

        results = await asyncio.gather(*tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logging.error(f"A concurrent Playwright task failed with a critical error: {result}")
            elif isinstance(result, list):
                all_results.extend(result)

    return all_results