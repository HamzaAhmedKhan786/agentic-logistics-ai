from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, String, Text, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from config.settings import settings
from models.schemas import PlanResponse


class Base(DeclarativeBase):
    pass


class PlanRecord(Base):
    __tablename__ = "plan_runs"

    run_id: Mapped[str] = mapped_column(String(36), primary_key=True)
    status: Mapped[str] = mapped_column(String(32), index=True)
    approved: Mapped[bool] = mapped_column(Boolean, default=False)
    payload: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )


engine = create_async_engine(settings.database_url)
Session = async_sessionmaker(engine, expire_on_commit=False)


async def init_database() -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)


async def save_plan(plan: PlanResponse) -> None:
    async with Session() as session:
        record = await session.get(PlanRecord, plan.run_id)
        payload = plan.model_dump_json()
        if record:
            record.payload = payload
            record.status = plan.status
            record.approved = plan.approved
        else:
            session.add(
                PlanRecord(
                    run_id=plan.run_id,
                    status=plan.status,
                    approved=plan.approved,
                    payload=payload,
                )
            )
        await session.commit()


async def get_plan(run_id: str) -> dict | None:
    async with Session() as session:
        record = await session.get(PlanRecord, run_id)
        return json.loads(record.payload) if record else None


async def approve_plan(run_id: str) -> dict | None:
    async with Session() as session:
        record = await session.get(PlanRecord, run_id)
        if not record:
            return None
        payload = json.loads(record.payload)
        payload["approved"] = True
        payload["approval_required"] = False
        payload["status"] = "completed"
        record.approved = True
        record.status = "completed"
        record.payload = json.dumps(payload)
        await session.commit()
        return payload


async def list_monitorable_runs() -> list[str]:
    async with Session() as session:
        result = await session.execute(
            select(PlanRecord.run_id).where(
                PlanRecord.status.in_(["completed", "awaiting_approval"])
            )
        )
        return list(result.scalars())
