#!/usr/bin/env python3
"""
Research: Correlation between source mentions and query response mentions

This script pulls data from the queries_execution table to analyze:
- Whether there's a correlation between the number/percentage of sources (citations) 
  where the brand is mentioned and whether the brand was mentioned in the query response.

Data pulled:
- query execution response/answer (from logs)
- query execution sources/citations (resources field)
- is_mentioned in response (product_in_results field)
- is_mentioned in source/citation (parsed from resources)
"""

import json
import urllib.request
import os
import ssl
from datetime import datetime
from collections import defaultdict

# Try to load dotenv if available
try:
    from dotenv import load_dotenv
    # Load .env from parent directory (project root)
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))
except ImportError:
    pass

# Configuration - Call API directly with API key
API_BASE_URL = "https://chat-rank-api-dev.mindshare.so/tables"
API_KEY = os.getenv('API_KEY', '')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "output")

# Create SSL context that doesn't verify certificates (for dev)
ssl_context = ssl.create_default_context()
ssl_context.check_hostname = False
ssl_context.verify_mode = ssl.CERT_NONE

def api_call(endpoint, body, timeout=120):
    """Make API call to the backend directly"""
    url = f"{API_BASE_URL}/{endpoint}/"
    
    if not API_KEY:
        print("  ⚠ Warning: API_KEY not set. Please set it in .env file.")
        return None
    
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode(),
        headers={
            'Content-Type': 'application/json',
            'x-api-key': API_KEY
        },
        method='POST'
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout, context=ssl_context) as resp:
            result = json.loads(resp.read())
            return result.get('data', result)
    except urllib.error.HTTPError as e:
        print(f"  ⚠ HTTP Error {e.code}: {e.reason}")
        try:
            error_body = e.read().decode()
            print(f"  ⚠ Response: {error_body[:500]}")
        except:
            pass
        return None
    except Exception as e:
        print(f"  ⚠ API Error: {e}")
        return None


def parse_resources(resources_data):
    """
    Parse the resources field to extract source/citation information.
    Returns a list of resources with mention status.
    
    The resources field structure is:
    {"resources":[{"Domain":"...","url":"...","is_customer_mentioned":true/false},...]}`
    """
    if not resources_data:
        return []
    
    try:
        # If it's a string, try to parse as JSON
        if isinstance(resources_data, str):
            parsed = json.loads(resources_data)
        else:
            parsed = resources_data
        
        # Handle the nested structure: {"resources": [...]}
        if isinstance(parsed, dict):
            if 'resources' in parsed:
                return parsed['resources'] if isinstance(parsed['resources'], list) else []
            else:
                return [parsed]
        elif isinstance(parsed, list):
            return parsed
        else:
            return []
    except (json.JSONDecodeError, TypeError) as e:
        return []


def fetch_queries_execution_data(limit=10000, execution_id=None):
    """
    Fetch queries_execution data with relevant fields.
    Only returns records that have sources (resources field is not empty).
    """
    print(f"\n📡 Fetching queries_execution data (limit: {limit})...")
    
    body = {
        'tableName': 'queries_execution',
        'is_deleted': 0,
        'limit': limit,
        'orderBy': 'id',
        'order': 'desc'
    }
    
    if execution_id:
        body['execution_id'] = execution_id
    
    data = api_call('get-by', body)
    
    if data:
        print(f"  ✓ Fetched {len(data)} records from API")
        
        # Filter out records without sources
        records_with_sources = []
        for record in data:
            resources_raw = record.get('resources')
            if resources_raw:
                # Try to parse and check if there are actual resources
                parsed = parse_resources(resources_raw)
                if len(parsed) > 0:
                    records_with_sources.append(record)
        
        print(f"  ✓ Filtered to {len(records_with_sources)} records WITH sources (removed {len(data) - len(records_with_sources)} without sources)")
        return records_with_sources
    else:
        print("  ✗ Failed to fetch data")
        return []


