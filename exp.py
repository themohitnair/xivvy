from process.parse import Parser
import asyncio
from config import VALID_CATEGORIES


async def main():
    parser = Parser()
    errors = 0
    categs = set()
    async for batch in parser.parse_yield_batches():
        for obj in batch:
            for category in obj.categories:
                if category not in VALID_CATEGORIES:
                    errors += 1
                categs.add(category.value)

    print(categs)
    print(errors)
    print(len(categs))
    print(len(VALID_CATEGORIES))


if __name__ == "__main__":
    asyncio.run(main())
