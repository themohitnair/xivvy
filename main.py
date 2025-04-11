from fastapi import FastAPI
from contextlib import asynccontextmanager
from typing import List
import logging.config

from search.database import Database
from search.embed import Embedder
from search.metadata import Lucy
from config import LOG_CONFIG
from models import SemSearchResult

logging.config.dictConfig(LOG_CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.embedder = Embedder()
    app.state.db = Database()
    app.state.logger = logging.getLogger(__name__)

    await app.state.db.initialize()
    app.state.logger.info("App initialized...")

    yield

    await app.state.db.client.close()
    app.state.logger.info("App closed...")


app = FastAPI(lifespan=lifespan)


@app.get("/search/", response_model=List[SemSearchResult])
async def search(query: str):
    logger = app.state.logger
    embedder = app.state.embedder
    database = app.state.db

    query_vector = embedder.embed_query(query)
    logger.info("Query embedded!")

    results = await database.search(query_vector, 10)
    logger.info("Qdrant Results received!")

    metadata_fetcher = Lucy(results)

    enriched_results = await metadata_fetcher.get_semantic_results()
    logger.info("Results enriched with arXiv data.")

    return enriched_results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="main:app", port=8000, host="localhost", reload=True)
