#!/usr/bin/env python3
"""
Demo of json-streamer v2.0 new features
"""

from jsonstreamer import JSONStreamer, JSONStreamerException, ObjectStreamer

print("=" * 60)
print("json-streamer v2.0 Feature Demo")
print("=" * 60)

# Feature 1: Context Manager (prevents memory leaks)
print("\n1. Context Manager Support")
print("-" * 60)

json_data = '{"feature": "context manager", "status": "working"}'

print("Using 'with' statement (auto-closes):")
with JSONStreamer() as streamer:
    events = []
    streamer.add_catch_all_listener(lambda e, *a: events.append(e))
    streamer.consume(json_data)

print(f"✅ Events received: {events}")
print("✅ Streamer automatically closed!")


# Feature 2: Safety Limits (DoS protection)
print("\n2. Safety Limits - Max Depth")
print("-" * 60)

deeply_nested = '{"a": {"b": {"c": {"d": "too deep"}}}}'

try:
    with JSONStreamer(max_depth=3) as streamer:
        streamer.consume(deeply_nested)
except JSONStreamerException as e:
    print(f"✅ Caught attack: {e}")


print("\n3. Safety Limits - Max String Size")
print("-" * 60)

huge_string = '{"key": "' + ("x" * 100) + '"}'

try:
    with JSONStreamer(max_string_size=50) as streamer:
        streamer.consume(huge_string)
except JSONStreamerException as e:
    print(f"✅ Caught attack: {e}")


# Feature 3: Configurable Buffer Size
print("\n4. Configurable Buffer Size")
print("-" * 60)

large_json = '{"data": "' + ("y" * 200) + '"}'

with JSONStreamer(buffer_size=128) as streamer:
    events = []
    streamer.add_catch_all_listener(lambda e, *a: events.append(e))
    streamer.consume(large_json)

print(f"✅ Parsed {len(large_json)} chars with 128-byte buffer")
print(f"✅ Events: {events}")


# Feature 4: Negative Number Parsing (bug fix)
print("\n5. Negative Number Parsing (Bug Fix)")
print("-" * 60)

numbers_json = '{"integers": [-123, -456], "floats": [-12.5, -0.3]}'

values = {"integers": [], "floats": []}
current_key = None


def track_values(event, *args):
    global current_key
    if event == "key":
        current_key = args[0]
    elif event == "element" and current_key:
        values[current_key].append((args[0], type(args[0]).__name__))


with JSONStreamer() as streamer:
    streamer.add_catch_all_listener(track_values)
    streamer.consume(numbers_json)

print("Integers:", values["integers"])
print("Floats:", values["floats"])
print("✅ -123 is", values["integers"][0][1], "(not float!)")


# Feature 5: ObjectStreamer with Safety
print("\n6. ObjectStreamer with Safety Features")
print("-" * 60)

pairs = []

with ObjectStreamer(max_depth=10, max_string_size=1000) as streamer:
    streamer.add_listener("pair", lambda p: pairs.append(p))
    streamer.consume('{"v2": "complete", "tests": 25, "coverage": 0.83}')

print("✅ Pairs extracted:", pairs)


print("\n" + "=" * 60)
print("All v2.0 features working! 🚀")
print("=" * 60)
