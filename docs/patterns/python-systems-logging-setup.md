---
language: python
domain: systems
type: pattern
title: Structured logging setup
tags: logging, structured-logging, json-logging, python-logging
---

# Structured Logging Setup

Replace ad-hoc logging with structured JSON logs for better parsing, searching, and analysis.

## Basic Structured Logging

```python
import logging
import json
import sys
from datetime import datetime
from typing import Any

class JSONFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        log_data = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }
        
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        
        # Add extra fields
        if hasattr(record, "extra"):
            log_data.update(record.extra)
        
        return json.dumps(log_data)

def setup_logging(level: int = logging.INFO) -> logging.Logger:
    """Configure structured logging."""
    logger = logging.getLogger()
    logger.setLevel(level)
    
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JSONFormatter())
    logger.addHandler(handler)
    
    return logger
```

## Context Variables

```python
import contextvars
from logging import LoggerAdapter

request_id_var = contextvars.ContextVar("request_id", default="")
user_id_var = contextvars.ContextVar("user_id", default="")

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.request_id = request_id_var.get()
        record.user_id = user_id_var.get()
        return True

# Add to handler
handler.addFilter(ContextFilter())

# In code
request_id_var.set("req-12345")
logger.info("Processing request")
```

## Usage

```python
logger = setup_logging()

logger.info("Request received", extra={"endpoint": "/api/users"})
logger.warning("Rate limit approaching", extra={"remaining": 10})
logger.error("Database connection failed", extra={"host": "db.example.com"})
```

## Loguru Alternative

```python
from loguru import logger

def setup_loguru():
    logger.configure(
        handlers=[
            {
                "sink": sys.stdout,
                "format": "{time:YYYY-MM-DD HH:mm:ss} | {level} | {message} | {extra}",
                "serialize": True,  # JSON output
            }
        ]
    )

# Usage
logger.bind(endpoint="/api/data", user_id="user-123").info("Request processed")
```

## File Rotation

```python
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    "app.log",
    maxBytes=10_000_000,  # 10 MB
    backupCount=5,
)
handler.setFormatter(JSONFormatter())
logger.addHandler(handler)
```

## Structured Logs Example Output

```json
{"timestamp": "2026-04-03T10:30:00Z", "level": "INFO", "logger": "api", "message": "Request received", "endpoint": "/api/users", "request_id": "req-123"}
{"timestamp": "2026-04-03T10:30:01Z", "level": "ERROR", "logger": "db", "message": "Connection failed", "host": "db.example.com", "error_code": "CONN_REFUSED"}
```

This pattern enables powerful log aggregation and analysis.