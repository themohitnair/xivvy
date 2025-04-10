from fastapi import FastAPI
from contextlib import asynccontextmanager
from search.database import Database
from search.embed import Embedder
from fastapi.responses import JSONResponse
from models import SearchResult
from typing import List

import logging.config
from config import LOG_CONFIG

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


@app.get("/search/", response_model=List[SearchResult])
async def search(query: str):
    logger = app.state.logger
    embedder = app.state.embedder
    database = app.state.db

    logger.info(f"Vector Count: {await database.count_vectors()}")

    query_vector = embedder.embed_query(query)

    results = await database.search(query_vector, 10)

    return JSONResponse(content={"results": [r.dict() for r in results]})


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="main:app", port=8000, host="localhost", reload=True)
