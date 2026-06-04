"""
Main Application Entry Point
Uses the enhanced dashboard with Agent Thought Process Monitor and Interactive Charting
"""

import logging
from dashboard import render_dashboard

logger = logging.getLogger(__name__)

def main():
    """Main application entry point"""
    try:
        render_dashboard()
    except Exception as e:
        logger.error(f"Error running dashboard: {e}")
        raise

if __name__ == "__main__":
    main()