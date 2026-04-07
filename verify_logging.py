import logging
import sys
from snapshow.cli import setup_logging
from snapshow.utils import open_file_with_system_default

def main():
    # Setup logging to file snapshow.log, but without console output
    setup_logging(verbose=True, log_to_console=False)
    
    logger = logging.getLogger(__name__)
    logger.info("Starting manual fault injection test...")
    
    try:
        open_file_with_system_default("dummy.jpg")
    except Exception as e:
        logger.error(f"Unexpected exception outside: {e}", exc_info=True)
    
    logger.info("Manual fault injection test complete.")

if __name__ == "__main__":
    main()
