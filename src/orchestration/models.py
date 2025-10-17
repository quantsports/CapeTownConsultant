"""
Orchestration models
Data models for multi-agent system
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional


class AgentStatus(Enum):
    """Agent lifecycle status"""

    IDLE = "idle"
    BUSY = "busy"
    INITIALIZING = "initializing"
    ERROR = "error"
    STOPPED = "stopped"


class AgentCapability(Enum):
    """Agent capabilities"""

    RESEARCH = "research"  # Web search, information gathering
    ANALYSIS = "analysis"  # Data analysis, synthesis
    WRITING = "writing"  # Content generation
    MEMORY = "memory"  # Knowledge storage/retrieval
    COORDINATION = "coordination"  # Multi-agent orchestration
    GENERAL = "general"  # General-purpose tasks


class TaskPriority(Enum):
    """Task priority levels"""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class TaskStatus(Enum):
    """Task execution status"""

    PENDING = "pending"
    ASSIGNED = "assigned"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AgentMetadata:
    """Metadata for an agent"""

    agent_id: str
    name: str
    capabilities: List[AgentCapability]
    status: AgentStatus
    created_at: datetime
    last_active: datetime
    tasks_completed: int = 0
    tasks_failed: int = 0
    total_cost: float = 0.0
    current_task_id: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "capabilities": [c.value for c in self.capabilities],
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "last_active": self.last_active.isoformat(),
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "total_cost": self.total_cost,
            "current_task_id": self.current_task_id,
        }


@dataclass
class Task:
    """A task to be executed by an agent"""

    task_id: str
    description: str
    required_capabilities: List[AgentCapability]
    priority: TaskPriority
    created_at: datetime
    status: TaskStatus
    assigned_agent_id: Optional[str] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    parent_task_id: Optional[str] = None  # For hierarchical tasks
    user_id: str = "default"
    max_retries: int = 3
    retry_count: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "description": self.description,
            "required_capabilities": [c.value for c in self.required_capabilities],
            "priority": self.priority.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "assigned_agent_id": self.assigned_agent_id,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": (
                self.completed_at.isoformat() if self.completed_at else None
            ),
            "result": self.result,
            "error": self.error,
            "parent_task_id": self.parent_task_id,
            "user_id": self.user_id,
            "retry_count": self.retry_count,
            "metadata": self.metadata,
        }


@dataclass
class WorkResult:
    """Result from a worker agent"""

    task_id: str
    agent_id: str
    success: bool
    result: Any
    error: Optional[str] = None
    cost: float = 0.0
    duration_seconds: float = 0.0
    citations: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "task_id": self.task_id,
            "agent_id": self.agent_id,
            "success": self.success,
            "result": self.result,
            "error": self.error,
            "cost": self.cost,
            "duration_seconds": self.duration_seconds,
            "citations": self.citations,
            "metadata": self.metadata,
        }
