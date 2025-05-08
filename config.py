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
DB_COLLECTION_NAME = "arxiv"
DB_PORT = 6333
XIVVY_PORT = 7000
EMB_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
BATCH_SIZE = 32
VECTOR_SIZE = 384
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

# Cache configuration
CACHE_SIZE = 1000  # Maximum number of items to store in cache
CACHE_TTL = 3600  # Cache time-to-live in seconds (1 hour)
