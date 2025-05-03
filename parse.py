import asyncio
import subprocess

from process.read import Parser
from process.embed import Embedder
from process.database import Database
from process.utils import wait_for_chroma, run_chroma_server

from config import VALID_CATEGORIES, CHROMA_PORT

# =========== OPTIONAL TOKEN COUNTING ==============
# ENABLE_TOKEN_COUNTING = True
# if ENABLE_TOKEN_COUNTING:
#     import tiktoken
#     enc = tiktoken.get_encoding("cl100k_base")
#     total_tokens = 0
# ===================================================


async def main():
    chroma_process = run_chroma_server(port=CHROMA_PORT)
    try:
        await wait_for_chroma(host="localhost", port=CHROMA_PORT)

        parser = Parser()
        database = Database()
        embedder = Embedder()

        await database.initialize()

        errors = 0
        categs = set()
        total_inserted = 0
        # total_tokens = 0

        async for batch in parser.parse_yield_batches():
            # ======== TOKEN COUNTING HOOK =========
            # if ENABLE_TOKEN_COUNTING:
            #     for paper in batch:
            #         total_tokens += len(enc.encode(paper.abstract_title))
            # ======================================

            embedded_batch = await embedder.embed_batch(batch)

            if embedded_batch:
                await database.insert_batch(embedded_batch)
                total_inserted += len(embedded_batch)

        print("========================================")
        print(f"Unique categories found: {categs}")
        print(f"Invalid categories count: {errors}")
        print(f"Unique categories count: {len(categs)}")
        print(f"Valid categories count: {len(VALID_CATEGORIES)}")
        print(f"Total papers inserted: {total_inserted}")

        # if ENABLE_TOKEN_COUNTING:
        #     print(f"Total tokens in all papers' content: {total_tokens}")
        print("========================================")

    finally:
        print("[INFO] Shutting down Chroma server...")
        chroma_process.terminate()
        try:
            chroma_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            chroma_process.kill()


if __name__ == "__main__":
    asyncio.run(main())
