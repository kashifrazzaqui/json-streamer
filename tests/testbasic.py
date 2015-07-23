import unittest
from functools import wraps

import jsonstreamer

json_file_name = lambda test_fn: 'tests/json_files/' + test_fn.__name__[5:] + '.json'


def load_test_data(func):
    """loads some json from a file with the same name as the test"""

    @wraps(func)
    def wrapper(self, *args, **kwargs):
        with open(json_file_name(func), encoding='utf-8') as json_file:
            json_input = json_file.read()
        return func(self, json_input)

    return wrapper


class JSONStreamerTests(unittest.TestCase):
    def setUp(self):
        self._assertions = []
        self._streamer = jsonstreamer.JSONStreamer()
        self._streamer.add_catch_all_listener(self._catch_all)

    def tearDown(self):
        self._streamer.close()
        self.assertEqual(len(self._assertions), 0)

    def _catch_all(self, event_name, *args):
        value = args[0] if args else None
        # print('Asserting event_name: {} , value : {}'.format(event_name,value))
        try:
            e, v = self._assertions.pop(0)
        except IndexError:
            raise AssertionError('not enough asserts')
        self.assertEqual(event_name, e)
        self.assertEqual(value, v)

    @load_test_data
    def test_simple_object(self, json_input):

        self._assertions = [('doc_start', None),
                            ('object_start', None),
                            ('key', 'apple'),
                            ('value', 8),
                            ('key', 'banana'),
                            ('value', 'many'),
                            ('object_end', None),
                            ('doc_end', None)]

        self._streamer.consume(json_input)


class ObjectStreamerTests(unittest.TestCase):
    def setUp(self):
        self._assertions = []
        self._streamer = jsonstreamer.ObjectStreamer()
        self._streamer.add_catch_all_listener(self._catch_all)

    def tearDown(self):
        self._streamer.close()
        self.assertEqual(len(self._assertions), 0)

    def _catch_all(self, event_name, *args):
        value = args[0] if args else None
        # print('\nAsserting event_name: {} , value : {}'.format(event_name, value))
        try:
            expected_event, expected_value = self._assertions.pop(0)
        except IndexError:
            raise AssertionError('not enough asserts')
        self.assertEqual(event_name, expected_event)
        self._assert_value(expected_value, value)

    def _assert_value(self, expected_value, value):
        if value and isinstance(value, tuple) and len(value) == 2:
            if isinstance(value[1], dict):
                self.assertDictEqual(value[1], expected_value[1])
                self.assertEqual(expected_value[0], value[0])
            elif isinstance(value[1], list):
                self.assertListEqual(value[1], expected_value[1])
                self.assertEqual(expected_value[0], value[0])
            else:
                self.assertEqual(value, expected_value)
        else:
            self.assertEqual(value, expected_value)

    @load_test_data
    def test_nested_dict(self, json_input):
        self._assertions = [('object_stream_start', None),
                            ('pair', ('params', {'dependencies': [{'app': 'Example'}]})),
                            ('object_stream_end', None)]
        self._streamer.consume(json_input)

    @load_test_data
    def test_array(self, json_input):
        self._assertions = [('array_stream_start', None),
                            ('element', "a"),
                            ('element', 2),
                            ('element', True),
                            ('element', {"apple": "fruit"}),
                            ('array_stream_end', None)]
        self._streamer.consume(json_input)

    @load_test_data
    def test_spl_chars_in_value(self, json_input):
        self._assertions = [('object_stream_start', None),
                            ('pair',
                             ('employees',
                              [
                                  {"first Name": "Jo:hn", "lastName": "Doe,Foe"},
                                  {"firstName": "An\\na", "lastName": "Smith Jack"},
                                  {"firstName": "Peter", "lastName": "Jones"},
                                  True,
                                  745
                              ]
                              )
                             ),
                            ('object_stream_end', None)]
        self._streamer.consume(json_input)

    @load_test_data
    def test_space_preservation(self, json_input):
        self._assertions = [('object_stream_start', None),
                            ('pair', ('between space', ' before space')),
                            ('pair', ('after space  ', '  all spaces ')),
                            ('object_stream_end', None)
                            ]
        self._streamer.consume(json_input)

    @load_test_data
    def test_arbit_1(self, json_input):
        self._assertions = [('object_stream_start', None),
                            ('pair', ('to', '8743d93a')),
                            ('pair', ('type', 'response')),
                            ('pair', ('payload',
                                      {'request_id': '0f2d9b9c',
                                       'result':
                                           {'type': 'allopathy',
                                            'manufacturer': {'url': 'johnsons.com', 'id': 5, 'name': 'johnsons'},
                                            'name': 'crocin 200 mg',
                                            'brand': 'crocin',
                                            'image_urls': ['http//1example.com/3', 'http//1example.com/2'],
                                            'price': 200.0,
                                            'attributes': [
                                                {'value': 'strip', 'key': 'pack_form', 'display_name': 'pack form'},
                                                {'value': 'tablet', 'key': 'drug_form', 'display_name': 'drug form'},
                                                {'value': '200 mg', 'key': 'strength', 'display_name': 'strength'},
                                                {'value': 'paracetamol', 'key': 'name', 'display_name': 'name'},
                                                {'value': 30, 'key': 'units_in_pack', 'display_name': 'units in pack'}],
                                            'sku_id': 91,
                                            'units_in_pack': 30
                                            }
                                       }
                                      )
                             ),
                            ('pair', ('entity', None)),
                            ('pair', ('pid', '43abc6be')),
                            ('object_stream_end', None)]
        self._streamer.consume(json_input)


class ObjectStreamerListenerTests(unittest.TestCase):
    def setUp(self):
        self._streamer = jsonstreamer.ObjectStreamer()

    def tearDown(self):
        self._streamer.close()
        self.assertEqual(len(self._assertions), 0)

    @load_test_data
    def test_on_element(self, json_input):
        self._assertions = ["a", 2, True, {"apple": "fruit"}]

        def _on_element(value):
            try:
                expected_value = self._assertions.pop(0)
            except IndexError:
                raise AssertionError('not enough asserts')

            self.assertEqual(expected_value, value)

        self._streamer.add_listener('element', _on_element)
        self._streamer.consume(json_input)

    @load_test_data
    def test_on_element_multiple_parses(self, json_input):
        self._assertions = ["a", 2, True, {"apple": "fruit"}, ]

        def _on_element(value):
            try:
                expected_value = self._assertions.pop(0)
            except IndexError:
                raise AssertionError('not enough asserts')

            self.assertEqual(expected_value, value)


        self._streamer.add_listener('element', _on_element)
        self._streamer.consume(json_input[0:8])
        self._streamer.consume(json_input[8:])

if __name__ == '__main__':
    unittest.main(verbosity=2)
