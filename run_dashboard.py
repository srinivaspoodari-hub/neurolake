#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
NeuroLake Unified Dashboard Launcher
====================================

This script starts the NeuroLake unified dashboard with all features integrated:
- SQL Query Editor
- Data Explorer
- Metadata Browser
- Query History
- NCF Management
- System Monitoring
- Logging
- AI Insights

Usage:
    python run_dashboard.py
    python run_dashboard.py --port 8080 --host 0.0.0.0
    python run_dashboard.py --dev  # Development mode with auto-reload
"""

import argparse
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from neurolake.dashboard import create_dashboard_app

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description='NeuroLake Unified Dashboard',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python run_dashboard.py                    # Run on localhost:8080
  python run_dashboard.py --port 3000        # Custom port
  python run_dashboard.py --host 0.0.0.0     # Listen on all interfaces
  python run_dashboard.py --dev              # Development mode with auto-reload
        """
    )

    parser.add_argument(
        '--host',
        type=str,
        default='0.0.0.0',
        help='Host to bind to (default: 0.0.0.0)'
    )

    parser.add_argument(
        '--port',
        type=int,
        default=8080,
        help='Port to bind to (default: 8080)'
    )

    parser.add_argument(
        '--dev',
        '--reload',
        action='store_true',
        help='Enable development mode with auto-reload'
    )

    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )

    args = parser.parse_args()

    # Set logging level
    logging.getLogger().setLevel(args.log_level)

    # Print banner
    print("""
    ============================================================

         _   _                      _           _
        | \\ | | ___ _   _ _ __ ___ | |    __ _| | _____
        |  \\| |/ _ \\ | | | '__/ _ \\| |   / _` | |/ / _ \\
        | |\\  |  __/ |_| | | | (_) | |__| (_| |   <  __/
        |_| \\_|\\___|\\__,_|_|  \\___/|_____\\__,_|_|\\_\\___|

               AI-Native Data Platform
              Unified Dashboard v0.1.0

    ============================================================
    """)

    logger.info("=" * 60)
    logger.info("Starting NeuroLake Unified Dashboard")
    logger.info("=" * 60)
    logger.info(f"Host: {args.host}")
    logger.info(f"Port: {args.port}")
    logger.info(f"Development Mode: {args.dev}")
    logger.info(f"Log Level: {args.log_level}")
    logger.info("=" * 60)
    logger.info(f"\n>> Dashboard URL: http://{args.host}:{args.port}")
    logger.info(f">> API Docs: http://{args.host}:{args.port}/docs")
    logger.info(f">> Health Check: http://{args.host}:{args.port}/health")
    logger.info("=" * 60)
    logger.info("\n>> Features Available:")
    logger.info("  * SQL Query Editor with Monaco")
    logger.info("  * Data Explorer and Metadata Browser")
    logger.info("  * Query History and Analytics")
    logger.info("  * NCF Format Management")
    logger.info("  * Real-time System Monitoring")
    logger.info("  * Centralized Logging")
    logger.info("  * AI-Powered Query Optimization")
    logger.info("=" * 60)

    try:
        import uvicorn

        app = create_dashboard_app()

        uvicorn.run(
            app,
            host=args.host,
            port=args.port,
            reload=args.dev,
            log_level=args.log_level.lower(),
        )

    except KeyboardInterrupt:
        logger.info("\n\nShutting down NeuroLake Dashboard...")
        logger.info("Goodbye!")

    except Exception as e:
        logger.error(f"Failed to start dashboard: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
