import logging.config
from fastapi import FastAPI
from contextlib import asynccontextmanager

from models import SearchResults

from process.database import Database
from process.embed import Embedder
from config import XIVVY_PORT, LOG_CONFIG, CHROMA_PORT
from process.utils import wait_for_chroma, run_chroma_server

logging.config.dictConfig(LOG_CONFIG)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Server starting…")
    process = run_chroma_server(CHROMA_PORT)
    logger.info("ChromaDB server subprocess started.")

    await wait_for_chroma("localhost", CHROMA_PORT)
    logger.info("ChromaDB HTTP endpoint is up and returning 200 OK.")

    app.state.db = Database()
    await app.state.db.initialize()
    logger.info("Database client and collection ready.")

    app.state.embedder = Embedder()
    logger.info("Embedder ready.")

    yield

    process.terminate()
    logger.info("ChromaDB server subprocess terminated.")


app = FastAPI(lifespan=lifespan)


@app.get("/", response_model=SearchResults)
async def search(query: str):
    embedding = await app.state.embedder.embed_query(query)
    results = await app.state.db.search(embedding, top_k=5)
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="localhost", port=XIVVY_PORT)
