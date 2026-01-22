# 🔬 Source Mention Research

Research tool analyzing the correlation between brand mentions in AI query sources (citations) and whether the brand appears in the AI response.

## Key Finding
**When brand IS mentioned in the AI response, ~2.9x more sources cite the brand** (8.7 vs 3.0 on average)

## Setup

1. Copy `.env.example` to `.env` and add your API key:
   ```bash
   cp .env.example .env
   ```

2. Install dependencies:
   ```bash
   pip install python-dotenv
   ```

3. Run the server:
   ```bash
   python3 server.py
   ```

4. Open http://localhost:8001 in your browser

## Features

- **Distribution Charts**: View data as % Scatter, # Count Scatter, or Bar Chart
- **Customer Lookup**: Enter a customer ID to analyze their latest execution
- **Execution Drill-down**: Click on executions to see individual query results
- **Raw Data Table**: Search and filter all records with source details

## Files

- `visualization.html` - Interactive web dashboard
- `server.py` - Local HTTP server with API proxy
- `fetch_correlation_data.py` - Python script to fetch/export data
- `output/` - Exported data files (JSON, CSV)

## Data Explanation

The default view shows the **last 10,000 query executions** (ordered by ID descending), filtering out any records without sources.

Metrics tracked:
- **Brand in Response**: Was the customer's brand mentioned in the AI answer?
- **Sources with Brand**: How many source citations mention the brand?
- **Brand Mention %**: Percentage of sources that mention the brand
