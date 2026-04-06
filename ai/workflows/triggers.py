"""Event triggers for workflows."""

import asyncio
import logging
from collections.abc import Callable

logger = logging.getLogger("ai.workflows")

try:
    import watchdog
    from watchdog.observers import Observer
except ImportError:
    watchdog = None
    Observer = None


class FileWatcher:
    """Watch files for changes using watchdog."""

    def __init__(self, paths: list[str], callback: Callable):
        self.paths = paths
        self.callback = callback
        self._observer: Observer | None = None
        self._handlers = []

    def start(self) -> None:
        """Start watching files."""
        if watchdog is None:
            logger.warning("watchdog not installed, file watching disabled")
            return

        self._observer = Observer()

        for path in self.paths:
            from watchdog.events import FileSystemEventHandler

            class Handler(FileSystemEventHandler):
                def __init__(self, cb):
                    self.cb = cb

                def on_modified(self, event):
                    if not event.is_directory:
                        self.cb(event.src_path)

            handler = Handler(self.callback)
            self._handlers.append(handler)
            self._observer.schedule(handler, path, recursive=True)

        self._observer.start()
        logger.info(f"FileWatcher started for {self.paths}")

    def stop(self) -> None:
        """Stop watching files."""
        if self._observer:
            self._observer.stop()
            self._observer.join()
            logger.info("FileWatcher stopped")


class EventBus:
    """Simple asyncio-based event bus."""

    def __init__(self):
        self._subscribers: dict[str, list[Callable]] = {}
        self._queue: asyncio.Queue = asyncio.Queue()
        self._running = False
        self._task: asyncio.Task | None = None

    def subscribe(self, event_type: str, handler: Callable) -> None:
        """Subscribe to an event type."""
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(handler)

    def publish(self, event_type: str, data: dict) -> None:
        """Publish an event."""
        self._queue.put_nowait({"type": event_type, "data": data})

    async def _consumer(self) -> None:
        """Consume events from the queue."""
        while self._running:
            try:
                event = await asyncio.wait_for(self._queue.get(), timeout=1.0)
                handlers = self._subscribers.get(event["type"], [])
                for handler in handlers:
                    try:
                        if asyncio.iscoroutinefunction(handler):
                            await handler(event["data"])
                        else:
                            handler(event["data"])
                    except Exception as e:
                        logger.error(f"Event handler error: {e}")
            except TimeoutError:
                continue

    def start(self) -> None:
        """Start the event bus consumer."""
        if self._running:
            return

        self._running = True
        self._task = asyncio.create_task(self._consumer())
        logger.info("EventBus started")

    async def stop(self) -> None:
        """Stop the event bus consumer."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("EventBus stopped")
