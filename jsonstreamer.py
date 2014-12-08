import events
from statemachine import StateMachine, State


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
    _criteria = ['other', 'whitespace']

    def __init__(self):
        super(JSONStreamer, self).__init__()
        self._lexer = Lexer()
        self._lexer.add_catch_all_listener(self._catch_all)
        self._text_accumulator = TextAccumulator()
        self._text_accumulator.add_listener('accumulation', self._on_text)
        self._text_accumulator.bind(self._lexer)
        new = State('new')
        doc_start = State('doc_start')
        doc_end = State('doc_end')
        object_start = State('object_start')
        object_end = State('object_end')
        array_start = State('array_start')
        array_end = State('array_end')
        quote_start = State('quote_start')
        quote_end = State('quote_end')
        value_start = State('value_start')
        value_end = State('value_end')
        self._machine = StateMachine(new)
        # TODO Describe events on states


    def _on_text(self, payload):
        print('TEXT: {} - {}'.format(payload, len(payload)))
        # TODO: pass this event to statemachine

    def _catch_all(self, event_name, payload):
        if event_name not in JSONStreamer._criteria:
            # print('{} {}'.format(event_name, payload))
            # TODO: pass this event to statemachine
            pass

    def consume(self, data):
        self._lexer.consume(data)

