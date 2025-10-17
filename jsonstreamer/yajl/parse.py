"""
Python bindings for the YAJL JSON parser library using cffi.
Provides streaming JSON parsing with callback-based event handling.
"""

import sys
from abc import ABCMeta, abstractmethod
from typing import Any, Optional, Tuple

from .yajl_cffi import ffi, yajl


class YajlError(Exception):
    """Exception raised when YAJL encounters a parsing error."""

    def __init__(self, value: str = "") -> None:
        """Initialize YajlError with an error message.

        Args:
            value: The error message (default: empty string)
        """
        self.value: str = value

    def __str__(self) -> str:
        """Return the error message as a string."""
        return self.value


class YajlListener(metaclass=ABCMeta):
    """Abstract base class for YAJL parsing event listeners.

    Subclasses must implement all abstract methods to receive parsing events
    as the JSON stream is processed.
    """

    @abstractmethod
    def on_null(self, ctx: Any) -> None:
        """Called when a null value is encountered."""
        pass

    @abstractmethod
    def on_boolean(self, ctx: Any, boolVal: bool) -> None:
        """Called when a boolean value is encountered.

        Args:
            ctx: Parser context
            boolVal: The boolean value (True or False)
        """
        pass

    @abstractmethod
    def on_string(self, ctx: Any, stringVal: str) -> None:
        """Called when a string value is encountered.

        Args:
            ctx: Parser context
            stringVal: The string value
        """
        pass

    @abstractmethod
    def on_start_map(self, ctx: Any) -> None:
        """Called when a JSON object (map) starts."""
        pass

    @abstractmethod
    def on_map_key(self, ctx: Any, stringVal: str) -> None:
        """Called when an object key is encountered.

        Args:
            ctx: Parser context
            stringVal: The key name
        """
        pass

    @abstractmethod
    def on_end_map(self, ctx: Any) -> None:
        """Called when a JSON object (map) ends."""
        pass

    @abstractmethod
    def on_start_array(self, ctx: Any) -> None:
        """Called when a JSON array starts."""
        pass

    @abstractmethod
    def on_end_array(self, ctx: Any) -> None:
        """Called when a JSON array ends."""
        pass

    def parse_start(self) -> None:
        """Called before each stream is parsed."""
        pass

    def parse_buf(self) -> None:
        """Called when a complete buffer has been parsed from the stream."""
        pass

    def complete_parse(self) -> None:
        """Called when the parsing of the stream has finished."""
        pass


