"""
Tape: A file-like buffer for streaming operations.

Provides a simple interface for writing to the end of a buffer while
reading and consuming from the beginning, enabling true streaming behavior.
"""

from typing import Optional


class Tape:
    """
    Allows writing to end of a file-like object while maintaining the read pointer accurately.
    The read operation actually removes characters read from the buffer.
    """

    def __init__(self, initial_value: str = "") -> None:
        """Initialize the Tape with optional initial content.

        Args:
            initial_value: Initial content to populate the tape buffer (default: empty string)
        """
        self._buffer: str = initial_value

    def read(self, size: Optional[int] = None) -> str:
        """Read and consume data from the beginning of the buffer.

        Args:
            size: Number of characters to read. If None, reads entire buffer. (default: None)

        Returns:
            The string that was read from the buffer. The read portion is removed from the buffer.

        Examples:
            >>> tape = Tape("hello world")
            >>> tape.read(5)
            'hello'
            >>> tape.read()
            ' world'
        """
        if size:
            result = self._buffer[0:size]
            self._buffer = self._buffer[size:]
            return result
        else:
            result = self._buffer
            self._buffer = ""
            return result

    def write(self, s: str) -> int:
        """Write data to the end of the tape buffer.

        Args:
            s: String content to write to the end of the tape

        Returns:
            The number of characters written

        Examples:
            >>> tape = Tape()
            >>> tape.write("hello")
            5
        """
        self._buffer += s
        return len(s)

    def __len__(self) -> int:
        """Return the current length of the buffer.

        Returns:
            Number of characters currently in the buffer
        """
        return len(self._buffer)

    def __str__(self) -> str:
        """Return the current buffer contents as a string.

        Returns:
            The complete buffer contents
        """
        return self._buffer
