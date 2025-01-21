# tests/conftest.py
import pytest
import os
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, scoped_session

from tests.factories import (
    UserFactory, CommentsFactory, CommentsMentionsFactory,
    TwilioMessageFactory, AuthorFactory, ConversationFactory,
)

TEST_DATABASE_URL = "postgresql://postgres:postgres@127.0.0.1:54320/postgres"
os.environ['DATABASE_URL'] = TEST_DATABASE_URL
os.environ['TESTING'] = "True"


@pytest.fixture(scope="session")
def engine():
    """Create test database engine"""
    engine = create_engine(TEST_DATABASE_URL)

    # Set environment variables for test

    # Execute SQL file directly
    with engine.connect() as conn:
        with conn.begin():
            with open('tests/schema/0000_oval_ricochet.sql', 'r') as file:
                conn.execute(text(file.read()))

    yield engine

    # Cleanup
    engine.dispose()


@pytest.fixture(scope="function")
def db_session(engine):
    """Create new database session for each test"""
    connection = engine.connect()
    transaction = connection.begin()

    # Create scoped session
    session_factory = sessionmaker(bind=connection)
    Session = scoped_session(session_factory)
    session = Session()

    yield session

    # Cleanup
    session.close()
    Session.remove()
    transaction.rollback()
    connection.close()


@pytest.fixture(scope="function")
def setup_factories(db_session):
    """Setup database session for all factories"""

    factories = [
        UserFactory, CommentsFactory, CommentsMentionsFactory,
        TwilioMessageFactory, AuthorFactory, ConversationFactory
    ]

    for factory in factories:
        factory._meta.sqlalchemy_session = db_session

    yield

    # Reset factory sessions
    for factory in factories:
        factory._meta.sqlalchemy_session = None
