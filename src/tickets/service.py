from typing import List

from sqlalchemy.orm import selectinload
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from src.db.models import Customer, Ticket
from src.tickets.schemas import TicketCreate, TicketUpdate


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
    statement = select(Ticket).options(selectinload(Ticket.customer)).join(Customer)

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
