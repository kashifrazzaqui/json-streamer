from setuptools import setup

setup(
    name="jsonstreamer",
    version="2.0.0",
    author="Kashif Razzaqui",
    author_email="kashif.razzaqui@gmail.com",
    url="https://github.com/kashifrazzaqui/json-streamer",
    description=(
        "Provides a SAX-like push parser which works with partial json fragments. "
        "Also provides an ObjectStreamer that emits key-value pairs or array elements "
        "of the `root` json object/array. Based on the fast c library yajl."
    ),
    packages=["jsonstreamer", "jsonstreamer.yajl"],
    install_requires=["cffi>=1.15.0"],
)
