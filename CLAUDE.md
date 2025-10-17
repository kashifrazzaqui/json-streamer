# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

json-streamer is a Python library that provides SAX-like streaming JSON parsing using the fast C library yajl. It allows parsing JSON streams incrementally without loading entire documents into memory.

### Core Components

1. **JSONStreamer** (`jsonstreamer/jsonstreamer.py`): SAX-like push parser that emits low-level events (object_start, array_start, key, value, element, etc.) as JSON tokens are parsed
2. **ObjectStreamer** (`jsonstreamer/jsonstreamer.py`): Higher-level parser built on top of JSONStreamer that emits complete top-level key-value pairs or array elements from the root JSON object/array
3. **Tape** (`jsonstreamer/tape.py`): File-like buffer object that allows writing to the end while reading from the beginning - enables streaming JSON parsing
4. **YajlParser** (`jsonstreamer/yajl/parse.py`): C bindings to the yajl library using ctypes

### Event System

Both parsers use the `again` library's EventSource framework for event handling:
- `add_listener(event, listener)` - attach specific event listeners
- `add_catch_all_listener(listener)` - attach a listener to all events
- `auto_listen(self, observer, prefix="_on_")` - automatically finds and attaches methods named `_on_<event>` as listeners

## Development Commands

### Setup
```bash
# Install dependencies (requires yajl C library to be installed first)
pip3 install -e .
```

### Running Tests
```bash
# Run all tests
pytest

# Run all tests with verbose output
python3 -m pytest -v

# Run specific test file
python3 tests/testbasic.py

# Run specific test class
python3 -m pytest tests/testbasic.py::JSONStreamerTests

# Run single test
python3 -m pytest tests/testbasic.py::JSONStreamerTests::test_simple_object
```

### Manual Testing
```bash
# Parse JSON from stdin
python -m jsonstreamer.jsonstreamer < some_file.json

# Or
cat some_file.json | python -m jsonstreamer.jsonstreamer
```

## Architecture Notes

### Streaming Parse Flow

1. User calls `consume(data)` on JSONStreamer/ObjectStreamer with partial JSON
2. Data is written to internal Tape buffer
3. YajlParser reads from Tape in chunks (65536 bytes by default)
4. Yajl C library parses bytes and triggers ctypes callbacks
5. Callbacks dispatch to listener methods (on_start_map, on_string, etc.)
6. JSONStreamer fires corresponding events to attached listeners
7. ObjectStreamer (if used) builds up complete objects/arrays and emits them when complete

### State Management

- **JSONStreamer** maintains a stack (`_stack`) to track whether currently inside OBJECT or ARRAY context, determining whether primitives are emitted as VALUE_EVENT or ELEMENT_EVENT
- **ObjectStreamer** maintains two stacks: `_obj_stack` for nested objects/arrays being constructed, and `_key_stack` for object keys waiting for values

### Key Implementation Details

- Parser instances cannot be reused after `close()` - create new instances for each parse
- `consume()` can be called multiple times with partial JSON fragments
- Must call `close()` when done to fire DOC_END_EVENT and free yajl memory
- YajlParser is configured with `allow_partial_values=True` and `allow_multiple_values=True` to enable streaming
- Test files use decorator `@load_test_data` to automatically load JSON from files named after test methods

## Dependencies

- **yajl C library**: Must be installed via system package manager (libyajl.so, libyajl.dylib, or yajl.dll)
- **again**: Python event framework library for event listener boilerplate

## Version 2.0 Changes (2025)

### Major Improvements

1. **Python 3.11+ Compatibility**: Replaced `again` library with built-in event system
2. **Context Manager Support**: Use `with` statement to prevent memory leaks
3. **Safety Limits**: `max_depth` and `max_string_size` parameters prevent DoS attacks
4. **Full Type Hints**: Complete type annotations in all modules
5. **Modern Packaging**: Uses `pyproject.toml` and `uv` for package management
6. **25 Tests**: Added 14 new tests for error handling and safety features

### Bug Fixes

- Fixed 6 `is` vs `==` comparisons with integer literals
- Fixed `type()` vs `isinstance()` usage
- Fixed negative number parsing (e.g., `-123` now correctly parses as `int`, not `float`)
- Improved exception handling for nested exceptions

### API Additions (Backward Compatible)

```python
# New constructor parameters:
streamer = JSONStreamer(
    buffer_size=65536,      # Configurable chunk size
    max_depth=100,          # Prevent deeply nested JSON
    max_string_size=1000000 # Prevent huge strings
)

# Context manager support:
with JSONStreamer() as streamer:
    streamer.consume(data)
# Auto-closes, prevents memory leaks!
```
