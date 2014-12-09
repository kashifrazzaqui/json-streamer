from collections import namedtuple
from pyutils.events import EventSource

import logging

logging.basicConfig(format='%(levelname)s:%(message)s', level=logging.DEBUG)


def log(msg, level=logging.DEBUG):
    logging.log(level, msg)


Transition = namedtuple('Transition', ['old_state', 'event', 'new_state'])


def describe_transition(self):
    return self.old_state.name + " -- " + self.event.name + " --> " + self.new_state.name


Transition.__str__ = describe_transition

# TODO Make Event.name and State.name enum
class Event:
    __slots__ = ('_name', '_payload')

    def __init__(self, name=None, payload=None):
        self._name = self.__class__.__name__.upper()
        if name:
            self._name = name.upper()
        self._payload = payload

    def invalid(self, state):
        """
        This hook is called when this event is ignored by the 'state' i.e. state does not mark this event as valid or
        invalid - its a non-event
        """
        log("current state '{0}' cannot process event '{1}'".format(state.name, self.name))

    @property
    def name(self):
        return self._name

    @property
    def payload(self):
        return self._payload

    @payload.setter
    def payload(self, val):
        self._payload = val

    @payload.deleter
    def payload(self):
        self._payload = None

    def execute(self):
        """
        override for event specific processing
        """
        pass


    def equals(self, *args):
        for event in args:
            event_name = event
            if isinstance(event, Event):
                event_name = event.name
            if self.name == event_name.upper():
                return True
        return False


class State:
    __slots__ = ('_transitions', '_name', '_faults', '_ignored', '_state_data')

    def __init__(self, name=None, state_data=None):
        self._transitions = []
        self._faults = set()  # dedups same object but not same event
        self._ignored = set()
        self._state_data = state_data
        self._name = self.__class__.__name__.upper()
        if name:
            self._name = name.upper()

    def __str__(self):
        result = ""
        for each in self._transitions:
            result += str(each) + "\n"
        for each in self._faults:
            result += self._name + " -- " + each.name + " -- > ERROR\n"
        return result

    @property
    def name(self):
        """
        name of the state - if two states have the same name, they are considered the 'same'
        """
        return self._name

    def choose(self, event):
        """
        called when multiple new states are possible on this event, returns chosen state
        """
        return self.can(event)[0]


    def setup(self, event, old_state):
        """
        abstract method
        called before this state is given an event to consume
        """
        pass

    def process(self, event):
        """
        abstract method
        called to process the consumption of an event
        """
        pass

    def teardown(self, event):
        """
        called after this state has consumed an event
        """
        pass

    def can(self, event):
        """
        returns a list of states that can result from processing this event
        """
        return [t.new_state for t in self._transitions if t.event.equals(event)]

    def is_faulty(self, event):
        """
        returns a boolean if fault processing is handled for this event
        """
        for each in self._faults:
            if each.name.upper() == event.name.upper():
                return True
        return False

    def is_ignored(self, event):
        """
        :param event:
        :return: boolean
        """
        for each in self._ignored:
            if event.name == each:
                return True
        return False

    def consume(self, event):
        """
        process the current event, setup new state and teardown current state
        """
        future_states = self.can(event)

        new_state = future_states[0]
        if len(future_states) > 1:
            new_state = self.choose(event)
        event.execute()
        self.process(event)
        new_state.setup(event, self)
        self.teardown(event)
        return new_state

    def _register_transition(self, event, new_state):
        self._transitions.append(Transition(self, event, new_state))

    def on(self, event, new_state):
        """
        add a valid transition to this state
        """
        if self.name == new_state.name:
            raise RuntimeError("Use loop method to define {} -> {} -> {}".format(self.name, event.name, new_state.name))
        self._register_transition(event, new_state)

    def loops(self, *args):
        """
        :param args: Event objects
        :returns: None

        same as 'on'
        mandatory to use this method instead of 'on' if the start and end events are the same
        enables self-documenting code
        """
        for event in args:
            self._register_transition(event, self)

    def ignores(self, *args):
        """
        :param args: Event objects
        :returns: None
        Any event that is ignored is acceptable but discarded
        """
        for event in args:
            self._ignored.add(event.name)

    def faulty(self, *args):
        """
        add an event or list of events that produces a predefined error
        an event is only added if its not already there
        """
        for each in args:
            if not self.is_faulty(each):
                self._faults.add(each)

    def handle_fault(self, event):
        """
        handle failure/error processing for event
        """
        msg = "Faulty event {0} was received by state {1}".format(event.name, self.name)
        raise RuntimeError(msg)

    def equals(self, *args):
        for each in args:
            state_name = each
            if isinstance(each, State):
                state_name = each.name
            if self.name == state_name.upper():
                return True
        return False


class StateMachine(EventSource):
    def __init__(self, initial_state):
        super(StateMachine, self).__init__()
        self._current_state = initial_state
        self._states = set()
        self._states.add(initial_state)
        self._listeners = []

    def __str__(self):
        result = ""
        for each in self._states:
            result = result + str(each) + "\n"
        result = result + "Current State: " + self._current_state.name
        return result

    def add_states(self, *args):
        for each in args:
            self._states.add(each)

    def consume(self, event):
        if self._current_state.can(event):
            self.fire('before_state_change', self._current_state, event)
            old_state = self._current_state
            self._current_state = self._current_state.consume(event)
            self.fire('after_state_change', old_state, event, self._current_state)
        else:
            if self._current_state.is_ignored(event):
                return
            if self._current_state.is_faulty(event):
                self._current_state.handle_fault(event)
            else:
                event.invalid(self._current_state)
            self.fire('error', self._current_state, event)

    @property
    def current_state(self):
        return self._current_state


def similar(applicants, event, end_state=None):
    for each in applicants:
        if end_state is None:
            each.loop(event)
        else:
            each.on(event, end_state)


def similarFaults(applicants, event):
    for each in applicants:
        each.faulty(event)


def example():
    class TCPClosed(State):
        def consume(self, event):
            print(self.name)
            valid_end_states = super().can(event)
            print(valid_end_states[0].name)
            return valid_end_states[0]

    class Listener:
        def before_state_change(self, current, event):
            print('before')

        def after_state_change(self, old, event, new):
            print('after')

    class TCPOpen(State):
        def consume(self, event):
            valid_end_states = super().can(event)
            return valid_end_states[0]

    e = Event('open', 7)
    f = Event('close', "abc")

    tcp_closed = TCPClosed('tcp_closed')
    tcp_open = TCPOpen('tcp_open')
    tcp_other = State('tcp_other')

    tcp_closed.on(e, tcp_open)
    tcp_closed.faulty(f)
    tcp_other.on(e, tcp_other)

    sm = StateMachine(tcp_closed)
    sm.add_states(tcp_open, tcp_other)
    l = Listener()
    sm.add_listener('before_state_change', l.before_state_change)
    sm.add_listener('after_state_change', l.after_state_change)
    sm.consume(e)
    sm.consume(f)
    print("StateMachine Description:\n")
    print(sm)


if __name__ == '__main__':
    example()
