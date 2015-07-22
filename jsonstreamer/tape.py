class Tape:
    """
    Allows writing to end of a file-like object while maintaining the read pointer accurately.
    The read operation actually removes characters read from the buffer.
    """

    def __init__(self, initial_value:str=''):
        """
        :param initial_value: initialize the Tape with a preset string
        """
        self._buffer = initial_value

    def read(self, size:int=None):
        """
        :param size: number of characters to read from the buffer
        :return: string that has been read from the buffer
        """
        if size:
            result = self._buffer[0:size]
            self._buffer = self._buffer[size:]
            return result
        else:
            result = self._buffer
            self._buffer = ''
            return result

    def write(self, s:str):
        """
        :param s: some characters to write to the end of the tape
        :return: length of characters written
        """
        self._buffer += s
        return len(s)

    def __len__(self):
        return len(self._buffer)

    def __str__(self):
        return self._buffer

