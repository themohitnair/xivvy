import os
from config import KAGGLE_DATASET_NAME, LOG_CONFIG, KAGGLE_CONFIG_DIR
import logging.config
import requests.exceptions

os.environ["KAGGLE_CONFIG_DIR"] = KAGGLE_CONFIG_DIR

from kaggle.api.kaggle_api_extended import KaggleApi

logging.config.dictConfig(LOG_CONFIG)


class DatasetDownloader:
    def __init__(self):
        self.api = KaggleApi()
        self.dataset_name = KAGGLE_DATASET_NAME
        self.logger = logging.getLogger(__name__)

        try:
            self.api.authenticate()
        except Exception as e:
            self.logger.error(
                f"An error ocurred while authenticating using Kaggle Credentials: {e}"
            )

    def download(self):
        try:
            self.logger.info("Starting dataset download...")
            self.api.dataset_download_files(self.dataset_name, path="data", unzip=True)
        except requests.exceptions.RequestException as e:
            self.logger.exception(f"Network/API error occurred: {e}")
        except PermissionError as e:
            self.logger.exception(f"Permission denied for directory access: {e}")
        except FileNotFoundError as e:
            self.logger.exception(f"Directory path not found: {e}")
        except ValueError as e:
            self.logger.exception(f"Invalid dataset parameters: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during download: {e}")
        finally:
            self.logger.info("Dataset downloaded successfully!")
