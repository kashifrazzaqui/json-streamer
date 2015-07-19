from jsonstreamer.jsonstreamer import ObjectStreamer, JSONStreamer, _Lexer


def test_array_of_objects():
    json_input = """
        {
          "params": {
            "dependencies": [
              {
                "app": "Example"
              }
            ]
          }
        }
    """

    import json

    j = json.loads(json_input)

    test_array_of_objects.result = None

    def _obj_start():
        test_array_of_objects.result = {}

    def _elem(e):
        key, value = e[0], e[1]
        test_array_of_objects.result[key] = value

    streamer = ObjectStreamer()
    streamer.add_listener(ObjectStreamer.OBJECT_STREAM_START_EVENT, _obj_start)
    streamer.add_listener(ObjectStreamer.PAIR_EVENT, _elem)
    streamer.consume(json_input)
    assert len(str(j)) == len(str(test_array_of_objects.result))
    return j['params']['dependencies'][0]['app'] == test_array_of_objects.result['params']['dependencies'][0]['app']


def test_obj_streamer_array():
    import json

    json_array = """["a",2,true,{"apple":"fruit"}]"""
    test_obj_streamer_array.counter = 0
    j = json.loads(json_array)

    def _catch_all(event_name, *args):
        if event_name == 'element':
            assert j[test_obj_streamer_array.counter] == args[0]
            test_obj_streamer_array.counter += 1

    streamer = ObjectStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_array)
    return len(j) == test_obj_streamer_array.counter


def test_obj_streamer_object():
    import json

    json_input = """
    {" employees":[
    {"first Name":"Jo:hn", "lastName":"Doe,Foe"},
    {"firstName":"An\\"na", "lastName":"Smith Jack"},
    {"firstName":"Peter", "lastName":"Jones"},
    true,
    745
    ]}
    """
    j = json.loads(json_input)

    def _catch_all(event_name, *args):
        if event_name == 'pair':
            k, v = args[0]
            assert type(j[k]) == type(v)

    obj_streamer = ObjectStreamer()
    obj_streamer.add_catch_all_listener(_catch_all)
    obj_streamer.consume(json_input)
    return True


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