def analyze_data(queries_execution_data):
    """
    Analyze the correlation between source mentions and response mentions.
    
    Returns a structured dataset for analysis and plotting.
    """
    results = []
    
    print(f"\n🔍 Analyzing {len(queries_execution_data)} query executions...")
    
    for idx, qe in enumerate(queries_execution_data):
        if idx % 100 == 0:
            print(f"  Processing {idx}/{len(queries_execution_data)}...")
        
        record = {
            'id': qe.get('id'),
            'query_id': qe.get('query_id'),
            'query_group_id': qe.get('query_group_id'),
            'execution_id': qe.get('execution_id'),
            'create_date': qe.get('create_date'),
            
            # Brand mentioned in response (main outcome variable)
            'product_in_results': qe.get('product_in_results', 0),
            'brand_in_response': bool(qe.get('product_in_results', 0)),
            
            # Resources/citations data
            'resources_raw': qe.get('resources'),
            'resources_log': qe.get('resources_log'),
            
            # Log files (paths to detailed data)
            'product_result_raw_log': qe.get('product_result_raw_log'),
            'competitors_log': qe.get('competitors_log'),
            'query_results_log': qe.get('query_results_log'),
            'bd_response_log': qe.get('bd_response_log'),
            'run_log': qe.get('run_log'),
            
            # Competitors data
            'competitors_raw': qe.get('competitors'),
        }
        
        # Parse resources to extract citation details
        resources = parse_resources(qe.get('resources'))
        record['resources_parsed'] = resources
        record['total_sources'] = len(resources)
        
        # Count sources where brand is mentioned
        # The key field is 'is_customer_mentioned' based on observed data structure
        sources_with_brand = 0
        sources_details = []
        
        for resource in resources:
            if isinstance(resource, dict):
                # Check for the 'is_customer_mentioned' field (the actual field name in the data)
                is_mentioned = bool(resource.get('is_customer_mentioned', False))
                
                if is_mentioned:
                    sources_with_brand += 1
                
                sources_details.append({
                    'url': resource.get('url', ''),
                    'domain': resource.get('Domain', ''),
                    'is_customer_mentioned': is_mentioned,
                })
        
        record['sources_with_brand'] = sources_with_brand
        record['sources_details'] = sources_details
        
        # Calculate percentage
        if record['total_sources'] > 0:
            record['brand_mention_percentage'] = (sources_with_brand / record['total_sources']) * 100
        else:
            record['brand_mention_percentage'] = 0
        
        results.append(record)
    
    print(f"  ✓ Analysis complete")
    return results


def generate_summary_stats(analyzed_data):
    """Generate summary statistics from the analyzed data.
    
    Note: All records in analyzed_data have sources (filtered upstream).
    """
    
    total = len(analyzed_data)
    with_response_mention = sum(1 for r in analyzed_data if r['brand_in_response'])
    
    # Group by whether brand was mentioned in response
    mentioned_group = [r for r in analyzed_data if r['brand_in_response']]
    not_mentioned_group = [r for r in analyzed_data if not r['brand_in_response']]
    
    summary = {
        'total_records': total,
        'records_with_brand_in_response': with_response_mention,
        'records_without_brand_in_response': total - with_response_mention,
        'note': 'All records have sources (records without sources were excluded)',
        
        # Average source counts
        'avg_sources_when_mentioned': 0,
        'avg_sources_when_not_mentioned': 0,
        'avg_brand_sources_when_mentioned': 0,
        'avg_brand_sources_when_not_mentioned': 0,
        'avg_brand_pct_when_mentioned': 0,
        'avg_brand_pct_when_not_mentioned': 0,
    }
    
    if mentioned_group:
        summary['avg_sources_when_mentioned'] = sum(r['total_sources'] for r in mentioned_group) / len(mentioned_group)
        summary['avg_brand_sources_when_mentioned'] = sum(r['sources_with_brand'] for r in mentioned_group) / len(mentioned_group)
        summary['avg_brand_pct_when_mentioned'] = sum(r['brand_mention_percentage'] for r in mentioned_group) / len(mentioned_group)
    
    if not_mentioned_group:
        summary['avg_sources_when_not_mentioned'] = sum(r['total_sources'] for r in not_mentioned_group) / len(not_mentioned_group)
        summary['avg_brand_sources_when_not_mentioned'] = sum(r['sources_with_brand'] for r in not_mentioned_group) / len(not_mentioned_group)
        summary['avg_brand_pct_when_not_mentioned'] = sum(r['brand_mention_percentage'] for r in not_mentioned_group) / len(not_mentioned_group)
    
    return summary


def print_sample_resources(analyzed_data, num_samples=5):
    """Print sample resources to understand the data structure."""
    
    print("\n📋 Sample resources data (to understand structure):")
    print("=" * 80)
    
    samples_shown = 0
    for record in analyzed_data:
        if record['resources_raw'] and samples_shown < num_samples:
            print(f"\n--- Record ID: {record['id']} ---")
            print(f"Brand in response: {record['brand_in_response']}")
            print(f"Total sources: {record['total_sources']}")
            print(f"Resources raw type: {type(record['resources_raw'])}")
            
            # Show raw resources (truncated)
            raw_str = str(record['resources_raw'])
            if len(raw_str) > 500:
                print(f"Resources raw (truncated): {raw_str[:500]}...")
            else:
                print(f"Resources raw: {raw_str}")
            
            samples_shown += 1
    
    if samples_shown == 0:
        print("No records with resources data found!")


