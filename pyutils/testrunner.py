
def run_tests(name, globals_dict):
    import sys
    RED = '\033[91m'
    BOLD = '\033[1m'
    END = '\033[0m'
    print (BOLD + 'Running tests for ' + name + ' ...' + END)
    tests = [globals_dict.get(fn) for fn in globals_dict if fn.startswith('test_')]
    for each in tests:
        if callable(each):
            sys.stdout.write('\n-> ' + each.__name__[5:] + ' ... ')
            result = each()
            if result:
                sys.stdout.write('OK')
            else:
                sys.stdout.write(RED + 'FAIL' + END)
