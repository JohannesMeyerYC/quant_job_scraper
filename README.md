# 🤖 Configurable Quantitative Job Market Scraper

This project is an advanced, configuration-driven web scraping tool designed to efficiently aggregate open job listings from the career pages of various high-frequency trading firms, quantitative funds, leading banks, and fintech companies. It uses a mixed synchronous/asynchronous architecture for speed, robustness, and responsible resource management.

***

## 🎯 Purpose and Mission

The primary goal of this tool is to provide **market transparency** and **data centralization** for individuals navigating the competitive financial and deep-tech job markets.

- **For Job Seekers:** It eliminates the manual, repetitive process of checking hundreds of career sites. Candidates receive a single, aggregated, and professionally formatted Excel file (`output/jobs.xlsx`) for rapid analysis, comparison, and strategic application planning.
- **For Market Analysts:** The tool provides a clean snapshot of current hiring activity, allowing for the tracking of industry growth trends, regional demands, and specific role needs (e.g., Quant Researcher, Core Developer, Strategist).
- **Architectural Value:** The design showcases best practices for dealing with complex web environments, prioritizing maintainability and responsible resource management through a robust, configuration-driven approach.

***

## 🛠️ Architecture and Technology Stack

The scraper employs a layered approach to maximize success rates and resource efficiency:

| Platform Type | Technology Used | Execution | Description |
| :--- | :--- | :--- | :--- |
| **`greenhouse`** | `requests` & `BeautifulSoup` | Synchronous (`asyncio.to_thread`) | Handles sites using the standard Greenhouse job board structure via direct HTTP requests for maximum speed. |
| **`custom_site`** | `requests` & `BeautifulSoup` | Synchronous (`asyncio.to_thread`) | A generic, simple scraper for basic custom HTML pages. Efficient but prone to failure on complex sites. |
| **`playwright`** | Playwright (Headless Browser) | Asynchronous | Uses a headless browser to render JavaScript, fetch dynamic content, and simulate user interactions, guaranteeing extraction from complex pages. |
| **Fallback System** | Logic in `main.py` | Mixed | Sites designated as `custom_site` that return **zero results** from the fast `requests` scraper are automatically added to the slower, more robust `playwright` queue for a second attempt. |

***

## ⚙️ Configuration

All firms and site-specific scraping rules are managed through two central files.

### 1. `firms.csv` (The Target List)

This file defines *which* firms to scrape and *how* to approach them. The scraper expects the file to be a comma-separated list with the following strict headers:

| Header | Description | Example Value |
| :--- | :--- | :--- |
| `firm_name` | The unique name of the firm. | `Two Sigma` |
| `url` | The direct URL of the job listing page. | `https://www.twosigma.com/careers/open-roles` |
| `platform_type` | Defines the scraping strategy. Must be `greenhouse_standard`, `custom_site`, or `playwright`. | `playwright` |

### 2. `job_scraper/config.py` (The Rules)

This file holds global settings and all firm-specific CSS selectors required for the Playwright scraper.

- **`HEADERS` & `USER_AGENT_LIST`:** Includes rotating User-Agents to mimic natural browser behavior and enhance anti-detection resilience.
- **`PLAYWRIGHT_CONFIGS`:** A dictionary where the key is the `firm_name` (must match the CSV) and the value contains:
    - `url`: The URL (overrides CSV if needed, but should match for clarity).
    - `job_card_selector`: CSS selector for the main job listing container.
    - `title_selector`: CSS selector for the job title *within* the job card.
    - `location_selector`: CSS selector for the job location *within* the job card.
    - `requires_interaction`: Boolean flag to indicate if scrolling or clicking is necessary to load all jobs.

***

## 🚀 Quick Start Guide

### Prerequisites

You need **Python 3.8+** installed.

```bash
# Clone the repository
git clone [https://github.com/JohannesMeyerYC/quant_job_scraper.git](https://github.com/JohannesMeyerYC/quant_job_scraper.git)
cd quant_job_scraper

# Set up the environment
python -m venv venv
source venv/bin/activate    # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browser drivers (required for the 'playwright' strategy)
playwright install

# Running the Scraper

Ensure your `firms.csv` file is configured correctly, then execute the main script:

```bash
python main.py

# Output

The final, cleaned, and styled output is generated in Excel format:

`output/jobs.xlsx`

The file includes columns for **Firm**, **Job Title**, **Location**, and **Link**, sorted by firm for easy review.

---

# 🛡️ Robustness and Error Handling

The system is designed to handle errors gracefully and non-critically, ensuring the entire job list is scraped even if individual sites fail:

- **File Loading**  
  `get_firm_list` handles `FileNotFoundError`, `UnicodeDecodeError`, and CSV format errors (missing columns) without crashing, returning an empty list instead.

- **Requests Scrapers**  
  All synchronous scraping attempts are wrapped with `asyncio.to_thread` and executed with  
  `asyncio.gather(..., return_exceptions=True)`. Any HTTP or parsing error results in a log message (`logging.error`) but does not halt the process.

- **Playwright Scrapers**  
  The Playwright module manages browser errors internally. Any critical failure in the main Playwright task is caught and logged in `run_scrapers_async`.

- **Export**  
  `export_to_excel` validates the input, creates the output directory if needed, and uses `try...except` blocks to handle potential Pandas or Excel writing issues, logging a critical error if export fails.

- **Graceful Exit**  
  The main function includes a `KeyboardInterrupt` handler, allowing the user to safely stop the process with **Ctrl+C**.
