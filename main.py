from fastapi import FastAPI
from config import XIVVY_PORT


app = FastAPI()


@app.get("/")
async def search(query: str):
    return {"message": f"xivvy breathes! your query was {query}"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app=app, host="localhost", port=XIVVY_PORT)
