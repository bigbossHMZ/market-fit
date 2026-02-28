import os
import logging
from dotenv import load_dotenv
from backend.clients.spapi.config import load_spapi_config

def configure_logging() -> logging.Logger:
    level_name = os.getenv("LOG_LEVEL", "INFO").upper()
    level = getattr(logging, level_name, logging.INFO)
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    # for noisy_lib in ("boto3","botocore", "urllib3"):
    #     logging.getLogger(noisy_lib).setLevel(logging.WARNING)

    return logging.getLogger(__name__)

def main():
    load_dotenv()

    logger = configure_logging()

    try:
        sp_api_config = load_spapi_config()
        logger.debug(f"SPAPI config loaded: {sp_api_config}")
    except ValueError as e:
        logger.error(f"Error loading SPAPI config: {e}")
        logger.info("Aborting... Please set the required environment variables and try again.")
        return





if __name__ == "__main__":
    main()
