json-streamer
=============
jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
ObjectStreamer class which emits top level entities in any JSON object. Works with Python3 only.

### Dependencies

    git clone git@github.com:lloyd/yajl.git
    cd yajl
    ./configure && make install

### Setup

    pip3 install jsonstreamer

    
### Example

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
streamer = JSONStreamer() 
streamer.add_catch_all_listener(_catch_all)
streamer.consume(json_object[0:10]) #note that partial input is possible
streamer.consume(json_object[10:])
streamer.close()
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
streamer = JSONStreamer() #can't reuse old object, make a fresh one
streamer.add_catch_all_listener(_catch_all)
streamer.consume(json_array[0:5])
streamer.consume(json_array[5:])
streamer.close()
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
object_streamer = ObjectStreamer()
object_streamer.add_catch_all_listener(_catch_all)
object_streamer.consume(json_object[0:9])
object_streamer.consume(json_object[9:])
object_streamer.close()
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
object_streamer = ObjectStreamer()
object_streamer.add_catch_all_listener(_catch_all)
object_streamer.consume(json_array[0:4])
object_streamer.consume(json_array[4:])
object_streamer.close()
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
    
    
