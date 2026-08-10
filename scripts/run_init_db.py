import asyncio
from app.database.init_db import init_db

async def main():
    print('running init_db...')
    await init_db(seed=False)
    print('init_db finished')

if __name__ == '__main__':
    asyncio.run(main())
