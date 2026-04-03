---
language: python
domain: testing
type: pattern
title: Temporary path fixtures with pytest
tags: pytest, tmp-path, temporary-directory, test-fixtures, tmpdir
---

# Temporary Path Fixtures with pytest

Use pytest's built-in temporary path fixtures for clean filesystem test isolation.

## Built-in tmp_path Fixture

```python
import pytest
from pathlib import Path

def test_create_file(tmp_path):
    """tmp_path is a Path object to a temporary directory."""
    file_path = tmp_path / "test.txt"
    file_path.write_text("test content")
    
    assert file_path.exists()
    assert file_path.read_text() == "test content"

def test_create_directory(tmp_path):
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    
    (subdir / "file.txt").write_text("data")
    assert (subdir / "file.txt").exists()
```

## tmpdir Fixture (Legacy)

```python
def test_using_tmpdir(tmpdir):
    # tmpdir is a py.path.local object
    path = tmpdir.join("test.txt")
    path.write("content")
    assert path.read() == "content"
```

## Multiple Temporary Directories

```python
def test_multiple_paths(tmp_path):
    input_dir = tmp_path / "input"
    output_dir = tmp_path / "output"
    input_dir.mkdir()
    output_dir.mkdir()
    
    (input_dir / "data.txt").write_text("test")
    
    process_files(input_dir, output_dir)
    
    assert (output_dir / "data.txt").exists()
```

## tmp_path_factory for Session-Scoped Paths

```python
@pytest.fixture(scope="session")
def shared_dir(tmp_path_factory):
    """Create a directory for the entire test session."""
    return tmp_path_factory.mktemp("shared")

def test_session_fixture(shared_dir):
    (shared_dir / "data.txt").write_text("shared data")
    assert (shared_dir / "data.txt").exists()
```

## tmp_path with Configuration

```python
def test_config_file(tmp_path):
    config = tmp_path / "config.json"
    config.write_text('{"debug": true}')
    
    app_config = load_config(config)
    assert app_config["debug"] is True
```

## Database Test with tmp_path

```python
import sqlite3

def test_database_operations(tmp_path):
    db_path = tmp_path / "test.db"
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE test (id INTEGER, value TEXT)")
    cursor.execute("INSERT INTO test VALUES (1, 'test')")
    conn.commit()
    
    cursor.execute("SELECT * FROM test")
    result = cursor.fetchone()
    
    assert result == (1, "test")
    conn.close()
```

## Cleanup Verification

```python
def test_cleanup_works(tmp_path):
    file = tmp_path / "temp.txt"
    file.write_text("will be cleaned")
    
    # File exists during test
    assert file.exists()

# After test completes, tmp_path is automatically cleaned up
```

## Custom tmp_path Fixture

```python
import pytest

@pytest.fixture
def mock_home(tmp_path):
    """Create a mock home directory structure."""
    home = tmp_path / "home"
    home.mkdir()
    (home / ".config").mkdir()
    (home / ".cache").mkdir()
    return home
```

This pattern provides clean filesystem isolation for tests.