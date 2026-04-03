---
language: python
domain: systems
type: pattern
title: systemd notification protocol
tags: systemd, sd-notify, notify, readiness, service
---

# systemd Notification Protocol

Notify systemd when your service is ready, or trigger restarts on failure. The sdnotify protocol lets your service communicate with systemd.

## Basic Readiness Notification

```python
import os
import socket

NOTIFY_SOCKET = os.environ.get("NOTIFY_SOCKET")

def sd_notify(state: str, extra: str = "") -> None:
    """Send sdnotify message to systemd."""
    if not NOTIFY_SOCKET:
        return  # Not run by systemd
    
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_DGRAM)
    try:
        msg = state
        if extra:
            msg = f"{state}\n{extra}"
        sock.sendto(msg.encode(), NOTIFY_SOCKET)
    except Exception:
        pass
    finally:
        sock.close()

def notify_ready() -> None:
    """Tell systemd we're ready to serve."""
    sd_notify("READY=1")

def notify_stopping() -> None:
    """Tell systemd we're stopping."""
    sd_notify("STOPPING=1")
```

## Using in a Flask/FastAPI Server

```python
from flask import Flask

app = Flask(__name__)

@app.route("/health")
def health():
    return {"status": "ok"}

if __name__ == "__main__":
    notify_ready()
    app.run(host="127.0.0.1", port=8080)
```

## Watchdog Integration

```python
import time
import threading

def watchdog_loop(interval: int = 30) -> None:
    """Send keep-alive notifications."""
    while True:
        time.sleep(interval)
        sd_notify("WATCHDOG=1")

# Start watchdog in background thread
watchdog_thread = threading.Thread(target=watchdog_loop, daemon=True)
watchdog_thread.start()

# In systemd unit:
# [Service]
# WatchdogSec=30
# Restart=on-failure
```

## Status Updates

```python
def notify_status(status: str) -> None:
    """Update systemd about current status."""
    sd_notify("STATUS=" + status)

# Usage
notify_status("Loading configuration...")
notify_status("Connected to database")
notify_status("Ready to serve requests")
```

## Error Reporting

```python
def notify_failure(reason: str) -> None:
    """Report failure to systemd."""
    sd_notify("ERRNO=1")
    sd_notify(f"STATUS=Failed: {reason}")

# Usage
try:
    load_config()
except Exception as e:
    notify_failure(str(e))
    raise
```

## systemd Unit Configuration

```ini
[Unit]
Description=My Python Service
After=network.target

[Service]
Type=notify
ExecStart=/usr/bin/python /opt/app/main.py
WatchdogSec=30
Restart=on-failure
TimeoutStartSec=60
TimeoutStopSec=30

[Install]
WantedBy=multi-user.target
```

This pattern integrates Python services with systemd's lifecycle.