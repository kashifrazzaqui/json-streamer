json-streamer
=============

**Version 2.0** - Modern, Safe, Fast JSON Streaming Parser

jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
ObjectStreamer class which emits top level entities in any JSON object. Based on the fast C library 'yajl'.
Great for parsing streaming JSON over a network as it comes in or JSON objects that are too large to hold in memory altogether.

## ✨ What's New in v2.0

- 🎯 **Easy Installation** - No system dependencies! Pre-built wheels with bundled yajl
- 🛡️ **Safety First** - Built-in DoS protection with configurable limits
- 🔒 **Context Managers** - Automatic cleanup prevents memory leaks
- 📘 **Type Hints** - Full type annotations for better IDE support
- 🐍 **Modern Python** - Supports Python 3.8 through 3.13
- 🧪 **Well Tested** - 25 tests with 81% coverage

### Installation

```bash
# v2.0 - Just works! No system dependencies needed
pip install jsonstreamer

# or with uv
uv add jsonstreamer
```

**That's it!** No need to manually install yajl - it's bundled in the wheel.

> **Note for source installs**: If installing from source (not wheel), you'll need yajl installed:
> ```bash
> # macOS
> brew install yajl
>
> # Ubuntu/Debian
> sudo apt-get install libyajl-dev
>
> # Fedora/RHEL
> sudo yum install yajl-devel
> ```

Also available at PyPI: https://pypi.python.org/pypi/jsonstreamer
    
### Quick Start

#### Command Line
```bash
python -m jsonstreamer < some_file.json

# or
cat some_file.json | python -m jsonstreamer
```

#### Context Manager (v2.0+ Recommended)
```python
from jsonstreamer import JSONStreamer

json_data = '{"name": "json-streamer", "version": "2.0"}'

# Using 'with' automatically calls close() - prevents memory leaks!
with JSONStreamer() as streamer:
    streamer.add_catch_all_listener(lambda event, *args: print(f'{event}: {args}'))
    streamer.consume(json_data)
```

#### With Safety Limits (v2.0+)
```python
# Protect against malicious JSON
with JSONStreamer(max_depth=100, max_string_size=1000000) as streamer:
    streamer.add_catch_all_listener(handler)
    streamer.consume(untrusted_json)  # Safe from DoS attacks!
```

### Examples

#### Code
variables which contain the input we want to parse


```python
json_object = """
    {
        "fruits":["apple","banana", "cherry"],
        "calories":[100,200,50]
    }
"""
json_array = """[1,2,true,[4,5],"a"]"""
```
    
a catch-all event listener function which prints the events

```python
def _catch_all(event_name, *args):
    print('\t{} : {}'.format(event_name, args))
```

#### JSONStreamer Example

Event listeners get events in their parameters and must have appropriate signatures for receiving their specific event of interest.

JSONStreamer provides the following events:
* doc_start
* doc_end
* object_start
* object_end
* array_start
* array_end
* key - this also carries the name of the key as a string param
* value -  this also carries the value as a string|int|float|boolean|None param
* element - this also carries the value as a string|int|float|boolean|None param

Listener methods must have signatures that match

For example for events: doc_start, doc_end, object_start, object_end, array_start and array_end the listener must be as such, note no params required

```python
def listener():
    pass
```
OR, if your listener is a class method, it can have an additional 'self' param as such

```python
def listener(self):
    pass
```

For events: key, value, element listeners must also receive an additional payload and must be declared as such

```python
def key_listener(key_string):
    pass
```

import and run jsonstreamer on 'json_object'

```python
from jsonstreamer import JSONStreamer

print("\nParsing the json object:")
# v2.0: Use context manager (recommended)
with JSONStreamer() as streamer:
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_object[0:10])  # note that partial input is possible
    streamer.consume(json_object[10:])

# Or the old way (still works, but you must call close())
# streamer = JSONStreamer()
# streamer.add_catch_all_listener(_catch_all)
# streamer.consume(json_object)
# streamer.close()
```

output

    Parsing the json object:
        doc_start : ()
        object_start : ()
        key : ('fruits',)
        array_start : ()
        element : ('apple',)
        element : ('banana',)
        element : ('cherry',)
        array_end : ()
        key : ('calories',)
        array_start : ()
        element : (100,)
        element : (200,)
        element : (50,)
        array_end : ()
        object_end : ()
        doc_end : ()

    
