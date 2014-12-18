from again import events
from again.statemachine import StateMachine, State, Event
from again.decorate import log
from enum import Enum
import re


class _Tokenizer(events.EventSource):
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
    """
    Combines characters to form words, handles escaping
    """
    _criteria = 'char'
    _escape_char = 'backslash'
    _escaped_bslash = '\\'
    _escaped_dbl_bslash = '\\\\'

    def __init__(self):
        super(_TextAccumulator, self).__init__()
        self._ = ""
        self._escaping = False

    def _listener(self, event_name, payload):
        if event_name == _TextAccumulator._criteria:
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
        self._started = False  # TODO reset this on 'reset' event at doc_end
        self._lexer = _Tokenizer()
        self._lexer.add_catch_all_listener(self._catch_all)
        self._text_accumulator = _TextAccumulator()
        self._text_accumulator.bind(self._lexer)
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

        e_start = Event('start')
        e_end = Event('end')
        e_reset = Event('reset')
        e_lbrace = Event('lbrace')
        e_rbrace = Event('rbrace')
        e_lsquare = Event('lsquare')
        e_rsquare = Event('rsquare')
        e_char = Event('char')
        e_comma = Event('comma')
        e_colon = Event('colon')
        e_dblquote = Event('dblquote')
        e_whitespace = Event('whitespace')
        e_newline = Event('newline')
        e_backslash = Event('backslash')

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
        # TODO check to see if braces are balanced
        object_end.loops(e_lbrace, e_rbrace)
        object_end.on(e_rsquare, array_end)
        object_end.on(e_comma, more)
        object_end.ignores(e_whitespace, e_newline)
        object_end.faulty(e_start, e_reset, e_lsquare, e_char, e_colon, e_dblquote, e_backslash)

        array_start.on(e_lbrace, object_start)
        array_start.loops(e_lsquare)
        array_start.on(e_char, literal)
        array_start.on(e_dblquote, string_start)
        array_start.ignores(e_newline, e_whitespace)
        array_start.faulty(e_start, e_end, e_reset, e_rbrace, e_rsquare, e_comma, e_colon, e_backslash)

        array_end.on(e_end, doc_end)
        array_end.on(e_comma, more)
        array_end.on(e_rbrace, object_end)
        array_end.loops(e_rsquare)
        array_end.faulty(e_start, e_reset, e_lbrace, e_lsquare, e_rsquare, e_char, e_colon, e_dblquote,
                         e_backslash)

        string_start.loops(e_char, e_comma, e_colon, e_whitespace, e_newline)
        string_start.on(e_backslash, string_escaping)
        string_start.on(e_dblquote, string_end)
        string_start.faulty(e_start, e_end, e_reset, e_lbrace, e_rbrace, e_lsquare, e_rsquare)

        string_escaping.on(e_char, string_start)
        string_escaping.on(e_dblquote, string_start)
        string_escaping.on(e_backslash, string_start)
        string_escaping.faulty(e_start, e_end, e_reset, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_comma, e_colon,
                               e_whitespace, e_newline)

        string_end.on(e_rbrace, object_end)
        string_end.on(e_rsquare, array_end)
        string_end.on(e_comma, more)
        string_end.on(e_colon, more)
        string_end.faulty(e_start, e_end, e_reset, e_lbrace, e_lsquare, e_char, e_colon, e_dblquote, e_backslash)

        literal.loops(e_char)
        literal.on(e_rbrace, object_end)
        literal.on(e_rsquare, array_end)
        literal.on(e_comma, more)
        literal.ignores(e_newline, e_whitespace)
        literal.faulty(e_start, e_end, e_reset, e_lbrace, e_lsquare, e_dblquote, e_colon, e_backslash)

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

        if new_state.equals(_Lexer._s_s_end):
            text = self._text_accumulator.pop()
            self.fire(_Lexer._literal, JSONLiteralType.STRING, text)

        if previous_state.equals(_Lexer._s_literal) and not new_state.equals(_Lexer._s_literal):
            literal = self._text_accumulator.pop()
            if re.fullmatch(_Lexer._number_pattern, literal):
                self.fire(_Lexer._literal, JSONLiteralType.NUMBER, literal)
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
            self._state_machine.consume(Event('start'))
        self._lexer.consume(data)


