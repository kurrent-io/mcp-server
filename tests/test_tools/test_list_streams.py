"""Unit tests for list_streams tool."""
import pytest
from unittest.mock import Mock
from kurrentdbclient.exceptions import NotFoundError


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_success(mock_server_module, stream_list_events):
    """Test successful listing of streams."""
    # Setup
    mock_server_module.kdb_client.read_stream.return_value = stream_list_events

    # Execute
    result = await mock_server_module.list_streams(limit=100, read_backwards=True)

    # Assert
    assert "STREAMS FOUND:" in result
    assert "order-stream" in result
    assert "user-stream" in result
    assert "payment-stream" in result

    # Verify client was called correctly
    mock_server_module.kdb_client.read_stream.assert_called_once_with(
        stream_name="$streams",
        resolve_links=True,
        limit=100,
        backwards=True
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_with_custom_limit(mock_server_module, stream_list_events):
    """Test listing streams with custom limit."""
    # Setup - return only first 2 streams
    mock_server_module.kdb_client.read_stream.return_value = stream_list_events[:2]

    # Execute
    result = await mock_server_module.list_streams(limit=2, read_backwards=True)

    # Assert
    assert "STREAMS FOUND:" in result
    assert "order-stream" in result
    assert "user-stream" in result
    assert "payment-stream" not in result

    # Verify limit was passed
    mock_server_module.kdb_client.read_stream.assert_called_once_with(
        stream_name="$streams",
        resolve_links=True,
        limit=2,
        backwards=True
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_forward_reading(mock_server_module, stream_list_events):
    """Test listing streams in forward direction."""
    # Setup
    mock_server_module.kdb_client.read_stream.return_value = stream_list_events

    # Execute
    result = await mock_server_module.list_streams(limit=100, read_backwards=False)

    # Assert
    assert "STREAMS FOUND:" in result

    # Verify backwards flag was set to False
    mock_server_module.kdb_client.read_stream.assert_called_once_with(
        stream_name="$streams",
        resolve_links=True,
        limit=100,
        backwards=False
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_not_found(mock_server_module):
    """Test when $streams stream is not found (fresh database)."""
    # Setup
    error_msg = "Stream '$streams' not found"
    mock_server_module.kdb_client.read_stream.side_effect = NotFoundError(error_msg)

    # Execute
    result = await mock_server_module.list_streams()

    # Assert
    assert "$streams was not found" in result
    assert "fresh/empty database" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_empty_result(mock_server_module):
    """Test listing when no streams exist."""
    # Setup - empty list
    mock_server_module.kdb_client.read_stream.return_value = []

    # Execute
    result = await mock_server_module.list_streams()

    # Assert
    assert "STREAMS FOUND:" in result
    # Should just have the prefix with no stream names


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_single_stream(mock_server_module):
    """Test listing with a single stream."""
    # Setup
    event = Mock()
    event.stream_name = "only-stream"
    mock_server_module.kdb_client.read_stream.return_value = [event]

    # Execute
    result = await mock_server_module.list_streams()

    # Assert
    assert "STREAMS FOUND:" in result
    assert "only-stream" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_default_parameters(mock_server_module, stream_list_events):
    """Test list_streams with default parameters."""
    # Setup
    mock_server_module.kdb_client.read_stream.return_value = stream_list_events

    # Execute - using defaults
    result = await mock_server_module.list_streams()

    # Assert
    mock_server_module.kdb_client.read_stream.assert_called_once_with(
        stream_name="$streams",
        resolve_links=True,
        limit=100,
        backwards=True
    )
    assert "STREAMS FOUND:" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_formatting(mock_server_module):
    """Test that streams are formatted correctly with commas."""
    # Setup - multiple streams
    events = []
    for stream_name in ["stream-1", "stream-2", "stream-3", "stream-4"]:
        event = Mock()
        event.stream_name = stream_name
        events.append(event)

    mock_server_module.kdb_client.read_stream.return_value = events

    # Execute
    result = await mock_server_module.list_streams()

    # Assert - check comma-separated format
    assert "STREAMS FOUND:" in result
    assert "stream-1," in result
    assert "stream-2," in result
    assert "stream-3," in result
    assert "stream-4," in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_list_streams_with_special_characters(mock_server_module):
    """Test listing streams with special characters in names."""
    # Setup
    events = []
    special_names = ["stream-with-dashes", "stream_with_underscores", "stream.with.dots", "$system-stream"]
    for stream_name in special_names:
        event = Mock()
        event.stream_name = stream_name
        events.append(event)

    mock_server_module.kdb_client.read_stream.return_value = events

    # Execute
    result = await mock_server_module.list_streams()

    # Assert - all special character streams should be listed
    for name in special_names:
        assert name in result
