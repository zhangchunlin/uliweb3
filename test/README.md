# Uliweb3 Test Suite Guide & Setup Instructions

Welcome to the test suite of the `uliweb3` library! This directory contains comprehensive unit tests, integration tests, and doctests ensuring the framework's stability, ASGI asynchronous capabilities, and transaction integrity.

---

## 🚀 How to Run the Tests

You can execute the test suite using either of the following standard Python test runners:

### Option 1: Legacy Runner (Nose)
Uliweb's legacy test suite can be run using `nosetests` with the doctest plugin enabled:
```bash
# 在仓库根目录执行（不要在 test/ 内跑，避免相对路径/导入问题）
nosetests --with-doc test
```

### Option 2: Modern Runner (Pytest)
For modern development, you can use `pytest`:
```bash
# 在仓库根目录执行
pytest test/
```

---

## 🛠️ Dependencies & Running Services

To run the complete test suite without skips, failures, or connection errors, the following dependencies and services must be prepared:

### 1. Redis Service (Required for Weto/Cache Doctests)
Some cache-related doctests (`test_cache.test_redis`) verify redis storage backend functionality. These tests expect a running Redis server on `localhost:6379`.

If Redis is not running, you will encounter `ConnectionRefusedError: [Errno 111] Connection refused` errors.

**To start Redis:**
- **Using Docker (Recommended & Cleanest):**
  ```bash
  docker run -d --name uliweb-redis -p 127.0.0.1:6379:6379 dockerhub.mot.com/redis
  ```
- **Using System Package Manager (Ubuntu/Linux):**
  ```bash
  sudo apt-get install redis-server
  sudo systemctl start redis-server
  ```

### 2. Setuptools and `pkg_resources` (Test Isolation)
In Python 3.10 and 3.11+, modern versions of `setuptools` (v70.0.0+) have completely removed the legacy `pkg_resources` module, which causes older packaging tests to raise `ModuleNotFoundError`.
- **Framework Solution**: The test suite (`test_staticfiles.py`) has been upgraded to automatically detect if `pkg_resources` is missing, and will gracefully skip the `test_pkg_resources_static_file` test using `unittest.SkipTest` instead of crashing.
- **To Run it (Optional)**: If you explicitly want to run and test `pkg_resources` static files resolution, you can install an older compatible version of setuptools:
  ```bash
  pip install "setuptools<70.0.0"
  ```

---

## 🔒 Synchronous ORM Transaction Thread Wrapper

Uliweb3 supports asynchronous (ASGI) dispatching. When a synchronous view (`def` view) is dispatched, the framework delegates its execution to a thread pool executor (`loop.run_in_executor`). 

Because database connections and SQLAlchemy Sessions are bound to `threading.local()`, the standard main-thread ASGI transaction middleware cannot commit or rollback database operations performed in these child thread contexts, risking transaction or SQLite write lock leaks.

To solve this, we introduced the framework-level transaction wrapper (`sync_orm_wrapper` inside `uliweb/core/SimpleFrame.py`), which:
1. Wraps all synchronous handler execution in a dedicated execution context on the child thread.
2. Automatically commits all pending ORM transactions (`CommitAll()`) on successful execution.
3. Automatically rolls back all ORM transactions (`RollbackAll()`) on exceptions.

### Verifying the Transaction Handler
We have integrated native test cases validating this transaction safety model within:
`test_async_dispatcher.py`

You can run these specific tests to verify transaction safety:
```bash
# Run using nosetests
nosetests --with-doctest test_async_dispatcher.py

# Run using pytest
pytest test_async_dispatcher.py
```
Both test runners will execute the tests, verifying transaction commitment and rollbacks cleanly and robustly.
