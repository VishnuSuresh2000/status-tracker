"""
Pytest configuration file for status-tracker tests.
Sets up consistent test fixtures and environment variables.
"""

import os
import pytest
from fastapi.testclient import TestClient
from sqlmodel import Session, SQLModel, create_engine, StaticPool

# Set test auth token BEFORE importing main
# This ensures all tests use the same token consistently
os.environ["API_AUTH_TOKEN"] = "test-auth-token-for-tests"

from main import app, get_session


# Setup in-memory SQLite for testing
engine = create_engine(
    "sqlite://",
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)


def override_get_session():
    """Override session for testing."""
    with Session(engine) as session:
        yield session


# Apply dependency override globally
app.dependency_overrides[get_session] = override_get_session


@pytest.fixture(name="session")
def session_fixture():
    """Create a fresh database session for each test."""
    SQLModel.metadata.create_all(engine)
    with Session(engine) as session:
        yield session
    SQLModel.metadata.drop_all(engine)


@pytest.fixture(name="client")
def client_fixture(session: Session):
    """Create a test client with the session."""
    def get_session_override():
        return session

    app.dependency_overrides[get_session] = get_session_override
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()


@pytest.fixture(name="auth_headers")
def auth_headers_fixture():
    """Return valid authentication headers for all tests."""
    return {"Authorization": "Bearer test-auth-token-for-tests"}
