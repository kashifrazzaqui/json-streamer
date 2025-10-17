"""
Adapted from yajl-py

Python bindings for the YAJL JSON parser library using ctypes.
Provides streaming JSON parsing with callback-based event handling.
"""

import sys
from abc import ABCMeta, abstractmethod
from ctypes import *
from typing import Any


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


def load_lib() -> Any:
    """Load and return the yajl shared library.

    Attempts to load the YAJL C library from various platform-specific locations.
    Tries common naming patterns for Linux, macOS, and Windows.

    Returns:
        The loaded CDLL object providing access to yajl C functions

    Raises:
        OSError: If the yajl library cannot be found in any expected location
    """
    for yajlso in ["libyajl%s" % (y) for y in ["", ".so", ".dylib", ".so.2"]] + ["yajl.dll"]:
        try:
            return cdll.LoadLibrary(yajlso)
        except OSError:
            pass
    raise OSError("Yajl cannot be found.")


yajl = load_lib()

yajl.yajl_alloc.restype = c_void_p
yajl.yajl_alloc.argtypes = [c_void_p, c_void_p, c_void_p]
yajl.yajl_config.restype = c_int
yajl.yajl_config.argtypes = [c_void_p, c_int]
yajl.yajl_free.argtypes = [c_void_p]
yajl.yajl_parse.restype = c_int
yajl.yajl_parse.argtypes = [c_void_p, c_char_p, c_size_t]
yajl.yajl_complete_parse.restype = c_int
yajl.yajl_complete_parse.argtypes = [c_void_p]
yajl.yajl_get_error.restype = c_char_p
yajl.yajl_get_error.argtypes = [c_void_p, c_int, c_char_p, c_size_t]
yajl.yajl_get_bytes_consumed.restype = c_size_t
yajl.yajl_get_bytes_consumed.argtypes = [c_void_p]
yajl.yajl_free_error.restype = None
yajl.yajl_free_error.argtypes = [c_void_p, c_char_p]

# Callback Functions
YAJL_NULL = CFUNCTYPE(c_int, c_void_p)
YAJL_BOOL = CFUNCTYPE(c_int, c_void_p, c_int)
YAJL_INT = CFUNCTYPE(c_int, c_void_p, c_longlong)
YAJL_DBL = CFUNCTYPE(c_int, c_void_p, c_double)
YAJL_NUM = CFUNCTYPE(c_int, c_void_p, POINTER(c_ubyte), c_uint)
YAJL_STR = CFUNCTYPE(c_int, c_void_p, POINTER(c_ubyte), c_uint)
YAJL_SDCT = CFUNCTYPE(c_int, c_void_p)
YAJL_DCTK = CFUNCTYPE(c_int, c_void_p, POINTER(c_ubyte), c_uint)
YAJL_EDCT = CFUNCTYPE(c_int, c_void_p)
YAJL_SARR = CFUNCTYPE(c_int, c_void_p)
YAJL_EARR = CFUNCTYPE(c_int, c_void_p)


class yajl_callbacks(Structure):
    _fields_ = [
        ("yajl_null", YAJL_NULL),
        ("yajl_boolean", YAJL_BOOL),
        ("yajl_integer", YAJL_INT),
        ("yajl_double", YAJL_DBL),
        ("yajl_number", YAJL_NUM),
        ("yajl_string", YAJL_STR),
        ("yajl_start_map", YAJL_SDCT),
        ("yajl_map_key", YAJL_DCTK),
        ("yajl_end_map", YAJL_EDCT),
        ("yajl_start_array", YAJL_SARR),
        ("yajl_end_array", YAJL_EARR),
    ]


