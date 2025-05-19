import json
import os
from mcp.server.fastmcp import FastMCP
from kurrentdbclient import KurrentDBClient, StreamState, NewEvent
from kurrentdbclient.exceptions import NotFoundError

mcp = FastMCP("KurrentDB", dependencies=["kurrentdbclient", "json", "os"])

kdb_client = None

@mcp.tool()
async def read_stream(stream: str, backwards: bool =False, limit: int = 10) -> str:
    """Get streams from KurrentDB.
    If stream is not found return a 404 stream not found error and call list_streams tool.

    Args:
        stream: Input to this tool is one single word stream name that needs to be read from KurrentDB.
        KurrentDB is a NoSQL database which uses streams to store data as a series of events.
        If the stream is not found then return a 404 stream not found error.
        If another error happens return a 500 error.

        backwards: This is the read direction of the stream.
        The stream is like a queue so reading forwards reads the oldest added event first.

        limit: is the number of events to return.
    """
    try:
        events = kdb_client.get_stream(
            stream_name=stream,
            resolve_links=True,
            backwards=backwards,
            limit=limit,
        )
        result = "Start of stream: "
        for event in events:
            result += "An event of type: " + event.type + " has occurred with details: " + event.data.decode(
                "utf-8") + ". Then "
        result += " End of stream. NO FURTHER ACTION REQUIRED."
        return result
    except NotFoundError as e:
        return "404 Stream not found: " + str(e)


@mcp.tool()
async def list_streams(limit: int = 100, read_backwards: bool = True) -> str:
    """
    This function lists all streams from KurrentDB.
    Args:
        limit: number of streams to read.
        read_backwards: This is the read direction of the $streams stream. Backwards means last added first.
    """
    try:
        events = kdb_client.read_stream(
            stream_name="$streams",
            resolve_links=True,
            limit = limit,
            backwards=read_backwards
        )
        result = "STREAMS FOUND: "
        for event in events:
            result += event.stream_name + ", "
        return result
    except NotFoundError as e:
        return "$streams was not found. This could mean we have a fresh/empty database."

@mcp.tool()
async def build_projection(user_prompt: str) -> list[dict[str, str] | dict[str, str]]:
    """
    This function takes a user prompt of what they think a projection should do and then asks the LLM to build a projection in the following format.
    """
    template = f"""Use this template to write the projection based on the user prompt.
    Call create_projection to add/save the projection to KurrentDB.
    The goal of a projection is to replay events in a stream and build the current state based on the events.
    Always try to write to streams instead of keeping it in the state variable.
    Breaking down the states into different streams and rebuilding them is best practice.
    KEEP IT AS SIMPLE AS POSSIBLE.
    START OF TEMPLATE
    fromStreams(stream_name1, stream_name2, stream_name3, ...) // fromAll() to read from $all stream
        .when({{
            $init: function () {{
                return {{
                    count: 0,
                    // any other state that needs to be added. Use this for small states.
                }}
            }},
            $any: function (state, event) {{
                // code to process the event
                emit(required_eventStreamId, required_eventType, required_new_event_data_no_need_to_stringify); // writes to a stream
                linkTo('required_eventStreamId', {{type: 'required_eventType', data: required_new_event_data_no_need_to_stringify}}); // writes a linkTo event which is a pointer to an actual event
            }},
            'other event types': function (state, event) {{
                // code to process the event
            }} // NOTE THAT YOU CANNOT USE $any if you are using other event types
        }})
        .outputState()
    END OF TEMPLATE
    NEVER KEEP DATA STRUCTURES (ARRAYS, MAP, DICT etc) IN STATE that can exceed 16 MB.
    Create granular streams to keep the data instead of long streams.
    You can group the events in one stream to facilitate search by using LinkTo which creates pointers to those events.
    event.eventStreamId is the stream name of the event.
    event.eventType is the type of the event.
    event.data is already an Object and contains the data of the event.
    event.eventNumber
    state.count or state.<name> is the state of the projection that you can define.
    Replace stream_name1, stream_name2, stream_name3 with the streams that the user wants to read from.
    Replace // code to process the event with the code that the user wants to run on each event in JavaScript.
    Replace // any other state that needs to be added with the state that the user wants to add.
    """

    return [
        {
            "role": "system",
            "content": f"You are a KurrentDB projection generator. "
                       f"You will be given a user prompt and you will generate a projection "
                       f"in KurrentDB using the following template {template}."
                       f"After generating the code, call create_projection tool with the generated code."
        },
        {
            "role": "user",
            "content": f"Write a projection in KurrentDB that does the following: {user_prompt}"
        }
    ]

@mcp.tool()
async def create_projection(projection_name:str, code: str) -> str:
    """This function is called after build_projection to create the projection in KurrentDB.
    Ask the user if they are satisfied with the code first.
    Emit should always be true.
    Args:
        projection_name: A string that is the name of the projection.
        code: Code generated for the projection
    """
    kdb_client.create_projection(
        name=projection_name,
        query=code,
        emit_enabled=True,
        track_emitted_streams=True
    )
    return f"test projection with {projection_name} with test_projection tool and verify the output is correct by writing sample events and reading then back."

@mcp.tool()
async def update_projection(projection_name: str, code: str) -> str:
    """This function is called when a user wants to update a projection.
    The context is the code that the user wants to update.
    """
    kdb_client.update_projection(name=projection_name, query=code, emit_enabled=True)

@mcp.tool()
async def test_projection(projection_name: str) -> str:
    """This function is called to get guidelines to test a projection.
    Call get_projections_status to get more information about the projection.
    """
    return ("Write test events to streams by calling write_events_to_stream that are read by the projection"
            " and verify whether the output stream or state is correct."
            f"the state is kept in stream $projections-{projection_name}-result")

@mcp.tool()
def write_events_to_stream(stream: str, data: dict, event_type: str, metadata: dict) -> str:
    """Write to a stream in KurrentDB. example format of data and metadata:
        { "field" : "value", "field2" : "value2" }
    Args:
        stream: The name of the stream to write to.
        data: The data to write to the stream in JSON format.
        eventType: The type of the event to write to the stream.
        metadata: The metadata which gives additional information on the event in JSON format.
    """
    event = NewEvent(type=event_type, data=bytes(json.dumps(data), 'utf-8'),
                     content_type='application/json',
                     metadata=bytes(json.dumps(metadata), 'utf-8'))

    kdb_client.append_to_stream(
        stream_name=stream,
        events=[event],
        current_version=StreamState.ANY
    )
    return "Data written to stream: " + stream

@mcp.tool()
def get_projections_status(projection_name: str) -> str:
    """Get the status and statistics of a projection in KurrentDB.
    Args:
        projection_name: The name of the projection to get the status of.
    """
    try:
        projection = kdb_client.get_projection_statistics(name=projection_name)
        return projection.__str__()
    except NotFoundError as e:
        return "404 Projection not found: " + str(e)

if __name__ == "__main__":
    # Initialize and run the server
    kdb_client = KurrentDBClient(
        uri=os.environ["KURRENTDB_CONNECTION_STRING"]
    )
    mcp.run(transport='stdio')
