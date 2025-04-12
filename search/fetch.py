import os
from config import KAGGLE_DATASET_NAME, PROJECT_ROOT, LOG_CONFIG
import logging.config

os.environ["KAGGLE_CONFIG_DIR"] = str(PROJECT_ROOT / "kaggle")

from kaggle.api.kaggle_api_extended import KaggleApi

logging.config.dictConfig(LOG_CONFIG)


class Benjamin:  # Levy "GothamChess" Rozman's pet dog
    def __init__(self):
        print("KAGGLE_CONFIG_DIR:", os.getenv("KAGGLE_CONFIG_DIR"))
        self.client = KaggleApi()
        self.client.authenticate()
        self.dataset_name = KAGGLE_DATASET_NAME
        self.logger = logging.getLogger(__name__)

        os.makedirs("data", exist_ok=True)
        self.logger.info("data directory created.")

    def download(self):
        self.logger.info("Downloading arxiv dataset snapshot file from kaggle.")
        self.client.dataset_download_files(self.dataset_name, path="data", unzip=True)
        self.logger.info("Download finished.")
