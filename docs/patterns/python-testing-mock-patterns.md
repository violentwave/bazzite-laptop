---
language: python
domain: testing
type: pattern
title: Mock patterns with unittest.mock
tags: unittest.mock, mocking, patch, mock-object, testing
---

# Mock Patterns with unittest.mock

Isolate code under test by mocking external dependencies.

## Basic Patching

```python
from unittest.mock import patch, MagicMock

# Patch a function
@patch("module.function_name")
def test_function(mock_fn):
    mock_fn.return_value = "mocked"
    result = my_function()
    assert result == "mocked"
    mock_fn.assert_called_once()

# Patch a class
@patch("module.ClassName")
def test_class(mock_cls):
    instance = MagicMock()
    mock_cls.return_value = instance
    instance.method.return_value = "result"
    
    obj = my_class_creator()
    assert obj.method() == "result"
```

## Mocking External APIs

```python
from unittest.mock import patch, Mock
import requests

@patch("requests.get")
def test_api_call(mock_get):
    mock_response = Mock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"key": "value"}
    mock_get.return_value = mock_response
    
    result = fetch_data("http://api.example.com")
    assert result == {"key": "value"}
```

## Side Effects

```python
from unittest.mock import Mock

def side_effect_function(arg):
    if arg == "error":
        raise ConnectionError("Network error")
    return f"processed_{arg}"

mock_fn = Mock(side_effect=side_effect_function)

# Test success
assert mock_fn("ok") == "processed_ok"

# Test error handling
with pytest.raises(ConnectionError):
    mock_fn("error")
```

## Mocking Context Managers

```python
from unittest.mock import mock_open, patch

# Mock file operations
def test_read_file():
    m = mock_open(read_data="file content")
    
    with patch("builtins.open", m):
        content = read_file("test.txt")
        assert content == "file content"

# Mock database connections
@patch("module.Database")
def test_db_query(mock_db):
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = [(1, "test")]
    
    mock_conn.cursor.return_value = mock_cursor
    mock_db.return_value = mock_conn
    
    result = query_data("SELECT * FROM users")
    assert len(result) == 1
```

## Property Mock

```python
from unittest.mock import PropertyMock

class MockResponse:
    status_code = 200
    text = "response"

@patch("module.requests.get")
def test_response_property(mock_get):
    mock_get.return_value = MockResponse()
    
    response = get_response()
    assert response.status_code == 200
```

## Async Mocking

```python
import asyncio
from unittest.mock import AsyncMock

async def test_async():
    async_mock = AsyncMock(return_value="async result")
    
    result = await async_mock()
    assert result == "async result"

# Mocking async context manager
class AsyncContextManager:
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, *args):
        pass

async def test_async_cm():
    mock_cm = AsyncMock(return_value=AsyncContextManager())
    mock_cm.__aenter__ = AsyncMock(return_value="entered")
    mock_cm.__aexit__ = AsyncMock(return_value=None)
```

## Verification

```python
from unittest.mock import call

mock = MagicMock()

# Call multiple times
mock("a")
mock("b")
mock("c")

# Verify calls
assert mock.call_count == 3
mock.assert_called_once()  # Fails - called 3 times

# Check call args
mock.assert_called_with("a")
assert mock.call_args_list == [call("a"), call("b"), call("c")]
```

This pattern enables testing without external dependencies.