"""Unit tests for projection tools."""
import pytest
from kurrentdbclient.exceptions import NotFoundError


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_projection_returns_message_structure(mock_server_module):
    """Test that build_projection returns proper LLM message structure."""
    # Execute
    result = await mock_server_module.build_projection(
        user_prompt="Count all order events and emit the count"
    )

    # Assert structure
    assert isinstance(result, list)
    assert len(result) == 2

    # Check system message
    assert result[0]["role"] == "system"
    assert "KurrentDB projection generator" in result[0]["content"]
    assert "fromStreams" in result[0]["content"]
    assert "emit" in result[0]["content"]

    # Check user message
    assert result[1]["role"] == "user"
    assert "Count all order events and emit the count" in result[1]["content"]


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_projection_includes_template(mock_server_module):
    """Test that build_projection includes the projection template."""
    # Execute
    result = await mock_server_module.build_projection(
        user_prompt="Test prompt"
    )

    # Assert template components are present in system message
    system_content = result[0]["content"]
    assert "fromStreams" in system_content
    assert "$init" in system_content
    assert "$any" in system_content
    assert "emit" in system_content
    assert "linkTo" in system_content
    assert "outputState" in system_content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_projection_includes_best_practices(mock_server_module):
    """Test that build_projection includes best practices guidance."""
    # Execute
    result = await mock_server_module.build_projection(
        user_prompt="Test prompt"
    )

    # Assert best practices are included
    system_content = result[0]["content"]
    assert "KEEP IT AS SIMPLE AS POSSIBLE" in system_content
    assert "16 MB" in system_content
    assert "create_projection" in system_content