JSONCompositeType = Enum('JSONCompositeType', 'OBJECT ARRAY')


class JSONStreamer(events.EventSource):
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
        self._lexer.consume(data)


class ObjectStreamer(events.EventSource):
    """
    For a JSON object it streams all complete keys/value pairs
    For a JSON array it streams all complete values
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
            k = self._key_stack.pop()
            self._obj_stack[-1][k] = o

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
        self._streamer.consume(data)

def test_obj_streamer_array():
    json_array = """["a",2,true,{"apple":"fruit"}]"""
    test_obj_streamer_array.counter = 0

    def _catch_all(event_name, *args):
        test_obj_streamer_array.counter += 1

    streamer = ObjectStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_array)
    return test_obj_streamer_array.counter is 6


def test_obj_streamer_object():
    json_input = """
    {" employees":[
    {"firstName":"Jo:hn", "lastName":"Doe,Foe"},
    {"firstName":"An\\"na", "lastName":"Smith Jack"},
    {"firstName":"Peter", "lastName":"Jones"},
    true,
    745
    ]}
    """
    test_obj_streamer_object.counter = 0

    def _catch_all(event_name, *args):
        test_obj_streamer_object.counter += 1

    obj_streamer = ObjectStreamer()
    obj_streamer.add_catch_all_listener(_catch_all)
    obj_streamer.consume(json_input)
    return test_obj_streamer_object.counter is 3

def test_obj_streamer_object_nested():
    json_n = """{"a":8, "b": {"c": {"d":9}}, "e":{"f":{"g":10, "h":[1,2,3]}}, "i":11}"""
    test_obj_streamer_object_nested.counter = 0

    def _catch_all(event_name, *args):
        test_obj_streamer_object_nested.counter += 1

    obj_streamer = ObjectStreamer()
    obj_streamer.add_catch_all_listener(_catch_all)
    obj_streamer.consume(json_n)
    return test_obj_streamer_object_nested.counter is 6

def test_lexer_basic():
    json_input = """
    {" employees":[
    {"firstName":"Jo:hn", "lastName":"Doe,Foe"},
    {"firstName":"An\\"na", "lastName":"Smith Jack"},
    {"firstName":"Peter", "lastName":"Jones"},
    true,
    745
    ]}
    """
    test_lexer_basic.counter = 0

    def _catch_all(event_name, *args):
        test_lexer_basic.counter += 1

    lexer = _Lexer()
    lexer.add_catch_all_listener(_catch_all)
    lexer.consume(json_input[0:20])
    lexer.consume(json_input[20:])
    return test_lexer_basic.counter is 26


def test_streamer_basic():
    json_input = """
    {" employees":[
    {"firstName":"Jo:hn", "lastName":"Doe,Foe"},
    {"firstName":"An\\"na", "lastName":"Smith Jack"},
    {"firstName":"Peter", "lastName":"Jones"},
    true,
    745
    ]}
    """
    test_streamer_basic.counter = 0

    def _catch_all(event_name, *args):
        test_streamer_basic.counter += 1

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_input[0:20])
    streamer.consume(json_input[20:])
    return test_streamer_basic.counter is 26


def test_lexer_nested():
    json_n = """{"a":8, "b": {"c": {"d":9}}, "e":{"f":{"g":10, "h":[1,2,3]}}, "f":11}"""
    test_lexer_nested.counter = 0

    def _catch_all(event_name, *args):
        test_lexer_nested.counter += 1

    lexer = _Lexer()
    lexer.add_catch_all_listener(_catch_all)
    lexer.consume(json_n)
    return test_lexer_nested.counter is 29


def test_streamer_nested():
    json_n = """{"a":8, "b": {"c": {"d":9}}, "e":{"f":{"g":10, "h":[1,2,3]}}, "i":11}"""

    test_streamer_nested.counter = 0

    def _catch_all(event_name, *args):
        test_streamer_nested.counter += 1

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_n)
    return test_streamer_nested.counter is 29


def test_streamer_array():
    json_array = """["a",2,true,{"apple":"fruit"}]"""
    test_streamer_array.counter = 0

    def _catch_all(event_name, *args):
        test_streamer_array.counter += 1

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_array)
    return test_streamer_array.counter is 10


if __name__ == '__main__':
    from again.testrunner import run_tests

    run_tests('jsonstreamer.py', globals())
