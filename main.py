import logging.config
import time
from fastapi import FastAPI, HTTPException, Query, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
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
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add CORS middleware to allow cross-origin requests
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Add GZip compression for responses
app.add_middleware(GZipMiddleware, minimum_size=1000)


# Add middleware for request logging, timing, and global error handling
@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time
        response.headers["X-Process-Time"] = str(process_time)
        app.state.logger.info(f"Request to {request.url.path} took {process_time:.4f} seconds")
        return response
    except Exception as e:
        # Log the exception but don't crash the server
        process_time = time.time() - start_time
        app.state.logger.error(f"Unhandled exception in {request.url.path}: {str(e)}")
        # Return a 500 response instead of crashing
        return Response(
            content=f'{{"detail": "Internal server error", "error_type": "{type(e).__name__}"}}',
            status_code=500,
            media_type="application/json"
        )


@app.get("/id", response_model=SearchResult, response_model_exclude_none=True)
async def search_by_id(id: str, response: Response):
    """Search for a paper by its ID"""
    try:
        if not id or not id.strip():
            response.status_code = 400
            return {"detail": "Paper ID cannot be empty"}
            
        app.state.logger.info(f"Searching for paper with ID: {id}")
        results = await app.state.db.search_by_id(paper_id=id)
        
        if not results:
            app.state.logger.info(f"Paper with ID {id} not found")
            response.status_code = 404
            return {"detail": f"Paper with ID {id} not found"}
            
        return results
    except Exception as e:
        app.state.logger.error(f"Error in search_by_id: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app="main:app", port=XIVVY_PORT, host="localhost", reload=True)


@app.get("/search", response_model=List[SearchResult], response_model_exclude_none=True)
async def search_papers(
    query: Optional[str] = None,
    categories: List[ArxivDomains] = Query(None),
    categories_match_all: bool = False,  # default OR
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    limit: int = Query(default=10, ge=1, le=100),  # Add validation
):
    """Search for papers using various criteria"""
    try:
        # Log search parameters
        app.state.logger.info(
            f"Search request: query='{query}', categories={categories}, "
            f"categories_match_all={categories_match_all}, date_from={date_from}, "
            f"date_to={date_to}, limit={limit}"
        )
        
        # Validate input parameters
        if query and len(query.strip()) > 500:
            app.state.logger.warning(f"Query too long: {len(query)} chars")
            raise HTTPException(status_code=400, detail="Query too long (max 500 characters)")
            
        # Validate date range if both dates are provided
        if date_from and date_to:
            try:
                from_dt = iso_date_to_unix(date_from)
                to_dt = iso_date_to_unix(date_to)
                if from_dt > to_dt:
                    app.state.logger.warning(f"Invalid date range: {date_from} to {date_to}")
                    raise HTTPException(
                        status_code=400, detail="date_from cannot be later than date_to"
                    )
            except ValueError as e:
                app.state.logger.warning(f"Invalid date format: {str(e)}")
                raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
        
        # Perform the search
        results = await app.state.db.search_by_query(
            query=query,
            categories=categories,
            categories_match_all=categories_match_all,
            date_from=date_from,
            date_to=date_to,
            limit=limit,
        )
        
        app.state.logger.info(f"Search returned {len(results)} results")
        return results
    except HTTPException:
        # Re-raise HTTP exceptions as they're already properly formatted
        raise
    except Exception as e:
        # Log unexpected errors and return a 500
        app.state.logger.error(f"Unexpected error in search_papers: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {type(e).__name__}")


@app.get("/health")
async def health_check():
    """Health check endpoint to verify API is running"""
    try:
        db_status = app.state.db.is_server_running()
        collection_status = await app.state.db.create_collection_if_not_exists()
        
        status = "healthy"
        if not db_status:
            status = "degraded"
        elif not collection_status:
            status = "partial"
            
        app.state.logger.info(f"Health check: {status}")
        
        return {
            "status": status,
            "database": "connected" if db_status else "disconnected",
            "collection": "ready" if collection_status else "not_ready",
            "version": "1.0.0",
            "timestamp": time.time()
        }
    except Exception as e:
        app.state.logger.error(f"Error in health check: {str(e)}")
        return {
            "status": "error",
            "error": str(e),
            "error_type": type(e).__name__,
            "version": "1.0.0",
            "timestamp": time.time()
        }
