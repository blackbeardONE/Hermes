from logger import logger
from csv_processing import process_all_csv_files

import sys

if __name__ == "__main__":
    logger.info("Starting CSV encoding conversion and translation process...")

    # Get folder path from command line argument or prompt user
    if len(sys.argv) > 1:
        folder_path = sys.argv[1]
        logger.info(f"Using folder path from command line argument: {folder_path}")
    else:
        folder_path = input("Enter the folder path to detect and process CSV files (default is current directory): ").strip()
        if not folder_path:
            folder_path = '.'
        logger.info(f"Using folder path from user input: {folder_path}")

    try:
        process_all_csv_files(root_dir=folder_path)
    except KeyboardInterrupt:
        logger.info("\nProcess interrupted by user. Exiting gracefully.")
        sys.exit(0)
