"""In-memory circular buffer for recent conversation turns."""

from collections import deque
from dataclasses import dataclass, field


@dataclass
class Turn:
    """A single conversation turn."""

    role: str
    content: str
    metadata: dict = field(default_factory=dict)


class TurnBuffer:
    """Fixed-size circular buffer of recent conversation turns."""

    def __init__(self, maxsize: int = 20) -> None:
        self._buffer: deque[Turn] = deque(maxlen=maxsize)

    def add(self, role: str, content: str, metadata: dict | None = None) -> None:
        self._buffer.append(Turn(role=role, content=content, metadata=metadata or {}))

    def get_all(self) -> list[Turn]:
        return list(self._buffer)

    def to_messages(self) -> list[dict[str, str]]:
        return [{"role": t.role, "content": t.content} for t in self._buffer]

    def clear(self) -> None:
        self._buffer.clear()

    def __len__(self) -> int:
        return len(self._buffer)
