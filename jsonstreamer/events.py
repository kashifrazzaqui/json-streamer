"""
Simple event system to replace the 'again' library dependency.
Provides EventSource class for event listener registration and firing.
"""

from collections import defaultdict
from typing import Any, Callable, Dict, List, Optional


class EventSource:
    """Base class providing event listener management and firing capabilities"""

    def __init__(self):
        """Initialize the event source with empty listener dictionaries"""
        self._listeners: Dict[str, List[Callable]] = defaultdict(list)
        self._catch_all_listeners: List[Callable] = []

    def add_listener(self, event: str, listener: Callable) -> None:
        """Add a listener for a specific event

        Args:
            event: The event name to listen for
            listener: The callable to invoke when the event fires
        """
        if listener not in self._listeners[event]:
            self._listeners[event].append(listener)

    def remove_listener(self, listener: Callable) -> None:
        """Remove a listener from all events

        Args:
            listener: The listener callable to remove
        """
        for event_listeners in self._listeners.values():
            if listener in event_listeners:
                event_listeners.remove(listener)

        if listener in self._catch_all_listeners:
            self._catch_all_listeners.remove(listener)

    def add_catch_all_listener(self, listener: Callable) -> None:
        """Add a listener that receives ALL events

        Args:
            listener: The callable to invoke for all events.
                     Must accept (event_name, *args) signature
        """
        if listener not in self._catch_all_listeners:
            self._catch_all_listeners.append(listener)

    def remove_catch_all_listener(self, listener: Callable) -> None:
        """Remove a catch-all listener

        Args:
            listener: The listener to remove
        """
        if listener in self._catch_all_listeners:
            self._catch_all_listeners.remove(listener)

    def auto_listen(self, observer: Any, prefix: str = "_on_") -> None:
        """Automatically attach methods from observer that match naming convention

        Finds all methods in observer whose names start with prefix followed by
        an event name, and automatically registers them as listeners.

        For example, if prefix="_on_" and observer has a method "_on_start",
        it will be registered as a listener for the "start" event.

        Args:
            observer: Object containing listener methods
            prefix: Method name prefix to search for (default: "_on_")
        """
        for attr_name in dir(observer):
            if attr_name.startswith(prefix):
                event_name = attr_name[len(prefix) :]
                attr = getattr(observer, attr_name)
                if callable(attr):
                    self.add_listener(event_name, attr)

    def fire(self, event: str, *args: Any) -> None:
        """Fire an event to all registered listeners

        Args:
            event: The event name to fire
            *args: Arguments to pass to the listeners
        """
        # Fire to specific event listeners
        for listener in self._listeners.get(event, []):
            listener(*args)

        # Fire to catch-all listeners with event name as first parameter
        for listener in self._catch_all_listeners:
            listener(event, *args)

    def clear_listeners(self, event: Optional[str] = None) -> None:
        """Clear listeners for a specific event or all events

        Args:
            event: Event name to clear listeners for. If None, clears all listeners.
        """
        if event is None:
            self._listeners.clear()
            self._catch_all_listeners.clear()
        else:
            self._listeners[event].clear()
