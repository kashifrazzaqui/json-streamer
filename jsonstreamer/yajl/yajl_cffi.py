"""
CFFI-based Python bindings for the YAJL JSON parser library.
Replaces the ctypes-based implementation with more modern cffi.
"""

from cffi import FFI

ffi = FFI()

# Define the C interface for yajl
ffi.cdef(
    """
    // Opaque handle type
    typedef struct yajl_handle_t * yajl_handle;

    // Status codes
    typedef enum {
        yajl_status_ok,
        yajl_status_client_canceled,
        yajl_status_error
    } yajl_status;

    // Configuration options
    typedef enum {
        yajl_allow_comments = 0x01,
        yajl_dont_validate_strings = 0x02,
        yajl_allow_trailing_garbage = 0x04,
        yajl_allow_multiple_values = 0x08,
        yajl_allow_partial_values = 0x10
    } yajl_option;

    // Callback function types
    typedef int (*yajl_null)(void * ctx);
    typedef int (*yajl_boolean)(void * ctx, int boolVal);
    typedef int (*yajl_integer)(void * ctx, long long integerVal);
    typedef int (*yajl_double)(void * ctx, double doubleVal);
    typedef int (*yajl_number)(void * ctx, const char * numberVal, size_t numberLen);
    typedef int (*yajl_string)(void * ctx, const unsigned char * stringVal, size_t stringLen);
    typedef int (*yajl_start_map)(void * ctx);
    typedef int (*yajl_map_key)(void * ctx, const unsigned char * key, size_t stringLen);
    typedef int (*yajl_end_map)(void * ctx);
    typedef int (*yajl_start_array)(void * ctx);
    typedef int (*yajl_end_array)(void * ctx);

    // Callbacks structure
    typedef struct {
        yajl_null        yajl_null;
        yajl_boolean     yajl_boolean;
        yajl_integer     yajl_integer;
        yajl_double      yajl_double;
        yajl_number      yajl_number;
        yajl_string      yajl_string;
        yajl_start_map   yajl_start_map;
        yajl_map_key     yajl_map_key;
        yajl_end_map     yajl_end_map;
        yajl_start_array yajl_start_array;
        yajl_end_array   yajl_end_array;
    } yajl_callbacks;

    // Core API functions
    yajl_handle yajl_alloc(const yajl_callbacks * callbacks,
                          void * afs,
                          void * ctx);

    int yajl_config(yajl_handle h, yajl_option opt, ...);

    yajl_status yajl_parse(yajl_handle hand,
                          const unsigned char * jsonText,
                          size_t jsonTextLength);

    yajl_status yajl_complete_parse(yajl_handle hand);

    unsigned char * yajl_get_error(yajl_handle hand, int verbose,
                                   const unsigned char * jsonText,
                                   size_t jsonTextLength);

    size_t yajl_get_bytes_consumed(yajl_handle hand);

    void yajl_free_error(yajl_handle hand, unsigned char * str);

    void yajl_free(yajl_handle hand);
"""
)


def load_yajl_library():
    """
    Load the yajl shared library.

    First tries to load a bundled library from the package directory,
    then falls back to system-installed libraries.

    Returns:
        FFI library object with yajl functions

    Raises:
        OSError: If yajl library cannot be found
    """
    import os
    import platform

    # Determine bundled library name
    system = platform.system()
    if system == "Darwin":
        bundled_name = "libyajl.dylib"
    elif system == "Windows":
        bundled_name = "yajl.dll"
    else:  # Linux
        bundled_name = "libyajl.so.2"

    # Try bundled library first (in package directory)
    package_dir = os.path.dirname(__file__)
    bundled_path = os.path.join(package_dir, bundled_name)

    if os.path.exists(bundled_path):
        try:
            lib = ffi.dlopen(bundled_path)
            return lib
        except OSError:
            pass  # Fall back to system libraries

    # Try system-installed libraries
    library_names = [
        "libyajl",  # Try without extension first (cffi will add .so/.dylib/.dll)
        "libyajl.so.2",  # Linux with version
        "libyajl.dylib",  # macOS
        "yajl.dll",  # Windows
    ]

    last_error = None
    for lib_name in library_names:
        try:
            lib = ffi.dlopen(lib_name)
            return lib
        except OSError as e:
            last_error = e
            continue

    # If we get here, none of the libraries could be loaded
    raise OSError(
        f"Yajl library could not be found. Tried bundled at {bundled_path} "
        f"and system libraries: {', '.join(library_names)}. "
        f"Last error: {last_error}"
    )


# Load the library once at module import
try:
    yajl = load_yajl_library()
except OSError:
    # Re-raise with more helpful message
    raise OSError(
        "yajl library not found. Please install it:\n"
        "  - Ubuntu/Debian: sudo apt-get install libyajl-dev\n"
        "  - macOS: brew install yajl\n"
        "  - Fedora/RHEL: sudo yum install yajl-devel"
    )
