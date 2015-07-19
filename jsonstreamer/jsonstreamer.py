"""jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
class which emits top level entities in any JSON object.

Useful for parsing partial JSON coming over the wire or via disk
Uses 'again' python module's 'events.EventSource' framework for event boilerplate
again -> https://github.com/kashifrazzaqui/again#eventing-boilerplate
"""

from again import events
from again.statemachine import StateMachine, State, Event
from enum import Enum
import re


class _Tokenizer(events.EventSource):
    """ Tokenizes characters and emits events - for internal use only """
    token_ids = [('{', 'lbrace'), ('}', 'rbrace'), ('[', 'lsquare'), (']', 'rsquare'), (',', 'comma'), (':', 'colon'),
                 ('"', 'dblquote'), (' ', 'whitespace'), ('\n', 'newline'), ('\\', 'backslash')]
    char = 'char'

    def __init__(self):
        super(_Tokenizer, self).__init__()

    def consume(self, data):
        for c in data:
            found = False
            for each in _Tokenizer.token_ids:
                if c == each[0]:
                    found = True
                    self.fire(each[1], each[0])
                    break
            if not found:
                self.fire(_Tokenizer.char, c)


class _TextAccumulator(events.EventSource):
    """ Combines characters to form words, handles escaping - for internal use only """
    _string_criteria = ['char', 'whitespace', 'dblquote', 'lsquare', 'rsqaure', 'comma', 'colon', 'lbrace', 'rbrace']
    _json_criteria = ['char', 'whitespace', 'dblquote']
    _escape_char = 'backslash'
    _escaped_bslash = '\\'
    _escaped_dbl_bslash = '\\\\'

    def __init__(self):
        super(_TextAccumulator, self).__init__()
        self._ = ""
        self._escaping = False
        self._string_start = False
        self._criteria = self._json_criteria

    def _listener(self, event_name, payload):
        if event_name == 'dblquote' and not self._escaping:
            if self._string_start:
                self._string_start = False
                self._criteria = self._json_criteria
            else:
                self._string_start = True
                self._criteria = self._string_criteria

        if event_name in self._criteria:
            if self._escaping:
                self._ += _TextAccumulator._escaped_bslash
                self._escaping = False
            self._ += payload
        else:
            if event_name == _TextAccumulator._escape_char:
                if self._escaping:  # already escaping - hence we are escaping a backslash
                    self._ += _TextAccumulator._escaped_dbl_bslash
                    self._escaping = False
                else:
                    self._escaping = True
            else:
                if self._escaping:
                    self._ += _TextAccumulator._escaped_bslash
                    self._ += payload
                    self._escaping = False

    @property
    def get(self):
        return self._

    def clear(self):
        self._ = ''

    def pop(self):
        result = self.get
        self.clear()
        return result

    def bind(self, lexer):
        lexer.add_catch_all_listener(self._listener)


JSONLiteralType = Enum('JSONValueType', 'STRING NUMBER BOOLEAN NULL')


