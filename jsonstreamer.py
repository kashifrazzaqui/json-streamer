from pyutils import events
from pyutils.statemachine import StateMachine, State, Event
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
    _escape_char = "backslash"

    def __init__(self):
        super(_TextAccumulator, self).__init__()
        self._ = ""
        self._escaping = False

    def _listener(self, event_name, payload):
        if event_name == _TextAccumulator._criteria:
            if self._escaping:
                self._ += "\\"
                self._escaping = False
            self._ += payload
        else:
            if event_name == _TextAccumulator._escape_char:
                if self._escaping:  # already escaping - hence we are escaping a backslash
                    self._ += "\\\\"
                    self._escaping = False
                else:
                    self._escaping = True
            else:
                if self._escaping:
                    self._ += "\\"
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
    _number_pattern = re.compile("^[-+]?[0-9]*\\.?[0-9]+([eE][-+]?[0-9]+)?$")
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
        raise RuntimeError("{} event cannot be processed in current state: {}".format(event, current_state))

    def _on_before_state_change(self, current_state, pending_event):
        pass

    def _on_after_state_change(self, previous_state, event, new_state):
        # TODO reorder new_state by probability for perf
        # print("{} - {} - {}".format(previous_state.name, event.name, new_state.name))

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
    _key = "key"
    _value = "value"
    _item = "item"

    def __init__(self):
        super(JSONStreamer, self).__init__()
        self._lexer = _Lexer()
        self._lexer.auto_listen(self)
        self._stack = []
        self._pending_value = False


    def _on_doc_start(self):
        self.fire(_Lexer._s_doc_start)

    def _on_doc_end(self):
        self.fire(_Lexer._s_doc_end)

    def _on_object_start(self):
        self._stack.append(JSONCompositeType.OBJECT)
        self.fire(_Lexer._s_o_start)

    def _on_object_end(self):
        self._stack.pop()
        self._pending_value = False
        self.fire(_Lexer._s_o_end)

    def _on_array_start(self):
        self._stack.append(JSONCompositeType.ARRAY)
        self.fire(_Lexer._s_a_start)

    def _on_array_end(self):
        self._stack.pop()
        self.fire(_Lexer._s_a_end)

    def _on_literal(self, json_value_type, value):
        top = self._stack[-1]
        if top is JSONCompositeType.OBJECT:
            if self._pending_value:
                self._pending_value = False
                self.fire(JSONStreamer._value, value)
            else:
                # must be a key
                assert (json_value_type is JSONLiteralType.STRING)
                self._pending_value = True
                self.fire(JSONStreamer._key, value)
        elif top is JSONCompositeType.ARRAY:
            self.fire(JSONStreamer._item, value)


    def consume(self, data):
        self._lexer.consume(data)


class ObjectStreamer(events.EventSource):
    """
    For a JSON object it streams all complete keys/value pairs
    For a JSON array it streams all complete values
    """
    def __init__(self):
        super(ObjectStreamer, self).__init__()
        self._streamer = JSONStreamer()
        self._streamer.auto_listen(self)

    def _on_doc_start(self):
        pass

    def _on_doc_end(self):
        pass

    def _on_object_start(self):
        pass

    def _on_object_end(self):
        pass

    def _on_array_start(self):
        pass

    def _on_array_end(self):
        pass

    def _on_key(self, key):
        pass

    def _on_value(self, value):
        pass

    def _on_item(self, item):
        pass


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

    def _catch_all(event_name, *args):
        print('>> {} : {}'.format(event_name, args))

    lexer = _Lexer()
    lexer.add_catch_all_listener(_catch_all)
    lexer.consume(json_input[0:20])
    lexer.consume(json_input[20:])
    return True


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

    def _catch_all(event_name, *args):
        print('>> {} : {}'.format(event_name, args))

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_input[0:20])
    streamer.consume(json_input[20:])
    return True


def test_lexer_nested():
    json_n = """{"a":8, "b": {"c": {"d":9}}, "e":{"f":{"g":10, "h":[1,2,3]}}, "f":11}"""

    def _catch_all(event_name, *args):
        print('>> {} : {}'.format(event_name, args))

    lexer = _Lexer()
    lexer.add_catch_all_listener(_catch_all)
    lexer.consume(json_n)
    return True


def test_streamer_nested():
    json_n = """{"a":8, "b": {"c": {"d":9}}, "e":{"f":{"g":10, "h":[1,2,3]}}, "i":11}"""

    def _catch_all(event_name, *args):
        print('JSONStreamer>> {} : {}'.format(event_name, args))

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_n)
    return True


if __name__ == '__main__':
    from pyutils.testrunner import run_tests

    run_tests('jsonstreamer.py', globals())
