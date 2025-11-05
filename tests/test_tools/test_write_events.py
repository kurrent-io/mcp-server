"""Unit tests for write_events_to_stream tool."""
import json
import pytest
from unittest.mock import Mock, call
from kurrentdbclient import NewEvent, StreamState


@pytest.mark.unit
def test_write_events_success(mock_server_module, sample_event_data, sample_event_metadata):
    """Test successful event writing."""
    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="order-stream",
        data=sample_event_data,
        event_type="OrderPlaced",
        metadata=sample_event_metadata
    )

    # Assert
    assert result == "Data written to stream: order-stream"

    # Verify client was called
    mock_server_module.kdb_client.append_to_stream.assert_called_once()

    # Get the call arguments
    call_args = mock_server_module.kdb_client.append_to_stream.call_args

    # Verify stream name
    assert call_args.kwargs['stream_name'] == "order-stream"

    # Verify current_version
    assert call_args.kwargs['current_version'] == StreamState.ANY

    # Verify events list
    events = call_args.kwargs['events']
    assert len(events) == 1

    # Verify event properties
    event = events[0]
    assert isinstance(event, NewEvent)
    assert event.type == "OrderPlaced"
    assert event.content_type == "application/json"

    # Verify data was serialized correctly
    event_data = json.loads(event.data.decode('utf-8'))
    assert event_data == sample_event_data

    # Verify metadata was serialized correctly
    event_metadata = json.loads(event.metadata.decode('utf-8'))
    assert event_metadata == sample_event_metadata


@pytest.mark.unit
def test_write_events_simple_data(mock_server_module):
    """Test writing event with simple data."""
    # Setup
    simple_data = {"message": "Hello World"}
    simple_metadata = {"source": "test"}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="test-stream",
        data=simple_data,
        event_type="TestEvent",
        metadata=simple_metadata
    )

    # Assert
    assert "Data written to stream: test-stream" in result

    # Verify the call
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]

    # Check data
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data == simple_data


@pytest.mark.unit
def test_write_events_empty_metadata(mock_server_module):
    """Test writing event with empty metadata."""
    # Setup
    data = {"key": "value"}
    empty_metadata = {}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="test-stream",
        data=data,
        event_type="TestEvent",
        metadata=empty_metadata
    )

    # Assert
    assert "Data written to stream: test-stream" in result

    # Verify metadata is empty but valid JSON
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_metadata = json.loads(event.metadata.decode('utf-8'))
    assert decoded_metadata == {}


@pytest.mark.unit
def test_write_events_complex_nested_data(mock_server_module):
    """Test writing event with complex nested data structure."""
    # Setup
    complex_data = {
        "order": {
            "id": "12345",
            "customer": {
                "name": "John Doe",
                "email": "john@example.com",
                "address": {
                    "street": "123 Main St",
                    "city": "Springfield",
                    "zip": "12345"
                }
            },
            "items": [
                {"sku": "ITEM-001", "qty": 2, "price": 10.99},
                {"sku": "ITEM-002", "qty": 1, "price": 25.50}
            ],
            "total": 47.48
        }
    }
    metadata = {"correlationId": "corr-123"}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="order-stream",
        data=complex_data,
        event_type="OrderPlaced",
        metadata=metadata
    )

    # Assert
    assert "Data written to stream: order-stream" in result

    # Verify complex data was serialized correctly
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data == complex_data


@pytest.mark.unit
def test_write_events_with_numbers(mock_server_module):
    """Test writing event with numeric data types."""
    # Setup
    numeric_data = {
        "integer": 42,
        "float": 3.14159,
        "negative": -100,
        "zero": 0,
        "large": 1000000
    }
    metadata = {}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="numeric-stream",
        data=numeric_data,
        event_type="NumericEvent",
        metadata=metadata
    )

    # Assert
    assert "Data written to stream: numeric-stream" in result

    # Verify numeric values preserved
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data["integer"] == 42
    assert decoded_data["float"] == 3.14159
    assert decoded_data["negative"] == -100


@pytest.mark.unit
def test_write_events_with_boolean(mock_server_module):
    """Test writing event with boolean values."""
    # Setup
    boolean_data = {
        "isActive": True,
        "isDeleted": False,
        "hasAccess": True
    }
    metadata = {}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="bool-stream",
        data=boolean_data,
        event_type="BooleanEvent",
        metadata=metadata
    )

    # Assert
    assert "Data written to stream: bool-stream" in result

    # Verify booleans preserved
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data["isActive"] is True
    assert decoded_data["isDeleted"] is False


@pytest.mark.unit
def test_write_events_with_arrays(mock_server_module):
    """Test writing event with array data."""
    # Setup
    array_data = {
        "tags": ["important", "urgent", "customer"],
        "numbers": [1, 2, 3, 4, 5],
        "mixed": ["string", 42, True, None]
    }
    metadata = {}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="array-stream",
        data=array_data,
        event_type="ArrayEvent",
        metadata=metadata
    )

    # Assert
    assert "Data written to stream: array-stream" in result

    # Verify arrays preserved
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data["tags"] == ["important", "urgent", "customer"]
    assert decoded_data["numbers"] == [1, 2, 3, 4, 5]


@pytest.mark.unit
def test_write_events_with_null_values(mock_server_module):
    """Test writing event with null/None values."""
    # Setup
    null_data = {
        "field1": "value",
        "field2": None,
        "field3": "another value"
    }
    metadata = {"key": None}

    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="null-stream",
        data=null_data,
        event_type="NullEvent",
        metadata=metadata
    )

    # Assert
    assert "Data written to stream: null-stream" in result

    # Verify null values preserved
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    decoded_data = json.loads(event.data.decode('utf-8'))
    assert decoded_data["field2"] is None


@pytest.mark.unit
def test_write_events_stream_name_variations(mock_server_module):
    """Test writing to streams with different naming conventions."""
    # Test various stream names
    stream_names = [
        "simple-stream",
        "stream_with_underscores",
        "stream.with.dots",
        "stream-123",
        "$system-stream"
    ]

    for stream_name in stream_names:
        mock_server_module.kdb_client.reset_mock()

        result = mock_server_module.write_events_to_stream(
            stream=stream_name,
            data={"test": "data"},
            event_type="TestEvent",
            metadata={}
        )

        assert f"Data written to stream: {stream_name}" in result
        mock_server_module.kdb_client.append_to_stream.assert_called_once()


@pytest.mark.unit
def test_write_events_event_type_variations(mock_server_module):
    """Test writing events with different event type naming conventions."""
    # Test various event types
    event_types = [
        "SimpleEvent",
        "Event_With_Underscores",
        "event-with-dashes",
        "EventWithNumbers123",
        "UPPERCASE_EVENT"
    ]

    for event_type in event_types:
        mock_server_module.kdb_client.reset_mock()

        result = mock_server_module.write_events_to_stream(
            stream="test-stream",
            data={"test": "data"},
            event_type=event_type,
            metadata={}
        )

        call_args = mock_server_module.kdb_client.append_to_stream.call_args
        event = call_args.kwargs['events'][0]
        assert event.type == event_type


@pytest.mark.unit
def test_write_events_content_type(mock_server_module):
    """Test that content type is always set to application/json."""
    # Execute
    result = mock_server_module.write_events_to_stream(
        stream="test-stream",
        data={"test": "data"},
        event_type="TestEvent",
        metadata={}
    )

    # Assert content type
    call_args = mock_server_module.kdb_client.append_to_stream.call_args
    event = call_args.kwargs['events'][0]
    assert event.content_type == "application/json"
