from distutils.core import setup
setup(name='jsonstreamer',
	version='1.2',
        author='Kashif Razzaqui',
        author_email='kashif.razzaqui@gmail.com',
        url='https://github.com/kashifrazzaqui/json-streamer',
	description='Provides a SAX-like push parser which works with partial json fragments. Also provides an ObjectStreamer that emits key-value pairs or array elements of the `root` json object/array',
        packages=['jsonstreamer'],
        requires=['again']
	)

