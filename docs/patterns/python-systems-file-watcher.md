---
language: python
domain: systems
type: pattern
title: File system watcher with watchdog
tags: watchdog, file-watcher, inotify, fsnotify, monitoring
---

# File System Watcher with watchdog

Watch for file changes efficiently using the watchdog library. Perfect for reloading configs or triggering actions on file changes.

## Basic File Watcher

```python
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ConfigReloader(FileSystemEventHandler):
    def __init__(self, callback):
        self.callback = callback
    
    def on_modified(self, event):
        if not event.is_directory and event.src_path.endswith(".json"):
            print(f"Config changed: {event.src_path}")
            self.callback()

def watch_config(path: str, callback) -> Observer:
    """Watch a config file and call callback on change."""
    event_handler = ConfigReloader(callback)
    observer = Observer()
    observer.schedule(event_handler, path, recursive=False)
    observer.start()
    return observer

# Usage
def reload_config():
    print("Reloading configuration...")

observer = watch_config("/etc/app/", reload_config)
try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

## Watching Multiple Directories

```python
class MultiDirWatcher:
    def __init__(self):
        self.observers = []
    
    def add_watch(self, path: str, handler):
        observer = Observer()
        observer.schedule(handler, path, recursive=True)
        observer.start()
        self.observers.append(observer)
    
    def stop_all(self):
        for obs in self.observers:
            obs.stop()
        for obs in self.observers:
            obs.join()

# Usage
watcher = MultiDirWatcher()

class LogHandler(FileSystemEventHandler):
    def on_any_event(self, event):
        print(f"{event.event_type}: {event.src_path}")

watcher.add_watch("/var/log/app/", LogHandler())
watcher.add_watch("/etc/app/", LogHandler())
```

## Debouncing Changes

```python
import threading
import time

class DebouncedHandler(FileSystemEventHandler):
    def __init__(self, callback, debounce_ms: int = 500):
        self.callback = callback
        self.debounce = debounce_ms / 1000
        self.timer = None
    
    def on_any_event(self, event):
        if self.timer:
            self.timer.cancel()
        self.timer = threading.Timer(
            self.debounce,
            self.callback,
            args=[event],
        )
        self.timer.start()
```

## Event Types

```python
class DetailedHandler(FileSystemEventHandler):
    def on_created(self, event):
        print(f"Created: {event.src_path}")
    
    def on_modified(self, event):
        print(f"Modified: {event.src_path}")
    
    def on_deleted(self, event):
        print(f"Deleted: {event.src_path}")
    
    def on_moved(self, event):
        print(f"Moved: {event.src_path} -> {event.dest_path}")
```

## Integration with Flask

```python
# config_watcher.py
_watcher = None

def init_watcher(app):
    global _watcher
    
    def reload():
        app.config.from_json("/etc/app/config.json")
        print("Config reloaded")
    
    _watcher = watch_config("/etc/app/", reload)
    
    @app.teardown_appcontext
    def cleanup(exception):
        if _watcher:
            _watcher.stop()
```

This pattern enables reactive file-based workflows.