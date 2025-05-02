import os
from dotenv import load_dotenv
from chromadb.config import Settings

LOG_CONFIG = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "detailed": {
            "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
            "datefmt": "%Y-%m-%d %H:%M",
        },
        "simple": {"format": "[%(levelname)s] %(message)s"},
    },
    "handlers": {
        "console": {
            "class": "logging.StreamHandler",
            "level": "DEBUG",
            "formatter": "simple",
            "stream": "ext://sys.stdout",
        },
    },
    "root": {"level": "INFO", "handlers": ["console"]},
}

load_dotenv()

CHROMA_SERVER_SETTINGS = Settings(
    chroma_api_impl="chromadb.api.fastapi.FastAPI",
    chroma_server_host="localhost",
    chroma_server_http_port=6969,
    persist_directory="./chroma_data",
)
KAGGLE_DATASET_NAME = "Cornell-University/arxiv"
KAGGLE_CONFIG_DIR = "kaggle/"
CHROMA_PERSIST_DIR = "chroma_data/"
TGA_KEY = os.getenv("TOGETHERAI_API_KEY")
CHROMA_COLLECTION_NAME = "arxiv"
CHROMA_PORT = 6969
XIVVY_PORT = 8000
EMB_MODEL = "BAAI/bge-base-en-v1.5"
BATCH_SIZE = 128
DATASET_PATH = "data/arxiv-metadata-oai-test.json"
VALID_CATEGORIES = {
    "cs",
    "econ",
    "eess",
    "math",
    "astro-ph",
    "cond-mat",
    "gr-qc",
    "hep",
    "math-ph",
    "nucl",
    "quant-ph",
    "physics",
    "q-bio",
    "q-fin",
    "stat",
    "nlin",
}
