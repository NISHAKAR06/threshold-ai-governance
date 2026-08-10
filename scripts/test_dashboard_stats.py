import os
import asyncio

os.environ['DATABASE_URL'] = 'postgresql+asyncpg://neondb_owner:npg_wJZRxSy2h9dn@ep-icy-math-awbtcpqh-pooler.c-12.us-east-1.aws.neon.tech/neondb?sslmode=require&channel_binding=require'

from app.database.database import engine
from app.database.session import AsyncSessionLocal
from app.repositories.action_repository import ActionRepository
from app.repositories.audit_repository import AuditRepository
from app.repositories.review_repository import ReviewRepository
from app.services.dashboard_service import DashboardService

async def main():
    async with AsyncSessionLocal() as session:
        svc = DashboardService(
            action_repo=ActionRepository(session),
            audit_repo=AuditRepository(session),
            review_repo=ReviewRepository(session),
        )
        print('Calling get_stats...')
        result = await svc.get_stats()
        print('Result:', result)

if __name__ == '__main__':
    asyncio.run(main())