ALLOW_COMMENTS = c_int(1)
DONT_VALIDATE_STRINGS = c_int(2)
ALLOW_TRAILING_GARBAGE = c_int(4)
ALLOW_MULTIPLE_VALUES = c_int(8)
ALLOW_PARTIAL_VALUES = c_int(16)
OK = c_int(0)
CLIENT_CANCELLED = c_int(1)
ERROR = c_int(2)


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
    Class that binds to yajl
    """

    def __init__(self, listener, buffer_size=65536):
        """
        :type listener: :class:`YajlListener`
        :param listener: instance hosting the callbacks that will be called while parsing.
        :param buffer_size: Size of buffer for reading JSON chunks (default: 65536)

        To configure the parser you need to set attributes. Attribute
        names are similar to that of yajl names less the "yajl_" prefix,
        for example: to enable yajl_allow_comments, set self.allow_comments=True
        """
        c_funcs = (
            YAJL_NULL,
            YAJL_BOOL,
            YAJL_INT,
            YAJL_DBL,
            YAJL_NUM,
            YAJL_STR,
            YAJL_SDCT,
            YAJL_DCTK,
            YAJL_EDCT,
            YAJL_SARR,
            YAJL_EARR,
        )

        def on_null(ctx):
            return dispatch("on_null", ctx)

        def on_boolean(ctx, boolVal):
            return dispatch("on_boolean", ctx, boolVal)

        def on_integer(ctx, integerVal):
            return dispatch("on_integer", ctx, integerVal)

        def on_double(ctx, doubleVal):
            return dispatch("on_double", ctx, doubleVal)

        def on_number(ctx, stringVal, stringLen):
            return dispatch("on_number", ctx, string_at(stringVal, stringLen).decode("utf-8"))

        def on_string(ctx, stringVal, stringLen):
            return dispatch("on_string", ctx, string_at(stringVal, stringLen).decode("utf-8"))

        def on_start_map(ctx):
            return dispatch("on_start_map", ctx)

        def on_map_key(ctx, stringVal, stringLen):
            return dispatch("on_map_key", ctx, string_at(stringVal, stringLen).decode("utf-8"))

        def on_end_map(ctx):
            return dispatch("on_end_map", ctx)

        def on_start_array(ctx):
            return dispatch("on_start_array", ctx)

        def on_end_array(ctx):
            return dispatch("on_end_array", ctx)

        def dispatch(func, *args, **kwargs):
            try:
                getattr(self._listener, func)(*args, **kwargs)
                return 1
            except Exception:
                self._exc_info = sys.exc_info()
                return 0

        if listener is None:
            self.callbacks = None
        else:
            callbacks = [
                on_null,
                on_boolean,
                on_integer,
                on_double,
                on_number,
                on_string,
                on_start_map,
                on_map_key,
                on_end_map,
                on_start_array,
                on_end_array,
            ]
            # cannot have both number and integer|double
            if hasattr(listener, "on_number"):
                # if yajl_number is available, it takes precedence
                callbacks[2] = callbacks[3] = 0
            else:
                callbacks[4] = 0
            # cast the funcs to C-types
            callbacks = [c_func(callback) for c_func, callback in zip(c_funcs, callbacks)]
            self.callbacks = byref(yajl_callbacks(*callbacks))

        # set self's vars
        self._buffer_size = buffer_size
        self._listener = listener
        self._handler = yajl.yajl_alloc(self.callbacks, None, None)
        self._config(self._handler)
        self.allow_partial_values = True
        self.allow_multiple_values = True

    def _config(self, hand):
        for k, v in [
            (ALLOW_COMMENTS, "allow_comments"),
            (DONT_VALIDATE_STRINGS, "dont_validate_strings"),
            (ALLOW_MULTIPLE_VALUES, "allow_multiple_values"),
            (ALLOW_PARTIAL_VALUES, "allow_partial_values"),
        ]:
            if hasattr(self, v):
                yajl.yajl_config(hand, k, getattr(self, v))

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
            if status != OK.value:
                if status == CLIENT_CANCELLED.value:
                    if self._exc_info:
                        exc_info = self._exc_info
                        raise exc_info[0](exc_info[1]).with_traceback(exc_info[2])
                    else:
                        raise YajlError("Client probably cancelled callback")
                else:
                    yajl.yajl_get_error.restype = c_char_p
                    error = yajl.yajl_get_error(self._handler, 1, data, len(data))
                    raise YajlError(error)
            if not data:
                return

    def close(self) -> None:
        """Free the YAJL parser handle and release associated memory."""
        yajl.yajl_free(self._handler)