def save_results(analyzed_data, summary):
    """Save results to files for further analysis."""
    
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    
    # Save full analyzed data
    full_data_path = os.path.join(OUTPUT_DIR, f"correlation_data_{timestamp}.json")
    with open(full_data_path, 'w') as f:
        # Create a serializable version (remove complex objects)
        serializable_data = []
        for record in analyzed_data:
            clean_record = {k: v for k, v in record.items() if k not in ['sources_details']}
            # Convert sources_details to simpler format
            clean_record['sources_summary'] = [
                {'url': s.get('url', ''), 'domain': s.get('domain', ''), 'is_customer_mentioned': s.get('is_customer_mentioned', False)} 
                for s in record.get('sources_details', [])
            ]
            serializable_data.append(clean_record)
        json.dump(serializable_data, f, indent=2, default=str)
    print(f"  ✓ Saved full data: {full_data_path}")
    
    # Save summary
    summary_path = os.path.join(OUTPUT_DIR, f"summary_{timestamp}.json")
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2)
    print(f"  ✓ Saved summary: {summary_path}")
    
    # Save CSV for easy plotting
    csv_path = os.path.join(OUTPUT_DIR, f"correlation_data_{timestamp}.csv")
    with open(csv_path, 'w') as f:
        # Header
        f.write("id,query_id,query_group_id,execution_id,brand_in_response,total_sources,sources_with_brand,brand_mention_percentage\n")
        # Data
        for record in analyzed_data:
            f.write(f"{record['id']},{record['query_id']},{record['query_group_id']},{record['execution_id']},{int(record['brand_in_response'])},{record['total_sources']},{record['sources_with_brand']},{record['brand_mention_percentage']:.2f}\n")
    print(f"  ✓ Saved CSV: {csv_path}")
    
    return full_data_path, summary_path, csv_path


def main():
    """Main execution function."""
    
    print("=" * 80)
    print("🔬 RESEARCH: Source Mentions vs Response Mentions Correlation")
    print("=" * 80)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    # Step 1: Fetch data
    queries_execution_data = fetch_queries_execution_data(limit=5000)
    
    if not queries_execution_data:
        print("\n❌ No data fetched. Make sure the server is running on http://localhost:8000")
        return
    
    # Step 2: Show sample resources to understand structure
    print_sample_resources([{'id': qe.get('id'), 'brand_in_response': qe.get('product_in_results'), 
                             'total_sources': 0, 'resources_raw': qe.get('resources')} 
                            for qe in queries_execution_data[:20]], num_samples=5)
    
    # Step 3: Analyze data
    analyzed_data = analyze_data(queries_execution_data)
    
    # Step 4: Generate summary statistics
    summary = generate_summary_stats(analyzed_data)
    
    # Step 5: Print summary
    print("\n" + "=" * 80)
    print("📊 SUMMARY STATISTICS (Only records WITH sources)")
    print("=" * 80)
    print(f"Total records analyzed: {summary['total_records']} (all have sources)")
    print(f"Records with brand in response: {summary['records_with_brand_in_response']} ({summary['records_with_brand_in_response']/summary['total_records']*100:.1f}%)")
    print(f"Records without brand in response: {summary['records_without_brand_in_response']} ({summary['records_without_brand_in_response']/summary['total_records']*100:.1f}%)")
    print()
    print("When brand IS mentioned in response:")
    print(f"  - Avg # of sources: {summary['avg_sources_when_mentioned']:.2f}")
    print(f"  - Avg # of sources with brand: {summary['avg_brand_sources_when_mentioned']:.2f}")
    print(f"  - Avg % of sources with brand: {summary['avg_brand_pct_when_mentioned']:.2f}%")
    print()
    print("When brand is NOT mentioned in response:")
    print(f"  - Avg # of sources: {summary['avg_sources_when_not_mentioned']:.2f}")
    print(f"  - Avg # of sources with brand: {summary['avg_brand_sources_when_not_mentioned']:.2f}")
    print(f"  - Avg % of sources with brand: {summary['avg_brand_pct_when_not_mentioned']:.2f}%")
    
    # Step 6: Save results
    print("\n💾 Saving results...")
    full_path, summary_path, csv_path = save_results(analyzed_data, summary)
    
    print("\n" + "=" * 80)
    print("✅ RESEARCH DATA COLLECTION COMPLETE")
    print("=" * 80)
    print(f"\nOutput files:")
    print(f"  - Full data: {full_path}")
    print(f"  - Summary: {summary_path}")
    print(f"  - CSV (for plotting): {csv_path}")
    print(f"\nFinished at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")


if __name__ == "__main__":
    main()
