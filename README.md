# Configurable Job Market Scraper

This project is an advanced, configurable web scraping tool designed to efficiently aggregate open job listings from the career pages of various high-frequency trading firms, quantitative funds, leading banks, and fintech companies. It leverages a mixed synchronous and asynchronous architecture to ensure both speed and robustness against different website technologies.

---

## Purpose and Impact

The primary goal of this tool is to provide market transparency and data centralization for individuals tracking the job market in competitive financial and tech sectors.

**For Job Seekers:** It eliminates the manual, repetitive process of checking multiple career sites. Candidates get a single, aggregated, and structured Excel file for analysis, comparison, and strategic application planning.  

**For Market Analysts:** The tool provides a snapshot of hiring activity, allowing for the tracking of growth trends and specific role demands across the industry.  

**Architectural Value:** The design showcases best practices for dealing with complex web environments, prioritizing maintainability and responsible resource management through a configuration-driven approach.

---

## Architecture and Technology

The scraper employs a layered approach to maximize success rates and resource efficiency:

| Platform Type | Technology Used | Description |
|---------------|-----------------|-------------|
| **Simple Sites** (Greenhouse, basic HTML) | `requests` and `BeautifulSoup` (`asyncio.to_thread`) | Handles sites with static or easily parsed HTML. Runs synchronously in a separate thread to prevent blocking the main event loop. |
| **Complex Sites** (Modern UI, JavaScript-heavy) | Playwright (Asynchronous) | Uses a headless browser to render JavaScript, fetch dynamic content, and simulate user interactions, ensuring accurate data extraction from complex pages. |
| **Fallback Mechanism** | Logic within `run_scrapers_async` | Sites that fail the simple scrape (due to errors or zero results) are automatically retried using the more robust, but resource-intensive, Playwright scraper. |

---

## Quick Start Guide

### Prerequisites

You need **Python 3.8+** installed.

```bash
# Clone the repository
git clone https://github.com/JohannesMeyerYC/quant_job_scraper.git
cd quant_job_scraper

# Set up the environment
python -m venv venv
source venv/bin/activate   # On Windows: .\venv\Scripts\activate
pip install -r requirements.txt

# Install Playwright browser drivers
playwright install

# Running the Scraper
python main.py

# The results will be compiled into an Excel file:
output/jobs.xlsx
