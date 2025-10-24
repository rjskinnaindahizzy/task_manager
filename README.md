# Task Manager MCP Server

This repository contains a minimal [Minimal Control Protocol (MCP)](https://github.com/model-context-protocol) server that demonstrates best practices for building typed, documentable tools with `FastMCP`. It exposes a simple in-memory task tracker that persists to disk between runs and can be called from any MCP-compatible client.

## Features
- Create new tasks with optional descriptions and low/medium/high priority levels.
- List tasks with filters for status and priority, returning either JSON or Markdown output.
- Update titles, descriptions, or priorities on existing tasks.
- Mark tasks as completed and capture completion timestamps.
- Delete tasks, with all data persisted to `~/.task_manager_data.json`.

## Requirements
- Python 3.10 or newer.
- Python packages: `mcp` (provides `FastMCP`) and `pydantic`.

```bash
python -m venv .venv
source .venv/bin/activate
pip install mcp pydantic
```

## Running the server
```bash
python task_manager_mcp.py
```

On startup the server loads any existing tasks from `~/.task_manager_data.json` and registers the tools listed below. Connect to it using your preferred MCP client (e.g., Claude Desktop or another MCP-aware agent) and target the server named `task_manager_mcp`.

## Available tools
| Tool | Description | Key parameters |
| --- | --- | --- |
| `create_task` | Create a pending task with a unique ID. | `title` (required), optional `description`, `priority` (`low`/`medium`/`high`, defaults to `medium`). |
| `list_tasks` | Retrieve tasks with optional filters. Returns Markdown by default or JSON when requested. | `status` (`pending`/`completed`/`all`), `priority` (`low`/`medium`/`high`), `format` (`markdown` or `json`). |
| `update_task` | Modify a task's title, description, or priority. | `task_id` plus any fields to update. |
| `complete_task` | Mark a task as completed and record the timestamp. | `task_id`. |
| `delete_task` | Permanently remove a task. | `task_id`. |

Each tool validates input with Pydantic models, returning concise success or error messages. If a task cannot be found, the server suggests listing tasks to discover valid IDs.

## Data persistence
- Tasks are stored in memory while the process runs and saved to `~/.task_manager_data.json` after any modification.
- The JSON file tracks both the task metadata and the auto-incrementing counter used for task IDs.
- Delete the file to reset the server state.

## Development notes
- Tasks are sorted by priority (high → low) and creation time when listed.
- Markdown responses include emoji markers for status and priority to improve readability in chat-based clients.
- The server is designed to be idempotent where appropriate (`list_task`, `complete_task`, and `delete_task` gracefully handle repeated calls).

Feel free to fork this project and adapt the tools or storage layer to suit your own MCP integrations.
