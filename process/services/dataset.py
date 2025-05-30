import os
import time
import logging.config
import json
from datetime import datetime, timedelta
import requests.exceptions

from config import (
    KAGGLE_DATASET_NAME,
    LOG_CONFIG,
    KAGGLE_CONFIG_DIR,
    LAST_DOWNLOAD_FILE,
)

os.environ["KAGGLE_CONFIG_DIR"] = KAGGLE_CONFIG_DIR

from kaggle.api.kaggle_api_extended import KaggleApi

logging.config.dictConfig(LOG_CONFIG)


# 2720631 paper records


# ['acc-phys', 'adap-org', 'alg-geom', 'ao-sci', 'astro-ph', 'astro-ph.CO', 'astro-ph.EP', 'astro-ph.GA', 'astro-ph.HE', 'astro-ph.IM', 'astro-ph.SR', 'atom-ph', 'bayes-an', 'chao-dyn', 'chem-ph', 'cmp-lg', 'comp-gas', 'cond-mat', 'cond-mat.dis-nn', 'cond-mat.mes-hall', 'cond-mat.mtrl-sci', 'cond-mat.other', 'cond-mat.quant-gas', 'cond-mat.soft', 'cond-mat.stat-mech', 'cond-mat.str-el', 'cond-mat.supr-con', 'cs.AI', 'cs.AR', 'cs.CC', 'cs.CE', 'cs.CG', 'cs.CL', 'cs.CR', 'cs.CV', 'cs.CY', 'cs.DB', 'cs.DC', 'cs.DL', 'cs.DM', 'cs.DS', 'cs.ET', 'cs.FL', 'cs.GL', 'cs.GR', 'cs.GT', 'cs.HC', 'cs.IR', 'cs.IT', 'cs.LG', 'cs.LO', 'cs.MA', 'cs.MM', 'cs.MS', 'cs.NA', 'cs.NE', 'cs.NI', 'cs.OH', 'cs.OS', 'cs.PF', 'cs.PL', 'cs.RO', 'cs.SC', 'cs.SD', 'cs.SE', 'cs.SI', 'cs.SY', 'dg-ga', 'econ.EM', 'econ.GN', 'econ.TH', 'eess.AS', 'eess.IV', 'eess.SP', 'eess.SY', 'funct-an', 'gr-qc', 'hep-ex', 'hep-lat', 'hep-ph', 'hep-th', 'math-ph', 'math.AC', 'math.AG', 'math.AP', 'math.AT', 'math.CA', 'math.CO', 'math.CT', 'math.CV', 'math.DG', 'math.DS', 'math.FA', 'math.GM', 'math.GN', 'math.GR', 'math.GT', 'math.HO', 'math.IT', 'math.KT', 'math.LO', 'math.MG', 'math.MP', 'math.NA', 'math.NT', 'math.OA', 'math.OC', 'math.PR', 'math.QA', 'math.RA', 'math.RT', 'math.SG', 'math.SP', 'math.ST', 'mtrl-th', 'nlin.AO', 'nlin.CD', 'nlin.CG', 'nlin.PS', 'nlin.SI', 'nucl-ex', 'nucl-th', 'patt-sol', 'physics.acc-ph', 'physics.ao-ph', 'physics.app-ph', 'physics.atm-clus', 'physics.atom-ph', 'physics.bio-ph', 'physics.chem-ph', 'physics.class-ph', 'physics.comp-ph', 'physics.data-an', 'physics.ed-ph', 'physics.flu-dyn', 'physics.gen-ph', 'physics.geo-ph', 'physics.hist-ph', 'physics.ins-det', 'physics.med-ph', 'physics.optics', 'physics.plasm-ph', 'physics.pop-ph', 'physics.soc-ph', 'physics.space-ph', 'plasm-ph', 'q-alg', 'q-bio', 'q-bio.BM', 'q-bio.CB', 'q-bio.GN', 'q-bio.MN', 'q-bio.NC', 'q-bio.OT', 'q-bio.PE', 'q-bio.QM', 'q-bio.SC', 'q-bio.TO', 'q-fin.CP', 'q-fin.EC', 'q-fin.GN', 'q-fin.MF', 'q-fin.PM', 'q-fin.PR', 'q-fin.RM', 'q-fin.ST', 'q-fin.TR', 'quant-ph', 'solv-int', 'stat.AP', 'stat.CO', 'stat.ME', 'stat.ML', 'stat.OT', 'stat.TH', 'supr-con'] - 176 categories


class DatasetDownloader:
    def __init__(self):
        self.api = KaggleApi()
        self.dataset_name = KAGGLE_DATASET_NAME
        self.logger = logging.getLogger(__name__)
        self.timestamp_file = LAST_DOWNLOAD_FILE
        try:
            self.api.authenticate()
            self.logger.info("Authenticated successfully.")
        except Exception as e:
            self.logger.error(
                f"An error occurred while authenticating using Kaggle Credentials: {e}"
            )

    def _save_download_time(self):
        timestamp = datetime.utcnow().isoformat()
        with open(self.timestamp_file, "w") as f:
            json.dump({"last_download": timestamp}, f)
        self.logger.info(f"Saved last download timestamp: {timestamp}")

    def _is_download_needed(self):
        if not os.path.exists(self.timestamp_file):
            self.logger.info(
                "No previous download timestamp found. Proceeding to download."
            )
            return True

        with open(self.timestamp_file, "r") as f:
            data = json.load(f)
            last_download_str = data.get("last_download")

        try:
            last_download_time = datetime.fromisoformat(last_download_str)
        except (TypeError, ValueError):
            self.logger.warning("Corrupted timestamp file. Proceeding to download.")
            return True

        if datetime.utcnow() - last_download_time > timedelta(days=7):
            self.logger.info(
                "Last download was over 7 days ago. Proceeding to download."
            )
            return True
        else:
            self.logger.info("Dataset is up-to-date. No download needed.")
            return False

    def download(self):
        start = time.perf_counter()
        self.logger.info("Starting dataset download...")

        if not os.path.exists("data"):
            self.logger.info("Creating data directory...")
            os.makedirs("data")
            self.logger.info("Data directory created successfully.")

        try:
            self.api.dataset_download_files(self.dataset_name, path="data", unzip=True)
            elapsed = time.perf_counter() - start
            self.logger.info(f"Dataset download complete. Time taken: {elapsed:.2f}s")
            self._save_download_time()
        except requests.exceptions.RequestException as e:
            self.logger.exception(f"Network/API error occurred: {e}")
        except PermissionError as e:
            self.logger.exception(f"Permission denied for directory access: {e}")
        except FileNotFoundError as e:
            self.logger.exception(f"Directory path not found: {e}")
        except Exception as e:
            self.logger.exception(f"Unexpected error during download: {e}")

    def run(self):
        total_start_time = time.perf_counter()

        if self._is_download_needed():
            json_file_path = os.path.join("data", "arxiv-metadata-oai-snapshot.json")
            if os.path.exists(json_file_path):
                self.logger.info(f"Removing previous {json_file_path}...")
                os.remove(json_file_path)
                self.logger.info(f"Previous {json_file_path} removed successfully.")
            else:
                self.logger.info(f"No previous {json_file_path} found.")

            self.download()
        else:
            self.logger.info("Skipping download process.")

        total_elapsed_time = time.perf_counter() - total_start_time
        self.logger.info(
            f"\nTotal operation completed in {total_elapsed_time:.2f} seconds."
        )
