"""Command-line interface for Sequel."""

import argparse
import sys

from sequel import __version__
from sequel.app import run_app
from sequel.config import get_config
from sequel.utils.logging import setup_logging


def main() -> None:
    """Main CLI entry point for Sequel."""
    parser = argparse.ArgumentParser(
        description="Sequel - A TUI for browsing Google Cloud resources",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  sequel                    # Start with default settings
  sequel --debug            # Enable debug logging
  sequel --no-cache         # Disable caching
  sequel --log-file app.log # Write logs to file

For more information, visit: https://github.com/dan-elliott-appneta/sequel
        """,
    )

    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug logging",
    )

    parser.add_argument(
        "--log-file",
        type=str,
        help="Path to log file (default: ~/.config/sequel/sequel.log)",
    )

    parser.add_argument(
        "--no-cache",
        action="store_true",
        help="Disable caching of API responses",
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    args = parser.parse_args()

    # Set up logging
    log_level = "DEBUG" if args.debug else get_config().log_level
    log_file = args.log_file if args.log_file else get_config().log_file
    setup_logging(level=log_level, log_file=log_file)

    # Update config based on CLI args
    if args.no_cache:
        config = get_config()
        config.cache_ttl_projects = 0
        config.cache_ttl_resources = 0

    try:
        # Run the application
        run_app()

    except KeyboardInterrupt:
        print("\nShutting down...")
        sys.exit(0)

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
