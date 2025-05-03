import logging.config
from fastapi import FastAPI, Query
from typing import List, Optional
from datetime import date
from contextlib import asynccontextmanager

from models import SearchResults

from process.database import Database
from process.embed import Embedder
from utils import wait_for_chroma, run_chroma_server, random_noun_or_adjective

from config import XIVVY_PORT, LOG_CONFIG, CHROMA_PORT

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
async def search(
    query: str | None = None,
    n: int = 5,
    categories: Optional[List[str]] = Query(None),
    start_date: Optional[date] = Query(None),
    end_date: Optional[date] = Query(None),
):
    if not query:
        query = random_noun_or_adjective()
    embedding = await app.state.embedder.embed_query(query)
    results = await app.state.db.search(
        embedding,
        top_k=n,
        category_filters=categories,
        start_date=start_date.isoformat() if start_date else None,
        end_date=end_date.isoformat() if end_date else None,
    )
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("main:app", host="localhost", port=XIVVY_PORT, reload=True)
