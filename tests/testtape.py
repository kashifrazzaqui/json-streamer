import unittest
from jsonstreamer.tape import Tape

class TapeTests(unittest.TestCase):

    def test_basic(self):
        t = Tape()
        t.write('abc')
        t.read()
        t.write('def')
        assert str(t) == 'def'


    def test_partial_read(self):
        t = Tape('abc')
        t.read(1)
        assert str(t) == 'bc'

    def test_write_after_partial_read(self):
        t = Tape('abc')
        t.read(1)
        t.write('def')
        assert str(t) == 'bcdef'

if __name__ == '__main__':
    unittest.main(verbosity=2)