import asyncio
import httpx
import subprocess
from wonderwords import RandomWord
import random


def run_chroma_server(port: int):
    return subprocess.Popen(
        [
            "chroma",
            "run",
            "--host",
            "localhost",
            "--port",
            str(port),
            "--path",
            "./chroma_data",
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


async def wait_for_chroma(host: str, port: int, timeout: float = 30.0):
    url = f"http://{host}:{port}/openapi.json"
    start = asyncio.get_event_loop().time()
    while True:
        try:
            async with httpx.AsyncClient() as client:
                resp = await client.get(url)
                if resp.status_code == 200:
                    return
        except (httpx.ConnectError, httpx.ReadError):
            pass
        if asyncio.get_event_loop().time() - start > timeout:
            raise TimeoutError(f"Chroma server did not start within {timeout}s")
        await asyncio.sleep(0.5)


def random_noun_or_adjective():
    rw = RandomWord()
    if random.choice(["noun", "adjective"]) == "noun":
        return rw.word(include_parts_of_speech=["noun"])
    else:
        return rw.word(include_parts_of_speech=["adjective"])
