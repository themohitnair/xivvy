from dotenv import load_dotenv

load_dotenv()

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

ARXIV_JSON_METADATASET_FILE = "data/arxiv-metadata-oai-test.json"  # Currently...
BATCH_SIZE = 4
LAST_PAPER_PROCESSED_FILE = "last_paper_processed.txt"
IF_OLD_PAPERS_PROCESSED_FILE = "if_old_papers_processed.txt"
KAGGLE_DATASET_NAME = "cornell-university/arxiv"
EMBEDDING_MODEL = "BAAI/bge-small-en-v1.5"
NUMBER_OF_THREADS = 4
NUMBER_OF_PARALLEL_PROCESSES = 1
QDRANT_HOST = "localhost"
QDRANT_PORT = 6333
