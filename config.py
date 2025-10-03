import random

USER_AGENT_LIST = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15',
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:109.0) Gecko/20100101 Firefox/119.0',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Windows NT 10.0; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    'Mozilla/5.0 (Linux; Android 14) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.6099.144 Mobile Safari/537.36'
]

def get_random_headers():
    return {
        'User-Agent': random.choice(USER_AGENT_LIST),
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.9',
        'Connection': 'keep-alive',
        'Cache-Control': 'no-cache',
        'Pragma': 'no-cache',
        'DNT': '1'
    }

REQUESTS_TIMEOUT = 20

REQUESTS_CONCURRENCY_DELAY = (1.0, 3.0)

PLAYWRIGHT_TASK_DELAY = (3.0, 7.0)

MAX_RETRIES = 3

PROXIES = {}


PLAYWRIGHT_CONFIGS = {
    "Jane Street": {
        "url": "https://www.janestreet.com/join-us/opportunities/all/",
        "job_card_selector": "li.opportunity-listing",
        "title_selector": "h3",
        "location_selector": "p.location",
        "requires_interaction": False 
    },
    "Jump Trading": {
        "url": "https://www.jumptrading.com/open-roles/",
        "job_card_selector": "div.role-card",
        "title_selector": "h2",
        "location_selector": "div.role-location",
        "requires_interaction": True 
    },
    "D.E. Shaw": {
        "url": "https://www.deshaw.com/careers/openings",
        "job_card_selector": "a.job-listing-item",
        "title_selector": "h2",
        "location_selector": "span.job-location",
        "requires_interaction": False
    },
    "IMC Trading": {
        "url": "https://careers.imc.com/global/en/job-search-results",
        "job_card_selector": "li.jobs-list-item",
        "title_selector": "h3",
        "location_selector": "span.job-location-text",
        "requires_interaction": False
    },
    "Citadel": {
        "url": "https://www.citadel.com/careers/open-opportunities/",
        "job_card_selector": "div[data-ph-id*='job-listing-item']", 
        "title_selector": "h2",
        "location_selector": "div:text('Location')",
        "requires_interaction": True
    },
    "Two Sigma": {
        "url": "https://www.twosigma.com/careers/open-roles/",
        "job_card_selector": "div.role-card-container", 
        "title_selector": "h3",
        "location_selector": "div.location-text",
        "requires_interaction": False
    },
    "Renaissance Technologies": {
        "url": "https://www.rentec.com/Careers.html",
        "job_card_selector": "a[href*='job-details']",
        "title_selector": "text", 
        "location_selector": None,
        "requires_interaction": False
    },
    "Optiver": {
        "url": "https://www.optiver.com/working-at-optiver/career-opportunities",
        "job_card_selector": "a[href*='/job/']",
        "title_selector": "h3",
        "location_selector": "span[data-label='location']",
        "requires_interaction": False
    },
    "Flow Traders": {
        "url": "https://www.flowtraders.com/careers/jobs",
        "job_card_selector": "a[href*='/vacancy/']",
        "title_selector": "h3",
        "location_selector": "div.location",
        "requires_interaction": True 
    },
    "WorldQuant": {
        "url": "https://www.worldquant.com/careers/open-roles",
        "job_card_selector": "a[href*='/job/']",
        "title_selector": "h2",
        "location_selector": "div.location-text",
        "requires_interaction": False
    },
    "Squarepoint Capital": {
        "url": "https://www.squarepoint-capital.com/careers",
        "job_card_selector": "a.job-listing",
        "title_selector": "h3",
        "location_selector": "span.location",
        "requires_interaction": False 
    },
    "Balyasny Asset Management": {
        "url": "https://www.bamfunds.com/careers/open-roles",
        "job_card_selector": "div.job-post",
        "title_selector": "h4",
        "location_selector": "span.location",
        "requires_interaction": True
    },
    "Point72": {
        "url": "https://www.point72.com/careers/all-jobs/",
        "job_card_selector": "a.role-item",
        "title_selector": "h3",
        "location_selector": "div.role-location",
        "requires_interaction": True
    },
    "Nvidia": {
        "url": "https://www.nvidia.com/en-us/careers/find-a-job/",
        "job_card_selector": "div.job-list-item",
        "title_selector": "h3",
        "location_selector": "span.job-location",
        "requires_interaction": True
    },
    "Coinbase": {
        "url": "https://www.coinbase.com/careers/open-roles",
        "job_card_selector": "a[href*='/careers/job/']",
        "title_selector": "h4",
        "location_selector": "div.location",
        "requires_interaction": True 
    }
}

GREENHOUSE_FIRMS = [
    "Stripe",
    "Gusto",
    "Robinhood",
    "Palantir",
    "Datadog",
    "Snowflake"
]

CUSTOM_SITE_FALLBACKS = [
    "Uber",
    "Airbnb",
    "Meta"
]