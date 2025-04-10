import os
from kaggle.api.kaggle_api_extended import KaggleApi


class Benjamin:  # Levy "GothamChess" Rozman's pet dog
    def __init__(self):
        self.client = KaggleApi()
        self.dataset_name = "cornell-university/arxiv"

        os.environ["KAGGLE_CONFIG_DIR"] = os.path.abspath("./kaggle")
        os.makedirs("data", exist_ok=True)

    def download(self):
        self.client.dataset_download_files(self.dataset_name, path="data", unzip=True)
