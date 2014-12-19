"""jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
class which emits top level entities in any JSON object.

Useful for parsing partial JSON coming over the wire or via disk
Uses 'again' python module's 'events.EventSource' framework for event boilerplate
again -> https://github.com/kashifrazzaqui/again#eventing-boilerplate
"""

from jsonstreamer.jsonstreamer import JSONStreamer, ObjectStreamer