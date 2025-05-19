# MCP Server
Expose stream data to the MCP Client. This is a simple MCP tool to explore data in KurrentDB.

## Recommended Usage
- Claude Desktop
- Sequential Thinking MCP for complex tasks

## Installation
You need to enable --run-projections=all and --start-standard-projections on KurrentDB
The $streams stream is used to look for available streams.

```json
{
    "servers": {
      "KurrentDB": {
        "type": "stdio",
        "command": "uv",
            "args": [
                "--directory",
                "path to mcp-server folder",
                "run",
                "server.py"
            ],
	    "env": {
             "KURRENTDB_CONNECTION_STRING": "insert kurrentdb connection here"
        }
      },
      "sequential-thinking": {
        "command": "npx",
        "args": [
          "-y",
          "@modelcontextprotocol/server-sequential-thinking"
        ]
      }
    }
  }
```
## Overview
This MCP server is designed to make stream data available to the MCP client. 
It provides a simple interface for querying and retrieving stream data.
It can also create, test and debug projections.

Access control is done using the KurrentDB connection string provided at configuration time as an environment variable.

## Components

### Tools
The servers exposes 8 tool calls:
1. `read_stream`
2. `list_streams`
3. `build_projection`
4. `create_projection`
5. `update_projection`
6. `test_projection`
7. `write_events_to_stream`
8. `get_projections_status`

### Configuration

- ConnectionString: This is a KurrentDB connection string which includes user credentials. Depending on the client being used, this can come from environment variable or a JSON Configuration file like in Claude Desktop's case.