__author__ = 'kashif'
RED = '\033[91m'
BLUE = '\033[94m'
BOLD = '\033[1m'
END = '\033[0m'

def log(fn):
    """
    logs parameters and result - takes no arguments
    """
    def func(*args, **kwargs):
        arg_string = ""
        for i in range(0, len(args)):
            var_name = fn.__code__.co_varnames[i]
            print('-- {} : '.format(var_name))
            if var_name != "self":
                arg_string += var_name + ":" + str(args[i]) + ","
        arg_string = arg_string[0:len(arg_string)-1]
        string = (RED + BOLD + '>> ' + END + 'Calling {0}({1})'.format(fn.__code__.co_name, arg_string))
        if len(kwargs):
            string = (RED + BOLD + '>> ' + END + 'Calling {0} with args {1} and kwargs {2}'.format(fn.__code__.co_name, arg_string, kwargs))
        print (string)
        result = fn(*args, **kwargs)
        string = BLUE + BOLD + '<< ' + END + 'Return {0} with result :{1}'.format(fn.__code__.co_name, result)
        print (string)
        return result
    return func


def logx(supress_args=[], supress_all_args=False, supress_result=False, receiver=None):
    """
    logs parameters and result
    takes arguments
        supress_args - list of parameter names to supress
        supress_all_args - boolean to supress all arguments
        supress_result - boolean to supress result
        receiver - custom logging function which takes a string as input; defaults to logging on stdout
    """
    def decorator(fn):
        def func(*args, **kwargs):
            if not supress_all_args:
                arg_string = ""
                for i in range(0, len(args)):
                    var_name = fn.__code__.co_varnames[i]
                    if var_name != "self" and var_name not in supress_args:
                        arg_string += var_name + ":" + str(args[i]) + ","
                arg_string = arg_string[0:len(arg_string)-1]
                string = (RED + BOLD + '>> ' + END + 'Calling {0}({1})'.format(fn.__code__.co_name, arg_string))
                if len(kwargs):
                    string = (RED + BOLD + '>> ' + END + 'Calling {0} with args {1} and kwargs {2}'.format(fn.__code__.co_name, arg_string, kwargs))
                if receiver:
                    receiver(string)
                else:
                    print (string)

            result = fn(*args, **kwargs)
            if not supress_result:
                string = BLUE + BOLD + '<< ' + END + 'Return {0} with result :{1}'.format(fn.__code__.co_name, result)
                if receiver:
                    receiver(string)
                else:
                    print (string)
            return result
        return func
    return decorator



def value_check(arg_name, pos, allowed_values):
    """
    allows value checking at runtime for args or kwargs
    """
    def decorator(fn):

        #brevity compromised in favour of readability
        def logic(*args, **kwargs):
            arg_count = len(args)
            if arg_count:
                if pos < arg_count:
                    if args[pos] in allowed_values:
                        return fn(*args, **kwargs)
                    else:
                        raise ValueError("'{0}' at position {1} not in allowed values {2}".format(args[pos], pos, allowed_values))
                else:
                    if arg_name in kwargs:
                        value = kwargs[arg_name]
                        if value in allowed_values:
                            return fn(*args, **kwargs)
                        else:
                            raise ValueError("'{0}' is not an allowed kwarg".format(arg_name))
                    else:
                        #partially applied functions because of incomplete args, let python handle this
                        return fn(*args, **kwargs)
            else:
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if value in allowed_values:
                        return fn(*args, **kwargs)
                else:
                    raise ValueError("'{0}' is not an allowed kwarg".format(arg_name))
        return logic
    return decorator

def type_check(arg_name, pos, reqd_type):
    """
    allows type checking at runtime for args or kwargs
    """
    def decorator(fn):

        #brevity compromised in favour of readability
        def logic(*args, **kwargs):
            arg_count = len(args)
            if arg_count:
                if pos < arg_count:
                    if isinstance(args[pos],reqd_type):
                        return fn(*args, **kwargs)
                    else:
                        raise TypeError("'{0}' at position {1} not of type {2}".format(args[pos], pos, reqd_type))
                else:
                    if arg_name in kwargs:
                        value = kwargs[arg_name]
                        if isinstance(value, reqd_type):
                            return fn(*args, **kwargs)
                        else:
                            raise TypeError("'{0}' is not of type {1}".format(arg_name, reqd_type))
                    else:
                        #partially applied functions because of incomplete args, let python handle this
                        return fn(*args, **kwargs)
            else:
                if arg_name in kwargs:
                    value = kwargs[arg_name]
                    if isinstance(value, reqd_type):
                        return fn(*args, **kwargs)
                else:
                    raise TypeError("'{0}' is not of type {1}".format(arg_name, reqd_type))
        return logic
    return decorator

