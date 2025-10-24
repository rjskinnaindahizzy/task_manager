"""
Task Management MCP Server

A simple in-memory task management system demonstrating MCP server best practices.
This server provides tools for creating, listing, updating, and completing tasks.
"""

from mcp.server.fastmcp import FastMCP
from pydantic import BaseModel, Field, field_validator, ConfigDict
from typing import Optional, List, Literal
from datetime import datetime
from pathlib import Path
import json

# Initialize MCP server
mcp = FastMCP("task_manager_mcp")

# Storage file path
STORAGE_FILE = Path.home() / ".task_manager_data.json"

# In-memory task storage
tasks_db: dict[str, dict] = {}
task_counter = 0

# Helper functions for persistence
def load_tasks():
    """Load tasks from JSON file."""
    global tasks_db, task_counter
    if STORAGE_FILE.exists():
        try:
            with open(STORAGE_FILE, 'r') as f:
                data = json.load(f)
                tasks_db = data.get("tasks", {})
                task_counter = data.get("counter", 0)
        except Exception:
            # If file is corrupt, start fresh
            tasks_db = {}
            task_counter = 0

def save_tasks():
    """Save tasks to JSON file."""
    try:
        with open(STORAGE_FILE, 'w') as f:
            json.dump({
                "tasks": tasks_db,
                "counter": task_counter
            }, f, indent=2)
    except Exception:
        pass  # Fail silently

# Load tasks on startup
load_tasks()

# Constants
MAX_TITLE_LENGTH = 200
MAX_DESCRIPTION_LENGTH = 1000
PRIORITY_EMOJI = {"high": "🔴", "medium": "🟡", "low": "🟢"}
STATUS_EMOJI = {"completed": "✓", "pending": "○"}
PRIORITY_ORDER = {"high": 0, "medium": 1, "low": 2}

# Pydantic Models for Input Validation

class StrictModel(BaseModel):
    """Base model with common configuration."""
    model_config = ConfigDict(str_strip_whitespace=True, extra='forbid')

class CreateTaskInput(StrictModel):
    """Input model for creating a new task."""
    model_config = ConfigDict(
        str_strip_whitespace=True,
        validate_assignment=True,
        extra='forbid'
    )
    
    title: str = Field(
        ...,
        description="Task title (e.g., 'Review Q4 budget', 'Fix login bug')",
        min_length=1,
        max_length=MAX_TITLE_LENGTH
    )
    description: Optional[str] = Field(
        default=None,
        description="Detailed task description",
        max_length=MAX_DESCRIPTION_LENGTH
    )
    priority: Literal["low", "medium", "high"] = Field(
        default="medium",
        description="Task priority level"
    )

class ListTasksInput(StrictModel):
    """Input model for listing tasks with optional filters."""
    
    status: Optional[Literal["pending", "completed", "all"]] = Field(
        default="all",
        description="Filter tasks by status"
    )
    priority: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="Filter tasks by priority (optional)"
    )
    format: Literal["json", "markdown"] = Field(
        default="markdown",
        description="Output format"
    )

class UpdateTaskInput(StrictModel):
    """Input model for updating an existing task."""
    
    task_id: str = Field(
        ...,
        description="ID of the task to update (e.g., 'task-1', 'task-42')"
    )
    title: Optional[str] = Field(
        default=None,
        description="New task title",
        max_length=MAX_TITLE_LENGTH
    )
    description: Optional[str] = Field(
        default=None,
        description="New task description",
        max_length=MAX_DESCRIPTION_LENGTH
    )
    priority: Optional[Literal["low", "medium", "high"]] = Field(
        default=None,
        description="New priority level"
    )

class CompleteTaskInput(StrictModel):
    """Input model for marking a task as completed."""
    task_id: str = Field(
        ...,
        description="ID of the task to complete (e.g., 'task-1', 'task-42')"
    )

class DeleteTaskInput(StrictModel):
    """Input model for deleting a task."""
    task_id: str = Field(
        ...,
        description="ID of the task to delete (e.g., 'task-1', 'task-42')"
    )

# Helper functions

def get_task_or_error(task_id: str) -> tuple[dict | None, str | None]:
    """Returns (task, None) or (None, error_message)."""
    if task_id not in tasks_db:
        return None, f"✗ Task '{task_id}' not found"
    return tasks_db[task_id], None

def filter_tasks(status: str | None, priority: str | None) -> list[dict]:
    """Apply status and priority filters to tasks."""
    return [
        task for task in tasks_db.values()
        if (status == "all" or task["status"] == status)
        and (priority is None or task["priority"] == priority)
    ]

# Tool Implementations

@mcp.tool(
    name="create_task",
    annotations={
        "title": "Create New Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": False,
        "openWorldHint": False
    }
)
async def create_task(params: CreateTaskInput) -> str:
    """Create a new task in the task management system.
    
    This tool creates a new task with a unique ID and sets its initial status to 'pending'.
    All tasks are created with a timestamp and can be filtered or updated later.
    
    Args:
        params (CreateTaskInput): Task creation parameters including:
            - title (str): Brief task title
            - description (Optional[str]): Detailed description
            - priority (str): Priority level - 'low', 'medium', or 'high'
    
    Returns:
        str: JSON response containing the created task with its assigned ID
    
    Example:
        Create a high-priority task:
        {"title": "Review security audit", "priority": "high"}
    """
    global task_counter
    
    task_counter += 1
    task_id = f"task-{task_counter}"
    
    task = {
        "id": task_id,
        "title": params.title,
        "description": params.description or "",
        "priority": params.priority,
        "status": "pending",
        "created_at": datetime.now().isoformat(),
        "completed_at": None
    }
    
    tasks_db[task_id] = task
    save_tasks()

    priority_emoji = PRIORITY_EMOJI[task["priority"]]
    return f"✓ Created task {task_id}: {task['title']} ({priority_emoji} {task['priority']})"