@pytest.mark.asyncio
@pytest.mark.unit
async def test_build_projection_with_different_prompts(mock_server_module):
    """Test build_projection with various user prompts."""
    prompts = [
        "Count events by type",
        "Filter order events where amount > 100",
        "Create a projection that tracks user registrations",
        "Aggregate sales by customer"
    ]

    for prompt in prompts:
        result = await mock_server_module.build_projection(user_prompt=prompt)

        # Assert each prompt is included in the user message
        assert result[1]["content"] == f"Write a projection in KurrentDB that does the following: {prompt}"


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_projection_success(mock_server_module, sample_projection_code):
    """Test successful projection creation."""
    # Execute
    result = await mock_server_module.create_projection(
        projection_name="test-projection",
        code=sample_projection_code
    )

    # Assert
    assert "test projection with test-projection" in result
    assert "test_projection tool" in result

    # Verify client was called correctly
    mock_server_module.kdb_client.create_projection.assert_called_once_with(
        name="test-projection",
        query=sample_projection_code,
        emit_enabled=True,
        track_emitted_streams=True
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_projection_with_different_names(mock_server_module, sample_projection_code):
    """Test creating projections with different naming conventions."""
    projection_names = [
        "simple-projection",
        "projection_with_underscores",
        "projection.with.dots",
        "ProjectionWithCamelCase",
        "projection-123"
    ]

    for proj_name in projection_names:
        mock_server_module.kdb_client.reset_mock()

        result = await mock_server_module.create_projection(
            projection_name=proj_name,
            code=sample_projection_code
        )

        # Verify projection was created with correct name
        mock_server_module.kdb_client.create_projection.assert_called_once()
        call_args = mock_server_module.kdb_client.create_projection.call_args
        assert call_args.kwargs['name'] == proj_name


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_projection_emit_always_enabled(mock_server_module, sample_projection_code):
    """Test that emit is always enabled for created projections."""
    # Execute
    await mock_server_module.create_projection(
        projection_name="test-projection",
        code=sample_projection_code
    )

    # Assert emit_enabled is True
    call_args = mock_server_module.kdb_client.create_projection.call_args
    assert call_args.kwargs['emit_enabled'] is True
    assert call_args.kwargs['track_emitted_streams'] is True


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_projection_success(mock_server_module, sample_projection_code):
    """Test successful projection update."""
    # Execute
    result = await mock_server_module.update_projection(
        projection_name="existing-projection",
        code=sample_projection_code
    )

    # Verify client was called correctly
    mock_server_module.kdb_client.update_projection.assert_called_once_with(
        name="existing-projection",
        query=sample_projection_code,
        emit_enabled=True
    )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_update_projection_with_modified_code(mock_server_module):
    """Test updating projection with modified code."""
    # Setup
    original_code = "fromStreams('test').when({$init: function() { return {count: 0}; }})"
    updated_code = "fromStreams('test').when({$init: function() { return {count: 0, total: 0}; }})"

    # Execute
    await mock_server_module.update_projection(
        projection_name="test-projection",
        code=updated_code
    )

    # Verify updated code was passed
    call_args = mock_server_module.kdb_client.update_projection.call_args
    assert call_args.kwargs['query'] == updated_code


@pytest.mark.asyncio
@pytest.mark.unit
async def test_test_projection_returns_guidelines(mock_server_module):
    """Test that test_projection returns testing guidelines."""
    # Execute
    result = await mock_server_module.test_projection(projection_name="test-projection")

    # Assert guidelines are returned
    assert "Write test events" in result
    assert "write_events_to_stream" in result
    assert "verify" in result
    assert "$projections-test-projection-result" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_test_projection_includes_result_stream(mock_server_module):
    """Test that test_projection mentions the correct result stream."""
    # Execute
    result = await mock_server_module.test_projection(projection_name="my-projection")

    # Assert correct result stream is mentioned
    assert "$projections-my-projection-result" in result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_test_projection_with_different_names(mock_server_module):
    """Test test_projection with various projection names."""
    projection_names = [
        "order-counter",
        "user_tracker",
        "sales.aggregator"
    ]

    for proj_name in projection_names:
        result = await mock_server_module.test_projection(projection_name=proj_name)

        # Assert correct result stream for each projection
        assert f"$projections-{proj_name}-result" in result


@pytest.mark.unit
def test_get_projections_status_success(mock_server_module, sample_projection_stats):
    """Test successful retrieval of projection status."""
    # Setup
    mock_server_module.kdb_client.get_projection_statistics.return_value = sample_projection_stats

    # Execute
    result = mock_server_module.get_projections_status(projection_name="test-projection")

    # Assert
    assert "Projection: test-projection" in result
    assert "Status: Running" in result
    assert "Progress: 100.0%" in result

    # Verify client was called
    mock_server_module.kdb_client.get_projection_statistics.assert_called_once_with(
        name="test-projection"
    )


@pytest.mark.unit
def test_get_projections_status_not_found(mock_server_module):
    """Test getting status of non-existent projection."""
    # Setup
    error_msg = "Projection 'nonexistent' not found"
    mock_server_module.kdb_client.get_projection_statistics.side_effect = NotFoundError(error_msg)

    # Execute
    result = mock_server_module.get_projections_status(projection_name="nonexistent")

    # Assert
    assert "404 Projection not found" in result
    assert error_msg in result


@pytest.mark.unit
def test_get_projections_status_with_different_names(mock_server_module):
    """Test getting status for projections with different names."""
    projection_names = [
        "projection-1",
        "projection_2",
        "projection.3"
    ]

    for proj_name in projection_names:
        mock_server_module.kdb_client.reset_mock()

        # Setup mock response
        stats = type('obj', (object,), {
            'name': proj_name,
            '__str__': lambda self: f"Stats for {proj_name}"
        })()
        mock_server_module.kdb_client.get_projection_statistics.return_value = stats

        # Execute
        result = mock_server_module.get_projections_status(projection_name=proj_name)

        # Verify correct projection name was queried
        mock_server_module.kdb_client.get_projection_statistics.assert_called_once_with(
            name=proj_name
        )


@pytest.mark.asyncio
@pytest.mark.unit
async def test_projection_workflow_integration(mock_server_module, sample_projection_code, sample_projection_stats):
    """Test the complete projection workflow: build -> create -> test -> get_status."""
    # Step 1: Build projection
    build_result = await mock_server_module.build_projection(
        user_prompt="Count all events"
    )
    assert isinstance(build_result, list)
    assert len(build_result) == 2

    # Step 2: Create projection
    create_result = await mock_server_module.create_projection(
        projection_name="count-projection",
        code=sample_projection_code
    )
    assert "test projection with count-projection" in create_result

    # Step 3: Test projection
    test_result = await mock_server_module.test_projection(
        projection_name="count-projection"
    )
    assert "write_events_to_stream" in test_result
    assert "$projections-count-projection-result" in test_result

    # Step 4: Get status
    mock_server_module.kdb_client.get_projection_statistics.return_value = sample_projection_stats
    status_result = mock_server_module.get_projections_status(
        projection_name="count-projection"
    )
    assert "Projection:" in status_result


@pytest.mark.asyncio
@pytest.mark.unit
async def test_create_projection_complex_code(mock_server_module):
    """Test creating projection with complex JavaScript code."""
    complex_code = """
fromStreams('order-stream', 'payment-stream')
    .when({
        $init: function () {
            return {
                totalOrders: 0,
                totalRevenue: 0,
                ordersByStatus: {}
            }
        },
        'OrderPlaced': function (state, event) {
            state.totalOrders += 1;
            state.totalRevenue += event.data.amount;
            emit('order-stats', 'StatsUpdated', {
                totalOrders: state.totalOrders,
                totalRevenue: state.totalRevenue
            });
        },
        'OrderCancelled': function (state, event) {
            state.totalOrders -= 1;
            state.totalRevenue -= event.data.amount;
        }
    })
    .outputState()
"""

    # Execute
    result = await mock_server_module.create_projection(
        projection_name="complex-projection",
        code=complex_code
    )

    # Assert complex code was passed correctly
    call_args = mock_server_module.kdb_client.create_projection.call_args
    assert call_args.kwargs['query'] == complex_code