def test_large_deep_obj_streamer():
    json_input = """[
      {
        "_id": "54926f0437ecbc6d8312303b",
        "index": 0,
        "guid": "e43742fa-6195-4722-a0ea-498f668025e0",
        "isActive": false,
        "balance": "$3,103.04",
        "picture": "http://placehold.it/32x32",
        "age": 32,
        "eyeColor": "green",
        "name": "Ann Hyde",
        "gender": "female",
        "company": "DARWINIUM",
        "email": "annhyde@darwinium.com",
        "phone": "+1 (869) 421-3562",
        "address": "812 Ferris Street, Calvary, Louisiana, 6032",
        "about": "Commodo eu laboris sint nostrud et deserunt minim amet. Aliquip exercitation nulla mollit proident velit id velit laboris fugiat. Aliqua deserunt dolore nostrud id proident exercitation excepteur Lorem non reprehenderit. Tempor sit et occaecat non est proident voluptate aliqua esse. Pariatur pariatur nostrud mollit magna sit nostrud duis cillum consectetur proident ipsum Lorem esse. Officia eiusmod non voluptate ad excepteur reprehenderit ullamco adipisicing magna eu proident voluptate.\\r\\n",
        "registered": "2014-10-26T11:04:19 -06:-30",
        "latitude": 8.175509,
        "longitude": 5.955378,
        "tags": [
          "sunt",
          "eiusmod",
          "magna",
          "ex",
          "ipsum",
          "amet",
          "fugiat"
        ],
        "friends": [
          {
            "id": 0,
            "name": "Annabelle Gibson"
          },
          {
            "id": 1,
            "name": "Faith Gutierrez"
          },
          {
            "id": 2,
            "name": "Thompson Black"
          }
        ],
        "greeting": "Hello, Ann Hyde! You have 6 unread messages.",
        "favoriteFruit": "strawberry"
      },
      {
        "_id": "54926f0407dd6e36bc016ab7",
        "index": 1,
        "guid": "9201a165-cc39-45ae-b1ed-339db74e0850",
        "isActive": false,
        "balance": "$1,582.94",
        "picture": "http://placehold.it/32x32",
        "age": 31,
        "eyeColor": "brown",
        "name": "Odessa Cleveland",
        "gender": "female",
        "company": "SOFTMICRO",
        "email": "odessacleveland@softmicro.com",
        "phone": "+1 (870) 488-3607",
        "address": "736 Nautilus Avenue, Clarksburg, Federated States Of Micronesia, 7789",
        "about": "Aliqua esse magna irure proident laboris magna laborum excepteur amet eu veniam. Nulla in reprehenderit veniam deserunt voluptate ex ipsum eu cillum mollit tempor culpa labore magna. Veniam aliquip mollit elit reprehenderit.\\r\\n",
        "registered": "2014-08-11T19:05:24 -06:-30",
        "latitude": 64.104772,
        "longitude": -127.211982,
        "tags": [
          "exercitation",
          "officia",
          "aliqua",
          "velit",
          "sit",
          "reprehenderit",
          "est"
        ],
        "friends": [
          {
            "id": 0,
            "name": "Elise Giles"
          },
          {
            "id": 1,
            "name": "Blanche Lynch"
          },
          {
            "id": 2,
            "name": "Elma Perry"
          }
        ],
        "greeting": "Hello, Odessa Cleveland! You have 10 unread messages.",
        "favoriteFruit": "apple"
      },
      {
        "_id": "54926f04911a99ae145b3590",
        "index": 2,
        "guid": "402cffef-54bc-4640-9079-51ab02af913e",
        "isActive": false,
        "balance": "$2,394.92",
        "picture": "http://placehold.it/32x32",
        "age": 27,
        "eyeColor": "blue",
        "name": "Cabrera Burnett",
        "gender": "male",
        "company": "ZILCH",
        "email": "cabreraburnett@zilch.com",
        "phone": "+1 (865) 466-3885",
        "address": "769 Franklin Street, Groton, Michigan, 9636",
        "about": "Aliqua ex labore labore dolore adipisicing sunt ut veniam aute ut aliquip. Amet nisi eu aliquip qui eu enim duis proident magna. Nulla veniam magna excepteur dolore laborum fugiat do consequat in ea elit deserunt. Ex culpa laboris velit occaecat officia commodo velit reprehenderit nisi consequat esse culpa. In deserunt in culpa do.\\r\\n",
        "registered": "2014-07-04T12:51:22 -06:-30",
        "latitude": 10.022683,
        "longitude": -153.137929,
        "tags": [
          "laborum",
          "consequat",
          "fugiat",
          "Lorem",
          "officia",
          "et",
          "est"
        ],
        "friends": [
          {
            "id": 0,
            "name": "Shawna Webster"
          },
          {
            "id": 1,
            "name": "Snider Morrison"
          },
          {
            "id": 2,
            "name": "Marsha Martinez"
          }
        ],
        "greeting": "Hello, Cabrera Burnett! You have 2 unread messages.",
        "favoriteFruit": "banana"
      }
    ]
    """

    test_large_deep_obj_streamer.result = None

    def array_start_listener():
        test_large_deep_obj_streamer.result = []

    def element_listener(e):
        test_large_deep_obj_streamer.result.append(e)

    import json

    j = json.loads(json_input)
    object_streamer = ObjectStreamer()
    object_streamer.add_listener('array_stream_start', array_start_listener)
    object_streamer.add_listener('element', element_listener)

    object_streamer.consume(json_input)

    assert test_large_deep_obj_streamer.result[1]['friends'][0]['name'] == 'Elise Giles'
    return len(test_large_deep_obj_streamer.result) == len(j)


def test_sample():
    json_input = """{"to": "8743d93a", "type": "response", "payload": {"result": {"units_in_pack": 30, "sku_id": 91, "price": 200.0, "manufacturer": {"id": 5, "url": "johnsons.com", "name": "jhonsons"}, "attributes": [{"display_name": "pack form", "value": "strip", "key": "pack_form"}, {"display_name": "drug form", "value": "tablet", "key": "drug_form"}, {"display_name": "strength", "value": "200 mg", "key": "strength"}, {"display_name": "name", "value": "paracetamol", "key": "name"}, {"display_name": "units in pack", "value": 30, "key": "units_in_pack"}], "brand": "crocin", "type": "allopathy", "name": "crocin 200 mg", "image_urls": ["http//1mg.com/3", "http//1mg.com/2"]}, "request_id": "0f2d9b9c"}, "entity": null, "pid": "43abc6be"} """
    test_sample.counter = 0

    def _catch_all(event_name, *args):
        test_sample.counter += 1

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_input)
    print(test_sample.counter)
    return test_sample.counter is 88


def test_nested_dict():
    json_input = """
    {"glossary":
        {"GlossDiv":
            {"title": "S",
                "GlossList":
                    {"GlossEntry":
                        {"Acronym": "SGML", "ID": "SGML", "SortAs": "SGML",
                        "GlossTerm": "Standard Generalized Markup Language",
                        "Abbrev": "ISO 8879:1986",
                        "GlossDef": {"para": "A meta-markup language, used to create markup languages such as DocBook.",
                        "GlossSeeAlso": ["GML", "XML"]},
                        "GlossSee": "markup"}
                    }
            },
            "title": "example glossary"
        }
    }
    """
    test_nested_dict.counter = 0

    def _catch_all(event_name, *args):
        test_nested_dict.counter += 1

    streamer = JSONStreamer()
    streamer.add_catch_all_listener(_catch_all)
    streamer.consume(json_input)
    return test_nested_dict.counter is 41


if __name__ == '__main__':
    from again.testrunner import run_tests

    run_tests('jsonstreamer.py', globals())