class _Lexer(events.EventSource):
    _number_pattern = re.compile('^[-+]?[0-9]*\\.?[0-9]+([eE][-+]?[0-9]+)?$')
    _true = 'true'
    _false = 'false'
    _null = 'null'
    _literal = 'LITERAL'

    _s_new = 'new'
    _s_doc_start = 'doc_start'
    _s_doc_end = 'doc_end'
    _s_o_start = 'object_start'
    _s_o_end = 'object_end'
    _s_a_start = 'array_start'
    _s_a_end = 'array_end'
    _s_s_start = 'string_start'
    _s_s_end = 'string_end'
    _s_literal = 'literal'
    _s_more = 'more'
    _s_escaping = 'string_escaping'
    _k_escaping = 'key_escaping'

    _e_start = 'start'
    _e_end = 'end'
    _e_reset = 'reset'
    _e_lbrace = 'lbrace'
    _e_rbrace = 'rbrace'
    _e_lsquare = 'lsquare'
    _e_rsquare = 'rsquare'
    _e_char = 'char'
    _e_comma = 'comma'
    _e_colon = 'colon'
    _e_dblquote = 'dblquote'
    _e_whitespace = 'whitespace'
    _e_newline = 'newline'
    _e_backslash = 'backslash'

    def __init__(self):
        super(_Lexer, self).__init__()
        self._started = False
        self._tokenizer = _Tokenizer()
        self._tokenizer.add_catch_all_listener(self._catch_all)
        self._text_accumulator = _TextAccumulator()
        self._text_accumulator.bind(self._tokenizer)
        self._setup_state_machine()

    def _setup_state_machine(self):
        new = State(_Lexer._s_new)
        doc_start = State(_Lexer._s_doc_start)
        doc_end = State(_Lexer._s_doc_end)
        object_start = State(_Lexer._s_o_start)
        object_end = State(_Lexer._s_o_end)
        array_start = State(_Lexer._s_a_start)
        array_end = State(_Lexer._s_a_end)
        key_escaping = State(_Lexer._k_escaping)
        string_start = State(_Lexer._s_s_start)
        string_end = State(_Lexer._s_s_end)
        literal = State(_Lexer._s_literal)
        more = State(_Lexer._s_more)
        string_escaping = State(_Lexer._s_escaping)

        e_start = Event(_Lexer._e_start)
        e_end = Event(_Lexer._e_end)
        e_reset = Event(_Lexer._e_reset)
        e_lbrace = Event(_Lexer._e_lbrace)
        e_rbrace = Event(_Lexer._e_rbrace)
        e_lsquare = Event(_Lexer._e_lsquare)
        e_rsquare = Event(_Lexer._e_rsquare)
        e_char = Event(_Lexer._e_char)
        e_comma = Event(_Lexer._e_comma)
        e_colon = Event(_Lexer._e_colon)
        e_dblquote = Event(_Lexer._e_dblquote)
        e_whitespace = Event(_Lexer._e_whitespace)
        e_newline = Event(_Lexer._e_newline)
        e_backslash = Event(_Lexer._e_backslash)

        new.on(e_start, doc_start)
        new.on(e_end, doc_end)
        new.ignores(e_newline, e_whitespace)
        new.faulty(e_lbrace, e_lsquare, e_rbrace, e_rsquare, e_char, e_comma, e_colon, e_dblquote, e_backslash)

        doc_start.on(e_lbrace, object_start)
        doc_start.on(e_lsquare, array_start)
        doc_start.ignores(e_newline, e_whitespace)
        doc_start.faulty(e_start, e_end, e_rbrace, e_rsquare, e_char, e_comma, e_colon, e_dblquote, e_backslash)

        doc_end.on(e_reset, new)
        doc_end.faulty(e_start, e_end, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_char, e_comma, e_colon, e_dblquote,
                       e_backslash)

        # JSON Object related states
        object_start.loops(e_lbrace)
        object_start.on(e_rbrace, object_end)
        object_start.on(e_dblquote, string_start)
        object_start.ignores(e_newline, e_whitespace)
        object_start.faulty(e_start, e_end, e_lsquare, e_rsquare, e_comma, e_colon, e_backslash)

        object_end.on(e_end, doc_end)
        object_end.loops(e_lbrace, e_rbrace)
        object_end.on(e_rsquare, array_end)
        object_end.on(e_comma, more)
        object_end.ignores(e_whitespace, e_newline)
        object_end.faulty(e_start, e_reset, e_lsquare, e_char, e_colon, e_dblquote, e_backslash)

        array_start.on(e_lbrace, object_start)
        array_start.on(e_rsquare, array_end)
        array_start.loops(e_lsquare)
        array_start.on(e_char, literal)
        array_start.on(e_dblquote, string_start)
        array_start.ignores(e_newline, e_whitespace)
        array_start.faulty(e_start, e_end, e_reset, e_rbrace, e_rsquare, e_comma, e_colon, e_backslash)

        array_end.on(e_end, doc_end)
        array_end.on(e_comma, more)
        array_end.on(e_rbrace, object_end)
        array_end.loops(e_rsquare)
        array_end.ignores(e_whitespace, e_newline)
        array_end.faulty(e_start, e_reset, e_lbrace, e_lsquare, e_rsquare, e_char, e_colon, e_dblquote,
                         e_backslash)

        string_start.loops(e_char, e_comma, e_colon, e_whitespace, e_newline, e_lbrace, e_rbrace, e_lsquare, e_rsquare)
        string_start.on(e_backslash, string_escaping)
        string_start.on(e_dblquote, string_end)
        string_start.faulty(e_start, e_end, e_reset)

        string_escaping.on(e_char, string_start)
        string_escaping.on(e_dblquote, string_start)
        string_escaping.on(e_backslash, string_start)
        string_escaping.faulty(e_start, e_end, e_reset, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_comma, e_colon,
                               e_whitespace, e_newline)

        string_end.on(e_rbrace, object_end)
        string_end.on(e_rsquare, array_end)
        string_end.on(e_comma, more)
        string_end.on(e_colon, more)
        string_end.ignores(e_whitespace, e_newline)
        string_end.faulty(e_start, e_end, e_reset, e_lbrace, e_lsquare, e_char, e_colon, e_dblquote, e_backslash)

        literal.loops(e_char)
        literal.on(e_rbrace, object_end)
        literal.on(e_rsquare, array_end)
        literal.on(e_comma, more)
        literal.ignores(e_newline, e_whitespace)
        literal.faulty(e_start, e_end, e_reset, e_lbrace, e_lsquare, e_colon, e_dblquote, e_backslash)

        more.on(e_lbrace, object_start)
        more.on(e_lsquare, array_start)
        more.on(e_char, literal)
        more.on(e_dblquote, string_start)
        more.ignores(e_whitespace, e_newline)
        more.faulty(e_start, e_end, e_reset, e_rbrace, e_rsquare, e_comma, e_colon, e_backslash)

        self._state_machine = StateMachine(new)
        self._state_machine.add_states(new, doc_start, doc_end, object_start, object_end, array_start, array_end,
                                       key_escaping, literal, string_start, string_end, more)
        self._state_machine.add_listener('before_state_change', self._on_before_state_change)
        self._state_machine.add_listener('after_state_change', self._on_after_state_change)
        self._state_machine.add_listener('error', self._on_error)

    def _on_error(self, current_state, event):
        raise RuntimeError("{} event cannot be processed in current state: {}".format(event.name, current_state.name))

    def _on_before_state_change(self, current_state, pending_event):
        pass

    def _on_after_state_change(self, previous_state, event, new_state):
        # TODO reorder new_state by probability for perf
        if previous_state.equals(_Lexer._s_s_end):
            text = self._text_accumulator.pop().strip()
            text = text[1:-1]  # remove surrounding double quotes
            self.fire(_Lexer._literal, JSONLiteralType.STRING, text)

        if previous_state.equals(_Lexer._s_literal) and not new_state.equals(_Lexer._s_literal):
            literal = self._text_accumulator.pop().strip()
            if re.fullmatch(_Lexer._number_pattern, literal):
                try:
                    i = int(literal)
                except ValueError:
                    i = float(literal)
                self.fire(_Lexer._literal, JSONLiteralType.NUMBER, i)
            elif literal == _Lexer._true:
                self.fire(_Lexer._literal, JSONLiteralType.BOOLEAN, True)
            elif literal == _Lexer._false:
                self.fire(_Lexer._literal, JSONLiteralType.BOOLEAN, False)
            elif literal == _Lexer._null:
                self.fire(_Lexer._literal, JSONLiteralType.NULL, None)
            else:
                raise RuntimeError("Invalid Literal {}".format(literal))

        if new_state.equals(_Lexer._s_doc_start, _Lexer._s_doc_end, _Lexer._s_o_start,
                            _Lexer._s_o_end, _Lexer._s_a_start, _Lexer._s_a_end):
            self.fire(new_state.name)
        if new_state.equals(_Lexer._s_doc_end):
            self._state_machine.consume(Event('reset'))
            self._started = False

    def _catch_all(self, event_name, payload):
        e = Event(event_name, payload)
        self._state_machine.consume(e)

    def consume(self, data):
        if not self._started:
            self._started = True
            self._state_machine.consume(Event(_Lexer._e_start))
        self._tokenizer.consume(data)

    def close(self):
        if self._started:
            self._state_machine.consume(Event(_Lexer._e_end))
            self._started = False
            self._tokenizer = None
            self._text_accumulator = None
            self._state_machine = None


