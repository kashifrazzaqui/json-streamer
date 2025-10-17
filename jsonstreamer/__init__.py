"""jsonstreamer provides a SAX-like push parser via the JSONStreamer class and a 'object' parser via the
ObjectStreamer class which emits top level entities in any JSON object.

Useful for parsing partial JSON coming over the wire or via disk.
Provides a custom event system for event listener boilerplate.
"""

from jsonstreamer.jsonstreamer import JSONStreamer, JSONStreamerException, ObjectStreamer

__all__ = ["JSONStreamer", "ObjectStreamer", "JSONStreamerException"]
