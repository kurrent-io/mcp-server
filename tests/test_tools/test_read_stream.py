"""Unit tests for read_stream tool."""
import pytest
from unittest.mock import Mock
from kurrentdbclient.exceptions import NotFoundError


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_success(mock_server_module, sample_events):
    """Test successful stream reading."""
    # Setup
    mock_server_module.kdb_client.get_stream.return_value = sample_events

    # Execute
    result = await mock_server_module.read_stream(stream="order-stream", backwards=False, limit=10)

    # Assert
    assert "Start of stream:" in result
    assert "OrderPlaced" in result
    assert "OrderConfirmed" in result
    assert "OrderShipped" in result
    assert "End of stream" in result
    assert "NO FURTHER ACTION REQUIRED" in result

    # Verify client was called correctly
    mock_server_module.kdb_client.get_stream.assert_called_once_with(
        stream_name="order-stream",
        resolve_links=True,
        backwards=False,
        limit=10
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_backwards(mock_server_module, sample_events):
    """Test reading stream backwards."""
    # Setup
    mock_server_module.kdb_client.get_stream.return_value = sample_events

    # Execute
    result = await mock_server_module.read_stream(stream="order-stream", backwards=True, limit=5)

    # Assert
    assert "Start of stream:" in result
    assert "End of stream" in result

    # Verify backwards flag was passed
    mock_server_module.kdb_client.get_stream.assert_called_once_with(
        stream_name="order-stream",
        resolve_links=True,
        backwards=True,
        limit=5
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_custom_limit(mock_server_module, sample_events):
    """Test reading stream with custom limit."""
    # Setup
    mock_server_module.kdb_client.get_stream.return_value = sample_events[:2]

    # Execute
    result = await mock_server_module.read_stream(stream="order-stream", backwards=False, limit=2)

    # Assert
    assert "Start of stream:" in result
    assert "End of stream" in result

    # Verify limit was passed
    mock_server_module.kdb_client.get_stream.assert_called_once_with(
        stream_name="order-stream",
        resolve_links=True,
        backwards=False,
        limit=2
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_not_found(mock_server_module):
    """Test reading a non-existent stream."""
    # Setup
    error_msg = "Stream 'nonexistent-stream' not found"
    mock_server_module.kdb_client.get_stream.side_effect = NotFoundError(error_msg)

    # Execute
    result = await mock_server_module.read_stream(stream="nonexistent-stream")

    # Assert
    assert "404 Stream not found" in result
    assert error_msg in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_empty(mock_server_module):
    """Test reading an empty stream."""
    # Setup - empty list of events
    mock_server_module.kdb_client.get_stream.return_value = []

    # Execute
    result = await mock_server_module.read_stream(stream="empty-stream")

    # Assert
    assert "Start of stream:" in result
    assert "End of stream" in result
    assert "NO FURTHER ACTION REQUIRED" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_single_event(mock_server_module, sample_event):
    """Test reading a stream with a single event."""
    # Setup
    mock_server_module.kdb_client.get_stream.return_value = [sample_event]

    # Execute
    result = await mock_server_module.read_stream(stream="single-event-stream")

    # Assert
    assert "Start of stream:" in result
    assert "OrderPlaced" in result
    assert '"orderId": "12345"' in result
    assert "End of stream" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_default_parameters(mock_server_module, sample_events):
    """Test read_stream with default parameters."""
    # Setup
    mock_server_module.kdb_client.get_stream.return_value = sample_events

    # Execute - using default backwards=False and limit=10
    result = await mock_server_module.read_stream(stream="test-stream")

    # Assert
    mock_server_module.kdb_client.get_stream.assert_called_once_with(
        stream_name="test-stream",
        resolve_links=True,
        backwards=False,
        limit=10
    )
    assert "Start of stream:" in result
    assert "End of stream" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_read_stream_event_data_parsing(mock_server_module):
    """Test that event data is properly decoded and included in result."""
    # Setup - create event with specific JSON data
    event = Mock()
    event.type = "UserRegistered"
    event.data = b'{"userId": "user-123", "email": "test@example.com", "name": "John Doe"}'
    event.stream_name = "user-stream"

    mock_server_module.kdb_client.get_stream.return_value = [event]

    # Execute
    result = await mock_server_module.read_stream(stream="user-stream")

    # Assert - check that JSON data was decoded
    assert "UserRegistered" in result
    assert "user-123" in result
    assert "test@example.com" in result
    assert "John Doe" in result
