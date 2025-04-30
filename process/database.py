import chromadb
from config import CHROMA_PORT, CHROMA_COLLECTION_NAME, LOG_CONFIG
import logging.config

logging.config.dictConfig(LOG_CONFIG)

# command to run at port 6969: `chroma run --path chroma_data/ --port 6969`


class Database:
    def __init__(self):
        self.client = None
        self.collection = None
        self.logger = logging.getLogger(__name__)

    async def initialize(self):
        self.logger("Initializing ChromaDB Client...")
        self.client = await chromadb.AsyncHttpClient(host="localhost", port=CHROMA_PORT)
        self.logger("ChromaDB Client Initialized.")

        self.logger("Creating collection if it doesn't exist...")
        self.collection = await self.client.get_or_create_collection(
            CHROMA_COLLECTION_NAME
        )
        self.logger("Created collection.")
