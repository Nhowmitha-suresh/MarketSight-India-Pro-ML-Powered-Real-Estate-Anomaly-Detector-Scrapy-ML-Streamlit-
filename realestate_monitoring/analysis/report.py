"""
Report generation module for MarketSight
Generates summary reports after analysis runs
"""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


def generate_report(report_data: dict, zip_code: str, output_format: str = 'both') -> dict:
    """
    Generate post-run report in JSON and text formats.
    
    Args:
        report_data: Dictionary with keys: total_new_listings, dq_failures, ml_anomalies, etc.
        zip_code: Target ZIP code
        output_format: 'json', 'text', or 'both'
    
    Returns:
        Dictionary with 'json_path' and/or 'text_path'
    """
    
    timestamp = datetime.utcnow().strftime('%Y%m%d_%H%M%S')
    report_dir = Path('analysis/reports')
    report_dir.mkdir(parents=True, exist_ok=True)
    
    # JSON Report
    json_filename = f"report_{zip_code}_{timestamp}.json"
    json_path = report_dir / json_filename
    
    json_report = {
        'generated_at': datetime.utcnow().isoformat(),
        'zip_code': zip_code,
        'summary': report_data
    }
    
    if output_format in ['json', 'both']:
        with open(json_path, 'w') as f:
            json.dump(json_report, f, indent=2)
        logger.info(f"JSON report saved: {json_path}")
    
    # Text Report
    text_filename = f"report_{zip_code}_{timestamp}.txt"
    text_path = report_dir / text_filename
    
    text_content = f"""
================================================================================
                    MarketSight Pro - Analysis Report (v2.0)
================================================================================
Generated: {json_report['generated_at']}
ZIP Code: {zip_code}

PIPELINE EXECUTION SUMMARY
================================================================================
Total New Listings Processed:  {report_data.get('total_new_listings', 0)}
Data Quality Failures (DQ):    {report_data.get('dq_failures', 0)}
Listings Analyzed by ML:       {report_data.get('ml_anomalies', 0) + report_data.get('ml_opportunities', 0) + report_data.get('ml_risks', 0)}

ANOMALY DETECTION RESULTS (ML-Based)
================================================================================
Total Anomalies Detected:      {report_data.get('ml_anomalies', 0)}
  ✓ Investment Opportunities:  {report_data.get('ml_opportunities', 0)} (Under-Priced)
  ⚠ Market Risks:              {report_data.get('ml_risks', 0)} (Over-Priced)

DEVIATION THRESHOLD APPLIED:   ±15% from predicted price

RECOMMENDATIONS
================================================================================
• Review {report_data.get('ml_opportunities', 0)} under-priced opportunities in the Market
• Investigate {report_data.get('ml_risks', 0)} over-priced listings for market risk
• {report_data.get('dq_failures', 0)} listings rejected by data quality checks
• Use dashboard to filter and analyze anomalies interactively

NEXT STEPS
================================================================================
1. Log in to MarketSight Pro dashboard (Streamlit app)
2. Navigate to "Opportunities View" to see under-priced listings
3. Check "Market Risk View" for over-priced properties
4. Use scatter plot for visual anomaly analysis by locality

================================================================================
End of Report
================================================================================
"""
    
    if output_format in ['text', 'both']:
        with open(text_path, 'w') as f:
            f.write(text_content)
        logger.info(f"Text report saved: {text_path}")
    
    result = {}
    if output_format in ['json', 'both']:
        result['json_path'] = str(json_path)
    if output_format in ['text', 'both']:
        result['text_path'] = str(text_path)
    
    return result


def print_report(report_data: dict, zip_code: str):
    """Print report to console"""
    print(f"\n{'='*80}")
    print(" " * 20 + "MarketSight Pro - Analysis Report (v2.0)")
    print(f"{'='*80}")
    print(f"ZIP Code: {zip_code}")
    print(f"Generated: {datetime.utcnow().isoformat()}\n")
    
    print("📊 PIPELINE SUMMARY")
    print(f"  Total listings processed:    {report_data.get('total_new_listings', 0)}")
    print(f"  Data quality failures:       {report_data.get('dq_failures', 0)}")
    
    print("\n🚀 ML ANOMALY DETECTION")
    print(f"  Total anomalies:             {report_data.get('ml_anomalies', 0)}")
    print(f"  ✓ Opportunities (Under):     {report_data.get('ml_opportunities', 0)}")
    print(f"  ⚠️ Risks (Over):              {report_data.get('ml_risks', 0)}")
    
    print(f"\n{'='*80}\n")


if __name__ == '__main__':
    # Example usage
    sample_report = {
        'total_new_listings': 42,
        'dq_failures': 3,
        'ml_anomalies': 7,
        'ml_opportunities': 4,
        'ml_risks': 3
    }
    generate_report(sample_report, '12345', output_format='both')
    print_report(sample_report, '12345')
