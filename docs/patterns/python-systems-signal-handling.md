---
language: python
domain: systems
type: pattern
title: Signal handling for graceful shutdown
tags: signals, shutdown, SIGTERM, SIGINT, graceful-exit
---

# Signal Handling for Graceful Shutdown

Handle SIGTERM and SIGINT to achieve clean shutdown of long-running Python services.

## Basic Signal Handler

```python
import signal
import sys
import threading

shutdown_event = threading.Event()

def signal_handler(signum, frame):
    """Handle termination signals gracefully."""
    print(f"Received signal {signum}, initiating shutdown...")
    shutdown_event.set()

# Register handlers
signal.signal(signal.SIGTERM, signal_handler)
signal.signal(signal.SIGINT, signal_handler)

# In main loop
def main():
    while not shutdown_event.is_set():
        do_work()
    print("Shutdown complete")

if __name__ == "__main__":
    main()
```

## Integration with Flask/FastAPI

```python
import signal
from flask import Flask

app = Flask(__name__)
_shutdown_event = threading.Event()

def create_shutdown_handler(app):
    def handler(signum, frame):
        print("Shutdown signal received")
        _shutdown_event.set()
        # Give server time to finish requests
        func = request.environ.get('werkzeug.server.shutdown')
        if func is not None:
            func()
    return handler

if __name__ == "__main__":
    signal.signal(signal.SIGTERM, create_shutdown_handler(app))
    signal.signal(signal.SIGINT, create_shutdown_handler(app))
    app.run()
```

## Cleanup in Context Manager

```python
import signal

class ServiceContext:
    def __init__(self):
        self._shutdown = threading.Event()
        signal.signal(signal.SIGTERM, self._handle_signal)
        signal.signal(signal.SIGINT, self._handle_signal)
    
    def _handle_signal(self, signum, frame):
        print("Received shutdown signal")
        self._shutdown.set()
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
    
    def cleanup(self):
        print("Cleaning up resources...")
        # Close database connections
        # Flush buffers
        # Stop background threads

# Usage
with ServiceContext() as service:
    service.run()
```

## Graceful Web Server Shutdown

```python
import http.server
import socketserver

class GracefulHTTPServer(socketserver.TCPServer):
    allow_reuse_address = True
    
    def shutdown(self):
        print("Stopping server...")
        super().shutdown()
        
        # Wait for active connections
        print("Waiting for clients to disconnect...")
        time.sleep(2)
        print("Server stopped")

def run_server():
    with GracefulHTTPServer(("", 8080), MyHandler) as httpd:
        signal.signal(signal.SIGTERM, lambda s, f: httpd.shutdown())
        signal.signal(signal.SIGINT, lambda s, f: httpd.shutdown())
        httpd.serve_forever()
```

## Timeout-Based Shutdown

```python
import signal

class GracefulShutdown:
    def __init__(self, timeout: int = 30):
        self.timeout = timeout
        self.shutdown_requested = threading.Event()
    
    def request_shutdown(self, signum, frame):
        print("Shutdown requested, finishing current work...")
        self.shutdown_requested.set()
        # After timeout, force exit
        signal.signal(signal.SIGALRM, self._force_exit)
        signal.alarm(self.timeout)
    
    def _force_exit(self, signum, frame):
        print("Forcing exit after timeout")
        sys.exit(1)
    
    def is_shutting_down(self) -> bool:
        return self.shutdown_requested.is_set()
```

This pattern ensures services stop cleanly without data loss.