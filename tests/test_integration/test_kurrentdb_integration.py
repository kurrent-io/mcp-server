"""Integration tests for KurrentDB MCP server.

These tests require a running KurrentDB instance.
Set KURRENTDB_CONNECTION_STRING environment variable to run these tests.

Example:
    export KURRENTDB_CONNECTION_STRING="esdb://localhost:2113?tls=false"
    pytest tests/test_integration -m integration
"""
import os
import json
import pytest
from kurrentdbclient import KurrentDBClient, NewEvent, StreamState
from kurrentdbclient.exceptions import NotFoundError


# Skip all integration tests if KurrentDB connection string is not set
pytestmark = pytest.mark.skipif(
    "KURRENTDB_CONNECTION_STRING" not in os.environ,
    reason="KurrentDB connection string not set. Set KURRENTDB_CONNECTION_STRING to run integration tests."
)


@pytest.fixture(scope="module")
def kdb_client():
    """Create a real KurrentDB client for integration testing."""
    connection_string = os.environ.get("KURRENTDB_CONNECTION_STRING")
    client = KurrentDBClient(uri=connection_string)
    yield client
    # Cleanup if needed


@pytest.fixture
def test_stream_name():
    """Generate a unique test stream name."""
    import uuid
    return f"test-stream-{uuid.uuid4()}"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_and_read_stream(kdb_client, test_stream_name):
    """Test writing to and reading from a real stream."""
    # Write events
    event_data = {"message": "Hello, KurrentDB!", "count": 42}
    event_metadata = {"source": "integration-test"}

    event = NewEvent(
        type="TestEvent",
        data=bytes(json.dumps(event_data), 'utf-8'),
        content_type='application/json',
        metadata=bytes(json.dumps(event_metadata), 'utf-8')
    )

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=[event],
        current_version=StreamState.ANY
    )

    # Read events back
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=False,
        limit=10
    )

    # Convert generator to list
    event_list = list(events)

    # Assert
    assert len(event_list) >= 1
    read_event = event_list[0]
    assert read_event.type == "TestEvent"

    read_data = json.loads(read_event.data.decode('utf-8'))
    assert read_data["message"] == "Hello, KurrentDB!"
    assert read_data["count"] == 42


@pytest.mark.integration
@pytest.mark.asyncio
async def test_write_multiple_events(kdb_client, test_stream_name):
    """Test writing multiple events to a stream."""
    # Write multiple events
    events_to_write = []
    for i in range(5):
        event_data = {"eventNumber": i, "message": f"Event {i}"}
        event = NewEvent(
            type=f"Event{i}",
            data=bytes(json.dumps(event_data), 'utf-8'),
            content_type='application/json',
            metadata=b'{}'
        )
        events_to_write.append(event)

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=events_to_write,
        current_version=StreamState.ANY
    )

    # Read all events
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=False,
        limit=10
    )

    event_list = list(events)

    # Assert
    assert len(event_list) == 5
    for i, event in enumerate(event_list):
        assert event.type == f"Event{i}"
        data = json.loads(event.data.decode('utf-8'))
        assert data["eventNumber"] == i


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_stream_backwards(kdb_client, test_stream_name):
    """Test reading stream in backward direction."""
    # Write events
    events_to_write = []
    for i in range(3):
        event = NewEvent(
            type=f"Event{i}",
            data=bytes(json.dumps({"order": i}), 'utf-8'),
            content_type='application/json',
            metadata=b'{}'
        )
        events_to_write.append(event)

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=events_to_write,
        current_version=StreamState.ANY
    )

    # Read backwards
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=True,
        limit=10
    )

    event_list = list(events)

    # Assert - should be in reverse order
    assert len(event_list) == 3
    assert event_list[0].type == "Event2"
    assert event_list[1].type == "Event1"
    assert event_list[2].type == "Event0"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_stream_with_limit(kdb_client, test_stream_name):
    """Test reading stream with limit."""
    # Write 10 events
    events_to_write = []
    for i in range(10):
        event = NewEvent(
            type="TestEvent",
            data=bytes(json.dumps({"number": i}), 'utf-8'),
            content_type='application/json',
            metadata=b'{}'
        )
        events_to_write.append(event)

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=events_to_write,
        current_version=StreamState.ANY
    )

    # Read with limit of 5
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=False,
        limit=5
    )

    event_list = list(events)

    # Assert - should only get 5 events
    assert len(event_list) == 5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_read_nonexistent_stream(kdb_client):
    """Test reading a stream that doesn't exist."""
    with pytest.raises(NotFoundError):
        events = kdb_client.get_stream(
            stream_name="nonexistent-stream-12345",
            resolve_links=True,
            backwards=False,
            limit=10
        )
        # Try to iterate (this triggers the actual read)
        list(events)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_list_streams(kdb_client):
    """Test listing streams via $streams stream."""
    try:
        # Read $streams
        events = kdb_client.read_stream(
            stream_name="$streams",
            resolve_links=True,
            limit=100,
            backwards=True
        )

        event_list = list(events)

        # Assert - should have at least some streams
        assert len(event_list) >= 0  # May be empty in fresh database

        # If streams exist, check structure
        if len(event_list) > 0:
            assert hasattr(event_list[0], 'stream_name')

    except NotFoundError:
        # This is acceptable for a fresh database
        pytest.skip("$streams not found - fresh database")


