"""
Manual Report Generator

Run this script to generate a daily performance report for any specific date.
Useful for reviewing past trading days or generating missed reports.

Usage:
    python3 generate_report.py                    # Today's report
    python3 generate_report.py 2026-01-12         # Specific date
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from Src.reporting_engine import ReportingEngine
from datetime import datetime

if __name__ == "__main__":
    date_str = sys.argv[1] if len(sys.argv) > 1 else datetime.now().strftime('%Y-%m-%d')
    
    engine = ReportingEngine()
    report_path = engine.generate_daily_report(date_str)
    
    if report_path:
        print(f"✅ Report generated: {report_path}")
    else:
        print(f"❌ No data found for {date_str}")
