"""
Tests for error handling, safety limits, and edge cases in jsonstreamer.
"""

import unittest

from jsonstreamer import JSONStreamer, JSONStreamerException, ObjectStreamer


class TestSafetyLimits(unittest.TestCase):
    """Test safety limits: max_depth and max_string_size."""

    def test_max_depth_exceeded_object(self):
        """Test that deeply nested objects trigger max_depth limit."""
        streamer = JSONStreamer(max_depth=3)

        # Depth 1: outermost object
        # Depth 2: nested object
        # Depth 3: another nested object
        # Depth 4: should fail
        json_deep = '{"a": {"b": {"c": {"d": "too deep"}}}}'

        with self.assertRaises(JSONStreamerException) as cm:
            streamer.consume(json_deep)
            streamer.close()

        self.assertIn("Maximum nesting depth", str(cm.exception))

    def test_max_depth_exceeded_array(self):
        """Test that deeply nested arrays trigger max_depth limit."""
        streamer = JSONStreamer(max_depth=3)

        json_deep = "[[[[1]]]]"

        with self.assertRaises(JSONStreamerException) as cm:
            streamer.consume(json_deep)
            streamer.close()

        self.assertIn("Maximum nesting depth", str(cm.exception))

    def test_max_string_size_exceeded(self):
        """Test that oversized strings trigger max_string_size limit."""
        streamer = JSONStreamer(max_string_size=10)

        json_long_string = '{"key": "this_string_is_way_too_long"}'

        with self.assertRaises(JSONStreamerException) as cm:
            streamer.consume(json_long_string)
            streamer.close()

        self.assertIn("String size", str(cm.exception))
        self.assertIn("exceeds maximum", str(cm.exception))

    def test_max_string_size_key(self):
        """Test that oversized keys trigger max_string_size limit."""
        streamer = JSONStreamer(max_string_size=5)

        json_long_key = '{"very_long_key_name": "value"}'

        with self.assertRaises(JSONStreamerException) as cm:
            streamer.consume(json_long_key)
            streamer.close()

        self.assertIn("String size", str(cm.exception))

    def test_no_limits(self):
        """Test that parsing works without limits set."""
        streamer = JSONStreamer()  # No limits

        json_deep = '{"a": {"b": {"c": {"d": {"e": {"f": "deep"}}}}}} '

        try:
            streamer.consume(json_deep)
            streamer.close()
        except JSONStreamerException:
            self.fail("Should not raise exception when no limits set")


class TestContextManager(unittest.TestCase):
    """Test context manager functionality."""

    def test_context_manager_closes_automatically(self):
        """Test that using 'with' statement closes the streamer."""
        events_received = []

        def catch_all(event, *args):
            events_received.append(event)

        with JSONStreamer() as streamer:
            streamer.add_catch_all_listener(catch_all)
            streamer.consume('{"key": "value"}')

        # Should have received doc_end event from automatic close()
        self.assertIn("doc_end", events_received)

    def test_context_manager_with_exception(self):
        """Test that close() is called even when exception occurs."""
        events_received = []

        def catch_all(event, *args):
            events_received.append(event)

        try:
            with JSONStreamer(max_depth=2) as streamer:
                streamer.add_catch_all_listener(catch_all)
                streamer.consume('{"a": {"b": {"c": "too deep"}}}')
        except JSONStreamerException:
            pass  # Expected

        # close() should have been called, firing doc_end
        self.assertIn("doc_end", events_received)


class TestInvalidJSON(unittest.TestCase):
    """Test handling of invalid JSON."""

    def test_invalid_json_syntax(self):
        """Test that invalid JSON raises appropriate error."""
        streamer = JSONStreamer()

        with self.assertRaises(JSONStreamerException):
            streamer.consume("{invalid json}")
            streamer.close()

    def test_incomplete_json(self):
        """Test that incomplete JSON can be continued."""
        streamer = JSONStreamer()
        events = []

        streamer.add_catch_all_listener(lambda e, *args: events.append(e))

        # Partial JSON
        streamer.consume('{"key": "val')
        # Complete it
        streamer.consume('ue"}')
        streamer.close()

        self.assertIn("value", events)
        self.assertIn("doc_end", events)


class TestNegativeNumbers(unittest.TestCase):
    """Test that negative numbers are parsed correctly as integers, not floats."""

    def test_negative_integer(self):
        """Test parsing of negative integers."""
        streamer = JSONStreamer()
        values = []

        def on_value(event, *args):
            if event == "element" and args:
                values.append(args[0])

        streamer.add_catch_all_listener(on_value)
        streamer.consume("[-123, -456]")
        streamer.close()

        self.assertEqual(values[0], -123)
        self.assertEqual(values[1], -456)
        self.assertIsInstance(values[0], int)
        self.assertIsInstance(values[1], int)

    def test_negative_float(self):
        """Test parsing of negative floats."""
        streamer = JSONStreamer()
        values = []

        def on_value(event, *args):
            if event == "element" and args:
                values.append(args[0])

        streamer.add_catch_all_listener(on_value)
        streamer.consume("[-123.45, -0.5]")
        streamer.close()

        self.assertEqual(values[0], -123.45)
        self.assertEqual(values[1], -0.5)
        self.assertIsInstance(values[0], float)
        self.assertIsInstance(values[1], float)


class TestBufferSize(unittest.TestCase):
    """Test configurable buffer size."""

    def test_custom_buffer_size(self):
        """Test that custom buffer sizes work."""
        streamer = JSONStreamer(buffer_size=128)
        events = []

        streamer.add_catch_all_listener(lambda e, *args: events.append(e))

        # Create JSON larger than buffer
        large_json = '{"key": "' + ("x" * 200) + '"}'
        streamer.consume(large_json)
        streamer.close()

        self.assertIn("value", events)
        self.assertIn("doc_end", events)


class TestObjectStreamerSafety(unittest.TestCase):
    """Test that ObjectStreamer inherits safety features."""

    def test_object_streamer_max_depth(self):
        """Test max_depth works with ObjectStreamer."""
        streamer = ObjectStreamer(max_depth=3)

        json_deep = '{"a": {"b": {"c": {"d": "too deep"}}}}'

        with self.assertRaises(JSONStreamerException):
            streamer.consume(json_deep)
            streamer.close()

    def test_object_streamer_context_manager(self):
        """Test context manager works with ObjectStreamer."""
        pairs = []

        with ObjectStreamer() as streamer:
            streamer.add_listener("pair", lambda p: pairs.append(p))
            streamer.consume('{"key1": "val1", "key2": "val2"}')

        self.assertEqual(len(pairs), 2)
        self.assertEqual(pairs[0], ("key1", "val1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
