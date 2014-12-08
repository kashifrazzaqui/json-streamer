import events
from statemachine import StateMachine, State, Event


class Lexer(events.EventSource):
    token_ids = [('{', 'lbrace'), ('}', 'rbrace'), ('[', 'lsquare'), (']', 'rsquare'), (',', 'comma'), (':', 'colon'),
                 ('"', 'dblquote'), (' ', 'whitespace'), ('\n', 'newline'), ('\\', 'backslash')]
    other = 'other'

    def __init__(self):
        super(Lexer, self).__init__()

    def consume(self, data):
        for c in data:
            found = False
            for each in Lexer.token_ids:
                if c == each[0]:
                    found = True
                    self.fire(each[1], each[0])
                    break
            if not found:
                self.fire(Lexer.other, c)


class TextAccumulator(events.EventSource):
    """
    Combines characters to form words, handles escaping
    """
    _criteria = 'other'
    _escape_char = "backslash"

    def __init__(self):
        super(TextAccumulator, self).__init__()
        self._ = ""
        self._escaping = False

    def _listener(self, event_name, payload):
        if event_name == TextAccumulator._criteria:
            if self._escaping:
                self._ += "\\"
                self._escaping = False
            self._ += payload
        else:
            if event_name == TextAccumulator._escape_char:
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
                elif len(self._) > 0:
                    self.fire('accumulation', self._)
                    self._ = ""

    def bind(self, lexer):
        lexer.add_catch_all_listener(self._listener)


class JSONStreamer(events.EventSource):
    _other = 'other'

    def __init__(self):
        super(JSONStreamer, self).__init__()
        self._lexer = Lexer()
        self._lexer.add_catch_all_listener(self._catch_all)
        self._text_accumulator = TextAccumulator()
        self._text_accumulator.add_listener('accumulation', self._on_text)
        self._text_accumulator.bind(self._lexer)
        self._setup_state_machine()

    def _setup_state_machine(self):
        # TODO extract all statemachine to a separate object and listen to it
        new = State('new')
        doc_start = State('doc_start')
        doc_end = State('doc_end')
        object_start = State('object_start')
        object_end = State('object_end')
        array_start = State('array_start')
        array_end = State('array_end')
        string_start = State('string_start')
        string_end = State('string_end')
        value_start = State('value_start')
        value_end = State('value_end')
        more = State('more')

        e_start = Event('start')
        e_end = Event('end')
        e_reset = Event('reset')
        e_lbrace = Event('lbrace')
        e_rbrace = Event('rbrace')
        e_lsquare = Event('lsquare')
        e_rsquare = Event('rsquare')
        e_text = Event('text')
        e_comma = Event('comma')
        e_colon = Event('colon')
        e_dblquote = Event('dblquote')
        e_whitespace = Event('whitespace')
        e_newline = Event('newline')
        e_backslash = Event('backslash')

        self._machine = StateMachine(new)
        new.on(e_start, doc_start)
        new.on(e_end, doc_end)
        new.faulty(e_lbrace, e_lsquare, e_rbrace, e_rsquare, e_text, e_comma, e_colon, e_dblquote, e_backslash)

        doc_start.on(e_lbrace, object_start)
        doc_start.on(e_lsquare, array_start)
        doc_start.faulty(e_start, e_end, e_rbrace, e_rsquare, e_text, e_comma, e_colon, e_dblquote, e_backslash)

        doc_end.on(e_reset, new)
        doc_end.faulty(e_start, e_end, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_text, e_comma, e_colon, e_dblquote,
                       e_backslash)

        # JSON Object related states
        object_start.on(e_lbrace, object_start)
        object_start.on(e_rbrace, object_end)
        object_start.on(e_dblquote, string_start)
        object_start.faulty(e_start, e_end, e_lsquare, e_rsquare, e_comma, e_colon, e_backslash)

        object_end.on(e_end, doc_end)
        object_end.on(e_lbrace, object_start)
        object_end.on(e_rbrace, object_end)  # TODO check to see if braces are balanced
        object_end.on(e_rsquare, array_end)
        object_end.on(e_comma, more)
        object_end.faulty(e_start, e_reset, e_lsquare, e_text, e_colon, e_dblquote, e_backslash)

        array_start.on(e_lbrace, object_start)
        array_start.on(e_lsquare, array_start)
        array_start.on(e_text, value_start)
        array_start.on(e_dblquote, string_start)
        array_start.faulty(e_start, e_end, e_reset, e_rbrace, e_rsquare, e_comma, e_colon, e_backslash)

        array_end.on(e_end, doc_end)
        array_end.on(e_comma, more)
        array_end.faulty(e_start, e_reset, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_text, e_colon, e_dblquote,
                         e_backslash)

        string_start.on(e_text, string_start)
        string_start.on(e_comma, string_start)
        string_start.on(e_colon, string_start)
        string_start.on(e_dblquote, string_end)
        string_start.on(e_whitespace, string_start)
        string_start.on(e_newline, string_start)
        string_start.faulty(e_start, e_end, e_reset, e_lbrace, e_rbrace, e_lsquare, e_rsquare, e_backslash)

        string_end.on(e_rbrace, object_end)
        string_end.on(e_rsquare, array_end)
        string_end.on(e_comma, more)
        string_end.on(e_colon, value_start)
        string_end.faulty(e_start, e_end, e_reset, e_lbrace, e_lsquare, e_text, e_dblquote, e_backslash)

        value_start.on(e_lbrace, object_start)
        value_start.on(e_lsquare, array_start)
        value_start.on(e_rsquare, array_end)
        value_start.on(e_text, value_end)
        value_start.on(e_comma, more)
        value_start.on(e_dblquote, string_start)
        value_start.faulty(e_start, e_end, e_reset, e_rbrace, e_colon, e_backslash)

        value_end.on(e_rsquare, array_end)
        value_end.on(e_comma, more)
        value_end.faulty(e_start, e_end, e_reset, e_lbrace, e_rbrace, e_lsquare, e_text, e_colon, e_dblquote,
                          e_backslash)

        more.on(e_lbrace, object_start)
        more.on(e_lsquare, array_start)
        more.on(e_text, value_end)
        more.on(e_dblquote, string_start)
        more.faulty(e_start, e_end, e_reset, e_rbrace, e_rsquare, e_comma, e_colon, e_backslash)

        # TODO based on statemachine events execute logic
        self._state_machine = StateMachine(new)
        self._state_machine.add_states(new, doc_start, doc_end, object_start, object_end, array_start, array_end, value_start, value_end, string_start, string_end, more)

    def _on_text(self, payload):
        print('TEXT: {} - {}'.format(payload, len(payload)))
        # TODO: pass this event to statemachine

    def _catch_all(self, event_name, payload):
        if event_name != JSONStreamer._other:
            # print('{} {}'.format(event_name, payload))
            # TODO: pass this event to statemachine
            pass

    def consume(self, data):
        self._lexer.consume(data)
