from datetime import datetime, timedelta, timezone
from select import select
from typing import List, Optional

from sqlalchemy import func
from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Customer, Ticket
from src.tickets.schemas import Status, TicketCreate, TicketUpdate


async def count_recently_blocked_tickets(
    session: AsyncSession, time_window_minutes: int
) -> int:
    """Counts the number of tickets blocked within a given time window."""
    time_threshold = datetime.now(timezone.utc) - timedelta(minutes=time_window_minutes)
    statement = (
        select(func.count(Ticket.id))
        .where(Ticket.status == Status.blocked)
        .where(Ticket.created_at >= time_threshold)
    )
    result = await session.exec(statement)
    return result.first()


async def block_ticket(
    session: AsyncSession,
    reason: str,
    category: str,
    ticket_id: int | None = None,
    email: str | None = None,
) -> Optional[Ticket]:
    """
    Create a ticket with "blocked" status
    """

    blocked_ticket_data = TicketCreate(
        ticket_id=ticket_id,
        subject=f"Blocked Ticket #{ticket_id}",
        content=f"Blocked due to: {reason} ({category})",
        email=email,
        status=Status.blocked,
        blocked_reason=reason,
        blocked_category=category,
    )
    return await create_ticket(session, blocked_ticket_data)


async def create_ticket(session: AsyncSession, ticket_data: TicketCreate) -> Ticket:
    """
    Create a new ticket in the database.
    """
    # Create a new Ticket instance from the schema data
    new_ticket = Ticket.model_validate(ticket_data)

    session.add(new_ticket)
    await session.commit()
    await session.refresh(new_ticket)
    return new_ticket


async def get_ticket_by_id(session: AsyncSession, ticket_id: int) -> Ticket | None:
    """
    Retrieve a single ticket by its UUID.
    """
    statement = select(Ticket).where(Ticket.ticket_id == int(ticket_id))
    result = await session.exec(statement)
    return result.first()


async def update_ticket(
    session: AsyncSession, ticket: Ticket, ticket_in: TicketUpdate
) -> Ticket:
    """
    Update a ticket's attributes.
    """
    # Get the update data from the input schema
    update_data = ticket_in.model_dump(exclude_unset=True)

    # Update the model instance with the new data
    ticket.sqlmodel_update(update_data)

    session.add(ticket)
    await session.commit()
    await session.refresh(ticket)
    return ticket


async def get_all_tickets(
    session: AsyncSession,
    limit: int = 20,
    offset: int = 0,
) -> List[Ticket]:
    """
    Get list of tickets
    """
    statement = (
        select(Ticket)
        .options(selectinload(Ticket.customer))
        .join(Customer, isouter=True)
    )

    statement = statement.offset(offset).limit(limit)

    result = await session.exec(statement)
    return result.all()


# sudo -u postgres psql
#   CREATE USER postgres WITH PASSWORD 'XXXXXXXX'
#   CREATE DATABASE customer_support_db OWNER postgres ENCODING 'UTF8';

# alembic --help
# alembic init -t async migrations
# alembic revision --autogenerate -m "Initial migration"
# alembic upgrade head
# docker run -d --name redis -p 6379:6379 redis

# fastapi dev main.py

# uvicorn main:app --reload

# uvicorn src:app --reload --port 8001

# ALTER USER postgres WITH PASSWORD 'Avwunudiogba';
# ALTER USER postgres WITH PASSWORD 'Avwunudiogba';
