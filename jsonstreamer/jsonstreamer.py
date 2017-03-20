"""jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
class which emits top level entities in any JSON object.

Useful for parsing partial JSON coming over the wire or via disk
Uses 'again' python module's 'events.EventSource' framework for event boilerplate
again -> https://github.com/kashifrazzaqui/again#eventing-boilerplate
"""

from enum import Enum
from sys import stdin, stdout

from again import events

from .yajl.parse import YajlParser, YajlListener, YajlError
from .tape import Tape

JSONLiteralType = Enum('JSONValueType', 'STRING NUMBER BOOLEAN NULL')
JSONCompositeType = Enum('JSONCompositeType', 'OBJECT ARRAY')


class JSONStreamerException(Exception):
    def __init__(self, msg):
        self._msg = msg

    def __str__(self):
        if isinstance(self._msg, str):
            return self._msg
        else:
            return self._msg.decode("utf-8")


class JSONStreamer(events.EventSource, YajlListener):
    """ Provides a SAX-like push parser which emits events on parsing JSON tokens

    Apart from the public API of this class - an API for attaching events is inherited from again.events.EventSource
    which provides the following functionality

    self.add_listener(event, listener)
    self.remove_listener(event, listener)
    self.add_catch_all_listener(listener) - this listener receives ALL events
    self.remove_catch_all_listener(listener)
    self.auto_listen(self, observer, prefix="_on_") - this automatically finds and attaches methods in the `observer`
        object which are named as `_on_event` as listeners to the jsonstreamer object. This reduces the need to attach
        each listener manually

    Events:
        Events are of the form (event, *args)

        JSONStreamer.DOC_START_EVENT (str): Fired when the `consume` method is called for the first time
        JSONStreamer.DOC_END_EVENT (str): Fired when the `close` method is called
        JSONStreamer.OBJECT_START_EVENT (str): Fired when a JSON object starts with a `{`
        JSONStreamer.OBJECT_END_EVENT (str): Fired when a JSON object ends with a `}`
        JSONStreamer.ARRAY_START_EVENT (str): Fired when a JSON array starts with a `[`
        JSONStreamer.ARRAY_END_EVENT (str): Fired when a JSON array ends with a `]`
        JSONStreamer.KEY_EVENT (str): Fired when a key is encountered within a JSON Object, event also delivers a
            string payload with the name of the key as the only parameter in *args
        JSONStreamer.VALUE_EVENT (str): Fired when a value for a key is encountered; event also delivers a payload
        with the value as the only parameter of *args. The type of the value can be a `string|int|float|boolean|None`
        JSONStreamer.ELEMENT_EVENT (str): Fired when an array element is encounterd; event also delivers a paylod
        with the value as the only parameter of *args. The type of the value can be a `string|int|float|boolean|None`
    """
    DOC_START_EVENT = 'doc_start'
    DOC_END_EVENT = 'doc_end'
    OBJECT_START_EVENT = 'object_start'
    OBJECT_END_EVENT = 'object_end'
    ARRAY_START_EVENT = 'array_start'
    ARRAY_END_EVENT = 'array_end'
    KEY_EVENT = 'key'
    VALUE_EVENT = 'value'
    ELEMENT_EVENT = 'element'

    def __init__(self):
        super(JSONStreamer, self).__init__()
        self._file_like = Tape()
        self._stack = []
        self._pending_value = False
        self._started = False
        self._parser = YajlParser(self)

    def on_start_map(self, ctx):
        self._stack.append(JSONCompositeType.OBJECT)
        self._pending_value = False
        self.fire(JSONStreamer.OBJECT_START_EVENT)

    def on_end_map(self, ctx):
        self._stack.pop()
        self._pending_value = False
        self.fire(JSONStreamer.OBJECT_END_EVENT)

    def on_start_array(self, ctx):
        self._stack.append(JSONCompositeType.ARRAY)
        self.fire(JSONStreamer.ARRAY_START_EVENT)

    def on_end_array(self, ctx):
        self._pending_value = False
        self._stack.pop()
        self.fire(JSONStreamer.ARRAY_END_EVENT)

    def on_map_key(self, ctx, value):
        self.fire(JSONStreamer.KEY_EVENT, value)

    def on_string(self, ctx, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, value)
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, value)
        else:
            raise RuntimeError('Invalid json-streamer state')

    def on_boolean(self, ctx, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, bool(value))
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, bool(value))
        else:
            raise RuntimeError('Invalid json-streamer state')

    def on_null(self, ctx):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, None)
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, None)
        else:
            raise RuntimeError('Invalid json-streamer state')

    def on_integer(self, ctx, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, int(value))
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, int(value))
        else:
            raise RuntimeError('Invalid json-streamer state')

    def on_double(self, ctx, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, float(value))
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, float(value))
        else:
            raise RuntimeError('Invalid json-streamer state')

    def on_number(self, ctx, value):
        ''' Since this is defined both integer and double callbacks are useless '''
        value = int(value) if value.isdigit() else float(value)
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            self.fire(JSONStreamer.VALUE_EVENT, value)
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, value)
        else:
            raise RuntimeError('Invalid json-streamer state')

    def _on_literal(self, json_value_type, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            if self._pending_value:
                self._pending_value = False
                self.fire(JSONStreamer.VALUE_EVENT, value)
            else:
                # must be a key
                assert (json_value_type is JSONLiteralType.STRING)
                self._pending_value = True
                self.fire(JSONStreamer.KEY_EVENT, value)
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer.ELEMENT_EVENT, value)

    def consume(self, data):
        """Takes input that must be parsed

        Note:
            Attach all your listeners before calling this method

        Args:
            data (str): input json string
        """
        if not self._started:
            self.fire(JSONStreamer.DOC_START_EVENT)
            self._started = True
        self._file_like.write(data)
        try:
            self._parser.parse(self._file_like)
        except YajlError as ye:
            raise JSONStreamerException(ye.value)

    def close(self):
        """Closes the streamer which causes a `DOC_END_EVENT` to be fired  and frees up memory used by yajl"""
        self.fire(JSONStreamer.DOC_END_EVENT)
        self._stack = None
        self._parser.close()


