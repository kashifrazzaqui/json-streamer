json-streamer
=============
jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
class which emits top level entities in any JSON object.



variables which contain the input we want to parse
    
    json_object = """
        {
            "fruits":["apple","banana", "cherry"],
            "calories":[100,200,50]
        }
    """
    
    json_array = """
        [1,2,true,[4,5],"a"]
    """
   
    
an event listener function which prints the events

    def _catch_all(event_name, *args):
        print('\t{} : {}'.format(event_name, args))
        
### JSONStreamer Example
import and run jsonstreamer on 'json_object'

    from jsonstreamer import JSONStreamer 
    
    print("\nParsing the json object:")
    streamer = JSONStreamer() 
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_object[0:10]) #note that partial input is possible
    streamer.consume(json_object[10:])
    streamer.close()
   
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

    print("\nParsing the json array:")
    streamer = JSONStreamer() #can't reuse old object, make a fresh one
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_array[0:5])
    streamer.consume(json_array[5:])
    streamer.close()

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
   
### ObjectStreamer Example

import and run ObjectStreamer on 'json_object'

    from jsonstreamer import ObjectStreamer
    
    print("\nParsing the json object:")
    object_streamer = ObjectStreamer()
    object_streamer.add_catch_all_listener(_catch_all)
    object_streamer.consume(json_object[0:9])
    object_streamer.consume(json_object[9:])
    object_streamer.close()
    
output

    Parsing the json object:
        object_stream_start : ()
        pair : (('fruits', ['apple', 'banana', 'cherry']),)
        pair : (('calories', [100, 200, 50]),)
        object_stream_end : ()

run the ObjectStreamer on the 'json_array'

    print("\nParsing the json array:")
    object_streamer = ObjectStreamer()
    object_streamer.add_catch_all_listener(_catch_all)
    object_streamer.consume(json_array[0:4])
    object_streamer.consume(json_array[4:])
    object_streamer.close()

output - note that the events are different for an array

    Parsing the json array:
        array_stream_start : ()
        element : (1,)
        element : (2,)
        element : (True,)
        element : ([4, 5],)
        element : ('a',)
        array_stream_end : ()
