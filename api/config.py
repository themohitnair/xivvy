HOST = "qdr"
XIVVY_PORT = 7000
DB_COLLECTION_NAME = "arxiv"
DB_PORT = 6334
CACHE_SIZE = 1000
CACHE_TTL = 3600
VECTOR_SIZE = 384
EMB_MODEL = "sentence-transformers/all-MiniLM-L12-v2"
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
