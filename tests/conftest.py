"""Pytest configuration and fixtures for MCP server tests."""
import json
import pytest
from unittest.mock import Mock, AsyncMock, MagicMock
from kurrentdbclient import NewEvent, StreamState
from kurrentdbclient.exceptions import NotFoundError


@pytest.fixture
def mock_kdb_client():
    """Create a mock KurrentDB client for testing."""
    client = Mock()

    # Setup default mock behaviors
    # Note: get_stream and read_stream return iterables, not coroutines
    client.get_stream = Mock()
    client.read_stream = Mock()
    client.append_to_stream = Mock()
    client.create_projection = Mock()
    client.update_projection = Mock()
    client.get_projection_statistics = Mock()

    return client


@pytest.fixture
def sample_event():
    """Create a sample event for testing."""
    event = Mock()
    event.type = "OrderPlaced"
    event.data = b'{"orderId": "12345", "amount": 100.50}'
    event.stream_name = "order-stream"
    event.event_number = 1
    return event


@pytest.fixture
def sample_events():
    """Create multiple sample events for testing."""
    events = []

    # Event 1
    event1 = Mock()
    event1.type = "OrderPlaced"
    event1.data = b'{"orderId": "12345", "amount": 100.50}'
    event1.stream_name = "order-stream"
    event1.event_number = 1
    events.append(event1)

    # Event 2
    event2 = Mock()
    event2.type = "OrderConfirmed"
    event2.data = b'{"orderId": "12345", "status": "confirmed"}'
    event2.stream_name = "order-stream"
    event2.event_number = 2
    events.append(event2)

    # Event 3
    event3 = Mock()
    event3.type = "OrderShipped"
    event3.data = b'{"orderId": "12345", "trackingNumber": "TRACK123"}'
    event3.stream_name = "order-stream"
    event3.event_number = 3
    events.append(event3)

    return events


@pytest.fixture
def stream_list_events():
    """Create sample $streams events for testing list_streams."""
    events = []

    # Stream 1
    event1 = Mock()
    event1.stream_name = "order-stream"
    events.append(event1)

    # Stream 2
    event2 = Mock()
    event2.stream_name = "user-stream"
    events.append(event2)

    # Stream 3
    event3 = Mock()
    event3.stream_name = "payment-stream"
    events.append(event3)

    return events


@pytest.fixture
def sample_projection_code():
    """Sample projection code for testing."""
    return """
fromStreams('order-stream')
    .when({
        $init: function () {
            return {
                count: 0
            }
        },
        $any: function (state, event) {
            state.count += 1;
            emit('order-count', 'CountUpdated', {count: state.count});
        }
    })
    .outputState()
"""


@pytest.fixture
def sample_projection_stats():
    """Sample projection statistics for testing."""
    stats = Mock()
    stats.name = "test-projection"
    stats.status = "Running"
    stats.progress = 100.0
    stats.events_processed_after_restart = 150
    stats.__str__ = Mock(return_value="Projection: test-projection, Status: Running, Progress: 100.0%")
    return stats


@pytest.fixture
def sample_event_data():
    """Sample event data dictionary."""
    return {
        "orderId": "12345",
        "customerId": "cust-789",
        "amount": 100.50,
        "currency": "USD",
        "items": [
            {"sku": "ITEM-001", "quantity": 2},
            {"sku": "ITEM-002", "quantity": 1}
        ]
    }


@pytest.fixture
def sample_event_metadata():
    """Sample event metadata dictionary."""
    return {
        "userId": "user-123",
        "timestamp": "2025-11-05T10:30:00Z",
        "correlationId": "corr-456"
    }


@pytest.fixture
def mock_server_module(mock_kdb_client, monkeypatch):
    """Mock the server module with a mock client."""
    import server
    monkeypatch.setattr(server, 'kdb_client', mock_kdb_client)
    return server


@pytest.fixture
def not_found_error():
    """Create a NotFoundError for testing."""
    return NotFoundError("Resource not found")


# Pytest configuration
def pytest_configure(config):
    """Configure pytest with custom markers."""
    config.addinivalue_line(
        "markers", "asyncio: mark test as async"
    )
    config.addinivalue_line(
        "markers", "unit: mark test as unit test"
    )
    config.addinivalue_line(
        "markers", "integration: mark test as integration test (requires KurrentDB)"
    )
    config.addinivalue_line(
        "markers", "e2e: mark test as end-to-end test"
    )
    config.addinivalue_line(
        "markers", "slow: mark test as slow running"
    )
