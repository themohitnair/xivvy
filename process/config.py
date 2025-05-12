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

DB_COLLECTION_NAME = "arxiv"
DB_PORT = 6334
HOST = "0.0.0.0"
CACHE_SIZE = 1000
CACHE_TTL = 3600
VECTOR_SIZE = 384
KAGGLE_DATASET_NAME = "Cornell-University/arxiv"
KAGGLE_CONFIG_DIR = "kaggle/"
EMB_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
BATCH_SIZE = 128

DATASET_PATH = "data/arxiv-metadata-oai-stuff.json"
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