class YajlParser:
    """
    CFFI-based parser that binds to yajl C library.
    """

    def __init__(self, listener: YajlListener, buffer_size: int = 65536) -> None:
        """
        Initialize the YAJL parser.

        Args:
            listener: Instance hosting the callbacks that will be called while parsing
            buffer_size: Size of buffer for reading JSON chunks (default: 65536)
        """
        self._buffer_size = buffer_size
        self._listener = listener
        self._exc_info: Optional[Tuple] = None
        self._callbacks_handle = None  # Keep reference to prevent GC
        self._callback_functions = []  # Keep references to callback functions

        if listener is None:
            self._handler = yajl.yajl_alloc(ffi.NULL, ffi.NULL, ffi.NULL)
        else:
            # Create callback functions using cffi
            @ffi.callback("int(void *)")
            def on_null(ctx):
                return self._dispatch("on_null", ctx)

            self._callback_functions.append(on_null)

            @ffi.callback("int(void *, int)")
            def on_boolean(ctx, boolVal):
                return self._dispatch("on_boolean", ctx, bool(boolVal))

            self._callback_functions.append(on_boolean)

            @ffi.callback("int(void *, long long)")
            def on_integer(ctx, integerVal):
                return self._dispatch("on_integer", ctx, int(integerVal))

            self._callback_functions.append(on_integer)

            @ffi.callback("int(void *, double)")
            def on_double(ctx, doubleVal):
                return self._dispatch("on_double", ctx, float(doubleVal))

            self._callback_functions.append(on_double)

            @ffi.callback("int(void *, const char *, size_t)")
            def on_number(ctx, numberVal, numberLen):
                s = ffi.string(numberVal, numberLen).decode("utf-8")
                return self._dispatch("on_number", ctx, s)

            self._callback_functions.append(on_number)

            @ffi.callback("int(void *, const unsigned char *, size_t)")
            def on_string(ctx, stringVal, stringLen):
                s = ffi.string(ffi.cast("char *", stringVal), stringLen).decode("utf-8")
                return self._dispatch("on_string", ctx, s)

            self._callback_functions.append(on_string)

            @ffi.callback("int(void *)")
            def on_start_map(ctx):
                return self._dispatch("on_start_map", ctx)

            self._callback_functions.append(on_start_map)

            @ffi.callback("int(void *, const unsigned char *, size_t)")
            def on_map_key(ctx, key, stringLen):
                s = ffi.string(ffi.cast("char *", key), stringLen).decode("utf-8")
                return self._dispatch("on_map_key", ctx, s)

            self._callback_functions.append(on_map_key)

            @ffi.callback("int(void *)")
            def on_end_map(ctx):
                return self._dispatch("on_end_map", ctx)

            self._callback_functions.append(on_end_map)

            @ffi.callback("int(void *)")
            def on_start_array(ctx):
                return self._dispatch("on_start_array", ctx)

            self._callback_functions.append(on_start_array)

            @ffi.callback("int(void *)")
            def on_end_array(ctx):
                return self._dispatch("on_end_array", ctx)

            self._callback_functions.append(on_end_array)

            # Build callbacks structure
            callbacks = ffi.new("yajl_callbacks *")

            # Determine which callbacks to use
            if hasattr(listener, "on_number"):
                # If on_number is available, it takes precedence over on_integer/on_double
                callbacks.yajl_number = on_number
                callbacks.yajl_integer = ffi.NULL
                callbacks.yajl_double = ffi.NULL
            else:
                callbacks.yajl_number = ffi.NULL
                callbacks.yajl_integer = on_integer
                callbacks.yajl_double = on_double

            callbacks.yajl_null = on_null
            callbacks.yajl_boolean = on_boolean
            callbacks.yajl_string = on_string
            callbacks.yajl_start_map = on_start_map
            callbacks.yajl_map_key = on_map_key
            callbacks.yajl_end_map = on_end_map
            callbacks.yajl_start_array = on_start_array
            callbacks.yajl_end_array = on_end_array

            # Keep reference to prevent garbage collection
            self._callbacks_handle = callbacks

            # Allocate the yajl handle
            self._handler = yajl.yajl_alloc(callbacks, ffi.NULL, ffi.NULL)

        # Configure parser
        self._config()

    def _dispatch(self, func_name: str, *args: Any) -> int:
        """
        Dispatch a callback to the listener.

        Returns:
            1 on success, 0 if listener raised an exception
        """
        try:
            getattr(self._listener, func_name)(*args)
            return 1
        except Exception:
            self._exc_info = sys.exc_info()
            return 0

    def _config(self) -> None:
        """Configure yajl parser options."""
        # Enable partial values and multiple values for streaming
        yajl.yajl_config(self._handler, ffi.cast("int", 0x10))  # allow_partial_values
        yajl.yajl_config(self._handler, ffi.cast("int", 0x08))  # allow_multiple_values

    def parse(self, f: Any) -> None:
        """Parse a JSON stream.

        Args:
            f: File-like object or Tape to read JSON data from.
               Must support read(size) method.

        Raises:
            YajlError: When invalid JSON is encountered in the input stream
        """
        self._listener.parse_start()

        while len(f):
            data = f.read(self._buffer_size).encode("utf-8")
            status = yajl.yajl_parse(self._handler, data, len(data))

            self._listener.parse_buf()

            if status != ffi.cast("int", 0):  # yajl_status_ok
                if status == ffi.cast("int", 1):  # yajl_status_client_canceled
                    if self._exc_info:
                        exc_info = self._exc_info
                        raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
                    else:
                        raise YajlError("Client probably cancelled callback")
                else:  # yajl_status_error
                    error_ptr = yajl.yajl_get_error(self._handler, 1, data, len(data))
                    error_msg = ffi.string(error_ptr).decode("utf-8")
                    yajl.yajl_free_error(self._handler, error_ptr)
                    raise YajlError(error_msg)

            if not data:
                return

    def close(self) -> None:
        """Free the YAJL parser handle and release associated memory."""
        if self._handler is not None:
            yajl.yajl_free(self._handler)
            self._handler = None