JSONCompositeType = Enum('JSONCompositeType', 'OBJECT ARRAY')


class JSONStreamer(events.EventSource):
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
        self._lexer = _Lexer()
        self._lexer.auto_listen(self)
        self._stack = []
        self._pending_value = False


    def _on_doc_start(self):
        self.fire(JSONStreamer.DOC_START_EVENT)

    def _on_doc_end(self):
        self.fire(JSONStreamer.DOC_END_EVENT)

    def _on_object_start(self):
        self._stack.append(JSONCompositeType.OBJECT)
        self._pending_value = False
        self.fire(JSONStreamer.OBJECT_START_EVENT)

    def _on_object_end(self):
        self._stack.pop()
        self._pending_value = False
        self.fire(JSONStreamer.OBJECT_END_EVENT)

    def _on_array_start(self):
        self._stack.append(JSONCompositeType.ARRAY)
        self.fire(JSONStreamer.ARRAY_START_EVENT)

    def _on_array_end(self):
        self._pending_value = False
        self._stack.pop()
        self.fire(JSONStreamer.ARRAY_END_EVENT)

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
        self._lexer.consume(data)

    def close(self):
        """Closes the streamer which causes a `DOC_END_EVENT` to be fired """
        self._lexer.close()
        self._lexer = None
        self._stack = None


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
        self._streamer.consume(data)

    def close(self):
        """Closes the object streamer"""
        self._streamer.close()
        self._streamer = None