class ObjectStreamer(events.EventSource):
    """ Emits key-value pairs or array elements at the top level of a json object/array

    Apart from the public API of this class - an API for attaching events is inherited from again.events.EventSource
    which provides the following functionality

    self.add_listener(event, listener)
    self.remove_listener(event, listener)
    self.add_catch_all_listener(listener) - this listener receives ALL events
    self.remove_catch_all_listener(listener)
    self.auto_listen(self, observer, prefix="_on_") - this automatically finds and attaches methods in the `observer`
        object which are named as `_on_event` as listeners to the jsonstreamer object. This reduces the need to attach
        each listener manually

    Events:
        Events are of the form (event, *args)
        ObjectStreamer.OBJECT_STREAM_START_EVENT (str): Fired at the start of the `root` JSON object, this is mutually
            exclusive from the ARRAY_STREAM_*_EVENTs
        ObjectStreamer.OBJECT_STREAM_END_EVENT (str): Fired at the end of the `root` JSON object, this is mutually
            exclusive from the ARRAY_STREAM_*_EVENTs
        ObjectStreamer.ARRAY_STREAM_START_EVENT (str): Fired at the start of the `root` JSON array, this is mutually
            exclusive from the OBJECT_STREAM_*_EVENTs
        ObjectStreamer.ARRAY_STREAM_END_EVENT (str): Fired at the end of the `root` JSON array, this is mutually
            exclusive from the OBJECT_STREAM_*_EVENTs
        ObjectStreamer.PAIR_EVENT (str): Fired when a top level key-value pair of the `root` object is complete. This
            event also carries a tuple payload which contains the key (str) and value (str|int|float|boolean|None)
        ObjectStreamer.ELEMENT_EVENT (str): Fired when an array element of the `root` array is complete. This event
            also carries a payload which contains the value (str|int|float|boolean|None) of the element
    """
    OBJECT_STREAM_START_EVENT = 'object_stream_start'
    OBJECT_STREAM_END_EVENT = 'object_stream_end'
    ARRAY_STREAM_START_EVENT = 'array_stream_start'
    ARRAY_STREAM_END_EVENT = 'array_stream_end'
    PAIR_EVENT = 'pair'
    ELEMENT_EVENT = 'element'

    def __init__(self):
        super(ObjectStreamer, self).__init__()
        self._streamer = JSONStreamer()
        self._streamer.auto_listen(self)

    def _on_doc_start(self):
        self._root = None
        self._obj_stack = []
        self._key_stack = []

    def _on_doc_end(self):
        pass

    def _on_object_start(self):
        if self._root is None:
            self._root = JSONCompositeType.OBJECT
            self.fire(ObjectStreamer.OBJECT_STREAM_START_EVENT)
        else:
            d = {}
            self._obj_stack.append(d)

    def _process_deep_entities(self):
        o = self._obj_stack.pop()
        key_depth = len(self._key_stack)
        if key_depth is 0:
            if len(self._obj_stack) is 0:
                self.fire(ObjectStreamer.ELEMENT_EVENT, o)
            else:
                self._obj_stack[-1].append(o)
        elif key_depth is 1:
            if len(self._obj_stack) is 0:
                k = self._key_stack.pop()
                self.fire(ObjectStreamer.PAIR_EVENT, (k, o))
            else:
                top = self._obj_stack[-1]
                if isinstance(top, list):
                    top.append(o)
                else:
                    k = self._key_stack.pop()
                    top[k] = o
        elif key_depth > 1:
            current_obj = self._obj_stack[-1]
            if type(current_obj) is list:
                current_obj.append(o)
            else:
                k = self._key_stack.pop()
                current_obj[k] = o

    def _on_object_end(self):
        if len(self._obj_stack) > 0:
            self._process_deep_entities()
        else:
            self.fire(ObjectStreamer.OBJECT_STREAM_END_EVENT)

    def _on_array_start(self):
        if self._root is None:
            self._root = JSONCompositeType.ARRAY
            self.fire('array_stream_start')
        else:
            self._obj_stack.append(list())

    def _on_array_end(self):
        if len(self._obj_stack) > 0:
            self._process_deep_entities()
        else:
            self.fire(ObjectStreamer.ARRAY_STREAM_END_EVENT)

    def _on_key(self, key):
        self._key_stack.append(key)

    def _on_value(self, value):
        k = self._key_stack.pop()
        if len(self._obj_stack) is 0:
            self.fire(ObjectStreamer.PAIR_EVENT, (k, value))
        else:
            self._obj_stack[-1][k] = value

    def _on_element(self, item):
        if len(self._obj_stack) is 0:
            self.fire('element', item)
        else:
            self._obj_stack[-1].append(item)

    def consume(self, data):
        """Takes input that must be parsed

        Note:
            Attach all your listeners before calling this method

        Args:
            data (str): input json string
        """
        try:
            self._streamer.consume(data)
        except YajlError as ye:
            print(ye.value)
            raise JSONStreamerException(ye.value)

    def close(self):
        """Closes the object streamer"""
        self._streamer.close()
        self._streamer = None


def run(data=stdin):
    json_input = data.read()

    def _catch_all(event_name, *args):
        stdout.write('\nevent: ' + event_name)
        for each in args:
            stdout.write('\t->' + ' values: ' + str(each))

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_input)
    streamer.close()
    stdout.write('\n')


if __name__ == '__main__':
    run()
