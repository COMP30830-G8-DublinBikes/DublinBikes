import time

# a timer function that we will use as a decorator
def timeit(method): # the method takes a method as an input, which is the one we will decorate
    def timed(*args, **kw):
        start = time.time()
        result = method(*args, **kw) # this is the call to the method, with variable arguments and keywords
        end = time.time()
        print('%r (%r, %r) %2.2f sec' % (method.__name__, args, kw, end-start)) 
        return result
    return timed

@timeit
def my_method(a, b):
    for i in range(100000000):
        pass

my_method(1, 2) 


# How do args and kw work:

# def flexible_function(*args, **kw): # I have variable positional arguments, and variable keyword arguments (i.e., arguments with explicit names)
#    print("Positional arguments (args):", args)
#    print("Keyword arguments (kw):", kw)

# Example call
#flexible_function(1, 2, 3, name="Alice", age=25)