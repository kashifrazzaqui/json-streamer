# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2025-01-XX (Unreleased)

### 🎉 Major Modernization Release

This release represents a comprehensive modernization and improvement of json-streamer,
making it compatible with modern Python versions (3.8-3.13) and adding numerous
safety and usability features.

### Added

- **Python 3.11+ Compatibility**: Replaced deprecated `again` library with built-in event system
  - Custom `events.EventSource` class with 100% API compatibility
  - Full type hints throughout the event system
  - No external dependencies for event handling

- **Context Manager Support** (`with` statement):
  ```python
  with JSONStreamer() as streamer:
      streamer.consume(data)
  # Automatically calls close() - prevents memory leaks!
  ```

- **Configurable Safety Limits**:
  - `max_depth`: Prevent stack overflow from deeply nested JSON
  - `max_string_size`: Prevent memory exhaustion from huge strings
  - `buffer_size`: Configurable chunk size for parsing (default: 65536)

- **Comprehensive Type Hints**:
  - Full type annotations in all modules (`tape.py`, `yajl/parse.py`, `jsonstreamer.py`, `events.py`)
  - Better IDE autocomplete and error detection
  - mypy-compatible type checking

- **Modern Packaging**:
  - `pyproject.toml` with full PEP 621 compliance
  - `uv` support for fast dependency management
  - Comprehensive package metadata and classifiers

- **Enhanced Documentation**:
  - Extensive docstrings on all public methods
  - Usage examples in docstrings
  - Type hints for all parameters and return values

- **14 New Tests**:
  - Safety limit validation (max_depth, max_string_size)
  - Context manager functionality
  - Negative number parsing
  - Invalid JSON handling
  - Buffer size configuration
  - Total: 25 tests (was 11)

### Fixed

- **Critical Bug Fixes**:
  - ❌ **6 `is` vs `==` comparisons** with integer literals (lines 257, 258, 262, 263, 305, 311)
    - `if len(stack) is 0:` → `if len(stack) == 0:`
    - Prevents subtle bugs due to Python integer caching behavior

  - ❌ **`type()` instead of `isinstance()`** (line 275)
    - `if type(obj) is list:` → `if isinstance(obj, list):`
    - More Pythonic and handles subclasses correctly

  - ❌ **Negative number parsing bug** (line 149)
    - `-123.isdigit()` returns `False`, causing negative integers to be parsed as floats
    - Now correctly handles: `-123` → `int`, `-123.45` → `float`

  - ❌ **Exception handling** in nested exceptions
    - Improved `JSONStreamerException.__str__()` to handle wrapped exceptions

### Changed

- **Breaking Changes**:
  - Removed `again` library dependency
  - Replaced `ctypes` with `cffi` for C bindings (more robust, better error handling)
  - Minimum Python version: 3.8 (was 3.4)
  - Version bumped to 2.0.0 due to dependency changes

- **Implementation Improvements**:
  - Migrated from ctypes to cffi for yajl bindings
  - Better callback management (prevents garbage collection issues)
  - Improved error messages from C library
  - Bundled wheels with yajl included (no system dependencies!)

- **API Enhancements** (Backward Compatible):
  - `JSONStreamer()` now accepts `buffer_size`, `max_depth`, `max_string_size` parameters
  - `ObjectStreamer()` now accepts same safety parameters
  - Both classes now support context managers

- **Internal Improvements**:
  - Better error messages with context
  - Cleaner exception hierarchy
  - More efficient string handling

### Developer Experience

- **Modern Tooling**:
  - `pyproject.toml` replaces `setup.py`
  - `uv` for fast package management
  - `pytest` configuration in `pyproject.toml`
  - `ruff` for linting
  - `black` for code formatting
  - `mypy` for type checking

- **CI/CD Ready**:
  - GitHub Actions workflow configuration
  - Pre-configured for multi-Python version testing
  - Coverage reporting with pytest-cov

### Installation

Now **even easier** - no system dependencies required!

```bash
# v2.0 - just pip install, yajl bundled in wheel!
pip install jsonstreamer

# or with uv
uv add jsonstreamer
```

No need to install libyajl separately anymore (for wheel installations).

### Migration Guide

#### From 1.x to 2.0:

1. **No code changes required** for basic usage - API is fully backward compatible!

2. **Optional: Use context managers** to prevent memory leaks:
   ```python
   # Old way (still works)
   streamer = JSONStreamer()
   streamer.consume(data)
   streamer.close()  # Easy to forget!

   # New way (recommended)
   with JSONStreamer() as streamer:
       streamer.consume(data)
   ```

3. **Optional: Add safety limits** for production use:
   ```python
   streamer = JSONStreamer(
       max_depth=100,           # Prevent deeply nested JSON attacks
       max_string_size=1000000, # Prevent huge string attacks
       buffer_size=32768        # Adjust for your use case
   )
   ```

4. **Install**: No changes needed
   ```bash
   pip install jsonstreamer
   # or
   uv add jsonstreamer
   ```

### Performance

- No performance regressions
- Same yajl C library backend
- Slightly improved error handling overhead

### Security

- Protection against deeply nested JSON (DoS attacks)
- Protection against oversized strings (memory exhaustion)
- Better input validation and error messages

### Acknowledgments

- Thanks to the community for patience during the modernization
- Original yajl bindings adapted from yajl-py
- Event system inspired by the `again` library pattern

---

## [1.3.6] - Previous Release

See git history for older changes.