run jsonstreamer on 'json_array'

```python
print("\nParsing the json array:")
# v2.0: Context manager handles cleanup automatically
with JSONStreamer() as streamer:  # can't reuse old object, make a fresh one
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_array[0:5])
    streamer.consume(json_array[5:])
```

output

    Parsing the json array:
        doc_start : ()
        array_start : ()
        element : (1,)
        element : (2,)
        element : (True,)
        array_start : ()
        element : (4,)
        element : (5,)
        array_end : ()
        element : ('a',)
        array_end : ()
        doc_end : ()
   
#### ObjectStreamer Example

ObjectStreamer provides the following events:
* object_stream_start
* object_stream_end
* array_stream_start
* array_stream_end
* pair
* element

import and run ObjectStreamer on 'json_object'

```python
from jsonstreamer import ObjectStreamer

print("\nParsing the json object:")
# v2.0: Context manager
with ObjectStreamer() as object_streamer:
    object_streamer.add_catch_all_listener(_catch_all)
    object_streamer.consume(json_object[0:9])
    object_streamer.consume(json_object[9:])
```    

output

    Parsing the json object:
        object_stream_start : ()
        pair : (('fruits', ['apple', 'banana', 'cherry']),)
        pair : (('calories', [100, 200, 50]),)
        object_stream_end : ()

run the ObjectStreamer on the 'json_array'

```python
print("\nParsing the json array:")
with ObjectStreamer() as object_streamer:
    object_streamer.add_catch_all_listener(_catch_all)
    object_streamer.consume(json_array[0:4])
    object_streamer.consume(json_array[4:])
```

output - note that the events are different for an array

    Parsing the json array:
        array_stream_start : ()
        element : (1,)
        element : (2,)
        element : (True,)
        element : ([4, 5],)
        element : ('a',)
        array_stream_end : ()

#### Example on attaching listeners for various events

```python
ob_streamer = ObjectStreamer()

def pair_listener(pair):
    print('Explicit listener: Key: {} - Value: {}'.format(pair[0],pair[1]))
    
ob_streamer.add_listener('pair', pair_listener) #same for JSONStreamer
ob_streamer.consume(json_object)

ob_streamer.remove_listener(pair_listener) #if you need to remove the listener explicitly
```

#### Even easier way of attaching listeners

```python
class MyClass:
    
    def __init__(self):
        self._obj_streamer = ObjectStreamer() #same for JSONStreamer
        
        # this automatically finds listeners in this class and attaches them if they are named
        # using the following convention '_on_eventname'. Note method names in this class
        self._obj_streamer.auto_listen(self) 
    
    def _on_object_stream_start(self):
        print ('Root Object Started')
        
    def _on_pair(self, pair):
        print('Key: {} - Value: {}'.format(pair[0],pair[1]))
        
    def parse(self, data):
        self._obj_streamer.consume(data)
        
        
m = MyClass()
m.parse(json_object)
```
    
## Troubleshooting

### "Yajl cannot be found" Error

**If using pre-built wheels (pip install):** This shouldn't happen - yajl is bundled!

**If installing from source:**
- **macOS**: `brew install yajl`
- **Ubuntu/Debian**: `sudo apt-get install libyajl-dev`
- **Fedora/RHEL**: `sudo yum install yajl-devel`
- **Windows**: Use pre-built wheel or install cmake and build yajl from source

The library should be in:
- macOS: `/usr/local/lib/libyajl.dylib` or `/opt/homebrew/lib/libyajl.dylib`
- Linux: `/usr/lib/libyajl.so` or `/usr/local/lib/libyajl.so.2`
- Windows: `yajl.dll` in system PATH

## Version 2.0 API Enhancements

All v1.x code works without changes! New optional features:

```python
# Configure safety limits (prevents DoS attacks)
streamer = JSONStreamer(
    max_depth=100,           # Maximum nesting depth
    max_string_size=1000000, # Maximum string size in bytes
    buffer_size=65536        # Parse buffer size
)

# Use context managers (prevents memory leaks)
with JSONStreamer() as streamer:
    streamer.consume(data)
# Automatically calls close()!
```

See [CHANGELOG.md](CHANGELOG.md) for full migration guide.

## Star History

[![Star History Chart](https://api.star-history.com/svg?repos=kashifrazzaqui/json-streamer&type=Date)](https://star-history.com/#kashifrazzaqui/json-streamer&Date)



