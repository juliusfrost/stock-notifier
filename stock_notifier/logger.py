import datetime
import logging
from pathlib import Path


def setup_logger():
    # Get the current date and time
    current_time = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")

    # Create a logger
    logger = logging.getLogger("stock-notifier")
    logger.setLevel(logging.DEBUG)

    # Create a formatter for the log messages
    formatter = logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")

    # Create a console handler and set the level to INFO
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)

    # Create a file handler with the current date and time in the file name
    log_dir = Path(__file__).parent.parent.joinpath("logs")
    log_dir.mkdir(exist_ok=True)
    log_file_path = log_dir.joinpath(f"{current_time}.log")
    file_handler = logging.FileHandler(log_file_path)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)

    return logger


logger = setup_logger()