@mcp.tool(
    name="list_tasks",
    annotations={
        "title": "List Tasks",
        "readOnlyHint": True,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def list_tasks(params: ListTasksInput) -> str:
    """List all tasks with optional filtering by status and priority.
    
    This tool retrieves tasks from the system and can filter by status (pending/completed/all)
    and priority level. Results can be returned in JSON or Markdown format.
    
    Args:
        params (ListTasksInput): Filtering and formatting options:
            - status (Optional[str]): Filter by 'pending', 'completed', or 'all'
            - priority (Optional[str]): Filter by 'low', 'medium', or 'high'
            - format (str): Output format - 'json' or 'markdown'
    
    Returns:
        str: Formatted list of tasks matching the filters
    
    Example:
        List all pending high-priority tasks:
        {"status": "pending", "priority": "high", "format": "markdown"}
    """
    filtered_tasks = filter_tasks(params.status, params.priority)

    if not filtered_tasks:
        return "No tasks found."

    # Sort by priority (high > medium > low) and then by creation date
    filtered_tasks.sort(key=lambda x: (PRIORITY_ORDER[x["priority"]], x["created_at"]))

    if params.format == "json":
        return json.dumps({
            "total_count": len(filtered_tasks),
            "tasks": filtered_tasks
        }, indent=2)

    # Clean markdown format
    lines = []
    for task in filtered_tasks:
        status_emoji = STATUS_EMOJI[task["status"]]
        priority_emoji = PRIORITY_EMOJI[task["priority"]]

        task_line = f"{status_emoji} [{task['id']}] {task['title']} ({priority_emoji} {task['priority']})"
        lines.append(task_line)

        if task["description"]:
            lines.append(f"   {task['description']}")

    header = f"Tasks ({len(filtered_tasks)} total)"
    return f"{header}\n" + "\n".join(lines)

@mcp.tool(
    name="update_task",
    annotations={
        "title": "Update Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def update_task(params: UpdateTaskInput) -> str:
    """Update an existing task's properties.
    
    This tool allows updating the title, description, or priority of an existing task.
    Only the specified fields will be updated; others remain unchanged.
    
    Args:
        params (UpdateTaskInput): Update parameters:
            - task_id (str): ID of the task to update
            - title (Optional[str]): New title
            - description (Optional[str]): New description
            - priority (Optional[str]): New priority level
    
    Returns:
        str: JSON response with the updated task or error message
    
    Example:
        Update task priority:
        {"task_id": "task-1", "priority": "high"}
    
    Error Handling:
        Returns clear error message if task_id doesn't exist.
        Suggests using list_tasks to see available task IDs.
    """
    task, error = get_task_or_error(params.task_id)
    if error:
        return error

    # Update only specified fields
    updates = []
    if params.title is not None:
        task["title"] = params.title
        updates.append(f"title → '{params.title}'")
    if params.description is not None:
        task["description"] = params.description
        updates.append("description updated")
    if params.priority is not None:
        task["priority"] = params.priority
        priority_emoji = PRIORITY_EMOJI[params.priority]
        updates.append(f"priority → {priority_emoji} {params.priority}")

    update_str = ", ".join(updates) if updates else "no changes"
    save_tasks()
    return f"✓ Updated {params.task_id}: {update_str}"

@mcp.tool(
    name="complete_task",
    annotations={
        "title": "Complete Task",
        "readOnlyHint": False,
        "destructiveHint": False,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def complete_task(params: CompleteTaskInput) -> str:
    """Mark a task as completed.
    
    This tool changes a task's status to 'completed' and records the completion timestamp.
    If the task is already completed, the operation is idempotent (no changes made).
    
    Args:
        params (CompleteTaskInput): Completion parameters:
            - task_id (str): ID of the task to mark as completed
    
    Returns:
        str: JSON response confirming completion or error message
    
    Example:
        Complete a task:
        {"task_id": "task-1"}
    
    Error Handling:
        Returns error if task doesn't exist with suggestion to list tasks.
    """
    task, error = get_task_or_error(params.task_id)
    if error:
        return error

    if task["status"] == "completed":
        return f"✓ Task {params.task_id} already completed"

    task["status"] = "completed"
    task["completed_at"] = datetime.now().isoformat()
    save_tasks()

    return f"✓ Completed {params.task_id}: {task['title']}"

@mcp.tool(
    name="delete_task",
    annotations={
        "title": "Delete Task",
        "readOnlyHint": False,
        "destructiveHint": True,
        "idempotentHint": True,
        "openWorldHint": False
    }
)
async def delete_task(params: DeleteTaskInput) -> str:
    """Delete a task permanently.

    This tool removes a task from the system entirely. This operation cannot be undone.

    Args:
        params (DeleteTaskInput): Deletion parameters:
            - task_id (str): ID of the task to delete

    Returns:
        str: Confirmation message or error message

    Example:
        Delete a task:
        {"task_id": "task-1"}

    Error Handling:
        Returns error if task doesn't exist.
    """
    task, error = get_task_or_error(params.task_id)
    if error:
        return error

    task_title = task["title"]
    del tasks_db[params.task_id]
    save_tasks()

    return f"✗ Deleted {params.task_id}: {task_title}"

# Run the server
if __name__ == "__main__":
    mcp.run()
