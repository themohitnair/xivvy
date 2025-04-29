import os
from dotenv import load_dotenv

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

KAGGLE_DATASET_NAME = "Cornell-University/arxiv"
KAGGLE_CONFIG_DIR = "kaggle/"
OAI_KEY = os.getenv("OPENAI_API_KEY")
CHROMA_COLLECTION_NAME = "arxiv"