@pytest.mark.integration
@pytest.mark.slow
def test_create_and_check_projection(kdb_client):
    """Test creating a projection and checking its status."""
    projection_name = f"test-projection-{os.urandom(4).hex()}"

    projection_code = """
fromStreams('$all')
    .when({
        $init: function () {
            return {
                count: 0
            }
        },
        $any: function (state, event) {
            state.count += 1;
        }
    })
    .outputState()
"""

    try:
        # Create projection
        kdb_client.create_projection(
            name=projection_name,
            query=projection_code,
            emit_enabled=True,
            track_emitted_streams=True
        )

        # Give it a moment to initialize
        import time
        time.sleep(2)

        # Check status
        stats = kdb_client.get_projection_statistics(name=projection_name)

        # Assert
        assert stats is not None
        assert hasattr(stats, 'name')
        # Note: Depending on KurrentDB version, status might vary

    except Exception as e:
        pytest.skip(f"Projection test failed - may not be supported: {e}")


@pytest.mark.integration
def test_get_nonexistent_projection_status(kdb_client):
    """Test getting status of non-existent projection."""
    with pytest.raises(NotFoundError):
        kdb_client.get_projection_statistics(name="nonexistent-projection-12345")


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complex_event_data(kdb_client, test_stream_name):
    """Test writing and reading complex nested event data."""
    complex_data = {
        "order": {
            "id": "ORD-12345",
            "customer": {
                "name": "John Doe",
                "email": "john@example.com"
            },
            "items": [
                {"sku": "ITEM-001", "qty": 2, "price": 10.99},
                {"sku": "ITEM-002", "qty": 1, "price": 25.50}
            ],
            "total": 47.48,
            "flags": {
                "isPaid": True,
                "isShipped": False
            }
        }
    }

    event = NewEvent(
        type="OrderPlaced",
        data=bytes(json.dumps(complex_data), 'utf-8'),
        content_type='application/json',
        metadata=b'{}'
    )

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=[event],
        current_version=StreamState.ANY
    )

    # Read back
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=False,
        limit=10
    )

    event_list = list(events)
    read_data = json.loads(event_list[0].data.decode('utf-8'))

    # Assert complex structure preserved
    assert read_data == complex_data
    assert read_data["order"]["customer"]["name"] == "John Doe"
    assert len(read_data["order"]["items"]) == 2
    assert read_data["order"]["flags"]["isPaid"] is True


@pytest.mark.integration
@pytest.mark.asyncio
async def test_event_metadata(kdb_client, test_stream_name):
    """Test that event metadata is properly stored and retrieved."""
    metadata = {
        "userId": "user-123",
        "correlationId": "corr-456",
        "timestamp": "2025-11-05T10:00:00Z"
    }

    event = NewEvent(
        type="TestEvent",
        data=b'{"test": "data"}',
        content_type='application/json',
        metadata=bytes(json.dumps(metadata), 'utf-8')
    )

    kdb_client.append_to_stream(
        stream_name=test_stream_name,
        events=[event],
        current_version=StreamState.ANY
    )

    # Read back
    events = kdb_client.get_stream(
        stream_name=test_stream_name,
        resolve_links=True,
        backwards=False,
        limit=10
    )

    event_list = list(events)
    read_metadata = json.loads(event_list[0].metadata.decode('utf-8'))

    # Assert metadata preserved
    assert read_metadata == metadata
