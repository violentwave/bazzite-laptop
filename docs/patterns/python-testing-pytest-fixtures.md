---
language: python
domain: testing
type: pattern
title: pytest fixtures for test isolation
tags: pytest, fixtures, test-isolation, conftest
---

# pytest Fixtures for Test Isolation

Use pytest fixtures to create isolated, reproducible test environments.

## Basic Fixtures

```python
import pytest

@pytest.fixture
def empty_db():
    """Create a fresh database for each test."""
    db = Database(":memory:")
    yield db
    db.close()

@pytest.fixture
def sample_data():
    """Provide sample data for tests."""
    return {
        "users": [
            {"id": 1, "name": "Alice"},
            {"id": 2, "name": "Bob"},
        ],
        "config": {"debug": True},
    }
```

## Fixture with Teardown

```python
import pytest
import tempfile
import shutil
from pathlib import Path

@pytest.fixture
def temp_dir():
    """Create temporary directory, clean up after."""
    tmp = tempfile.mkdtemp()
    yield Path(tmp)
    shutil.rmtree(tmp)

@pytest.fixture
def config_file(temp_dir):
    """Create a config file, clean up after."""
    config_path = temp_dir / "config.json"
    config_path.write_text('{"key": "value"}')
    yield config_path
    config_path.unlink(missing_ok=True)
```

## Session-Scoped Fixtures

```python
@pytest.fixture(scope="session")
def db_connection():
    """One connection for entire test session."""
    conn = create_connection()
    yield conn
    conn.close()

@pytest.fixture(scope="session")
def test_client():
    """Reuse test client across all tests."""
    return TestClient(app)
```

## Factory Fixtures

```python
import factory

class UserFactory(factory.Factory):
    class Meta:
        model = dict
    id = factory.Sequence(lambda n: n)
    name = factory.Faker("name")
    email = factory.LazyAttribute(lambda o: f"{o.name}@example.com")

@pytest.fixture
def user_factory():
    """Factory for creating test users."""
    return UserFactory

def test_create_user(user_factory):
    user = user_factory(name="Test User")
    assert user["name"] == "Test User"
```

## Fixtures with Parameters

```python
@pytest.fixture(params=[1, 2, 3])
def number(request):
    """Run test with each parameter."""
    return request.param

def test_numbers(number):
    assert number > 0  # Runs 3 times
```

## autouse Fixtures

```python
@pytest.fixture(autouse=True)
def reset_globals():
    """Reset global state before each test."""
    some_global_state = {}
    yield
    some_global_state.clear()
```

## Using in Tests

```python
def test_database_insert(empty_db, sample_data):
    for user in sample_data["users"]:
        empty_db.insert("users", user)
    
    assert empty_db.count("users") == 2

def test_config_loading(config_file):
    config = load_config(config_file)
    assert config["key"] == "value"
```

## Fixture Cleanup Order

```python
@pytest.fixture
def resources():
    # Setup in reverse order of teardown
    resource_a = acquire_resource_a()
    resource_b = acquire_resource_b()
    
    yield resource_a, resource_b
    
    # Teardown in reverse order
    release_resource_b(resource_b)
    release_resource_a(resource_a)
```

This pattern ensures clean, isolated test environments.