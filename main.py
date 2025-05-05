import logging.config
from fastapi import FastAPI, Query
from contextlib import asynccontextmanager

from models import ArxivDomains, SearchResult
from typing import List, Optional
from process.database import Database
from config import LOG_CONFIG, XIVVY_PORT

logging.config.dictConfig(LOG_CONFIG)


@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.logger = logging.getLogger(__name__)

    app.state.logger.info("Initializing Database...")
    app.state.db = Database()

    await app.state.db.create_collection_if_not_exists()
    app.state.logger.info("Initialized Database.")

    yield


app = FastAPI(
    lifespan=lifespan,
    title="Xivvy Search Engine",
    description="API for searching ArXiv papers",
)


@app.get("/id")
async def search_by_id(id: str):
    results = await app.state.db.search_by_id(paper_id=id)
    return results


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="main:app", port=XIVVY_PORT, host="localhost", reload=True)


@app.get("/search", response_model=List[SearchResult])
async def search_papers(
    query: Optional[str] = None,
    categories: List[ArxivDomains] = Query(None),
    categories_match_all: bool = False,  # default OR
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = 10,
):
    results = await app.state.db.search_by_query(
        query=query,
        categories=categories,
        categories_match_all=categories_match_all,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return results
