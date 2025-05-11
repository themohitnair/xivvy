import asyncio
from services.dataset import DatasetDownloader
from services.pipeline import Pipeline

DatasetDownloader().run()
asyncio.run(Pipeline().run())
