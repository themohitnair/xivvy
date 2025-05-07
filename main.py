import logging.config
from fastapi import FastAPI, HTTPException, Query
from contextlib import asynccontextmanager

from models import ArxivDomains, SearchResult
from typing import List, Optional
from process.database import Database
from config import LOG_CONFIG, XIVVY_PORT
from utils import iso_date_to_unix

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
    if date_from and date_to:
        from_dt = iso_date_to_unix(date_from)
        to_dt = iso_date_to_unix(date_to)
        if from_dt > to_dt:
            raise HTTPException(
                status_code=400, detail="date_from cannot be later than date_to"
            )
    results = await app.state.db.search_by_query(
        query=query,
        categories=categories,
        categories_match_all=categories_match_all,
        date_from=date_from,
        date_to=date_to,
        limit=limit,
    )
    return results
