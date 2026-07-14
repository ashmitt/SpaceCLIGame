import logging
from typing import Callable, Dict, List, Tuple

from src.event.models import Event

logger = logging.getLogger("ColonyOS.EventBus")


class EventBus:
    _instance = None
    _subscribers: Dict[str, List[Tuple[int, Callable[[Event], None]]]] = {}

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(EventBus, cls).__new__(cls)
        return cls._instance

    def subscribe(
        self, event_type: str, callback: Callable[[Event], None], priority: int = 3
    ) -> None:
        """
        Registers a callback to receive events of a specific type.
        Priority is sorted ascending (1 = highest priority, executes first).
        """
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []

        # Check if already subscribed to avoid duplicate callbacks
        for _, cb in self._subscribers[event_type]:
            if cb == callback:
                return

        self._subscribers[event_type].append((priority, callback))
        # Sort subscribers by priority ascending
        self._subscribers[event_type].sort(key=lambda x: x[0])
        logger.debug(f"Subscribed callback to '{event_type}' with priority {priority}")

    def unsubscribe(self, event_type: str, callback: Callable[[Event], None]) -> None:
        if event_type in self._subscribers:
            self._subscribers[event_type] = [
                item for item in self._subscribers[event_type] if item[1] != callback
            ]

    def publish(self, event: Event) -> None:
        """Publishes an event and dispatches it to subscribers in priority order."""
        event_type = event.event_type
        logger.debug(f"Publishing event '{event_type}' from '{event.publisher}'")

        # Dispatch to specific subscribers
        if event_type in self._subscribers:
            for priority, handler in self._subscribers[event_type]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(
                        f"Error executing event handler for type '{event_type}': {e}", exc_info=True
                    )

        # Dispatch to wildcard subscribers if any (using '*')
        if "*" in self._subscribers:
            for priority, handler in self._subscribers["*"]:
                try:
                    handler(event)
                except Exception as e:
                    logger.error(f"Error executing wildcard handler: {e}", exc_info=True)

    def clear(self) -> None:
        """Clears all subscribers."""
        self._subscribers.clear()
