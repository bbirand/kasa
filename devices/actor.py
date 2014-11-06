'''
Base Threaded Actor class

'''
import zmq
import threading
import time
import uuid

#TODO: Can make this into a larger Arbiter class with more functionality
global _thread_dict
_thread_dict = {}

class Actor(threading.Thread):
    # String identification of the actor. Should be overwritten in subclass
    # Can also be given to __init__ as an argument
    name = None

    # If this is true, then the actor must be unique, and another actor
    # cannot exist by the same name.
    # If false, a unique uuid is appended to the name so that the name is
    # always different
    _unique_actor = True

    def __init__(self, name = None, input_address = None, *args, **kwargs):
        global _thread_dict
        super(Actor, self).__init__(*args, **kwargs)
        
        # If name was given, overwrite it
        if name:
            self.name = name

        # If this actor doesn't have to be unique, add a uuid
        if not self._unique_actor:
            self.name = self.name + str(uuid.uuid1())
        
        # TODO: Make sure that the name is unique
        if self.name in _thread_dict:
            raise ValueError("This name is already taken")

        # Store in the global dict
        _thread_dict[self.name] = self
        
        self._input_address = input_address
        self._out_address = 'inproc://{}/out'.format(self.name)      
        
        self._kwargs = kwargs
        self._stop = threading.Event()
        
    def subscribe(self, other):
        ''' Adds `other` as a subscriber
        Takes the object as an argument
        '''
        # Notify the `other` to connect to itself
        # And starts it
        other._connect_input(input_address = self._out_address)
        other.start()
        return other
    __or__ = subscribe
    
    def stop(self):
        self._stop.set()
    
    def _connect_input(self, input_address = None):
        self._input_address = input_address

        # If input address is not given, do not create socket
        # This behavior might change
        if input_address is None:
            return

        # If input address was given, connect the input socket
        #print "Connection to {}".format(input_address)
        c = zmq.Context.instance()
        self.inp = c.socket(zmq.SUB)

        # Try to connect. If we can't, wait and try again
        while True:
            try:
                self.inp.connect(input_address)
            except zmq.ZMQError:
                time.sleep(0.1)
            else:
                break
        self.inp.setsockopt_string(zmq.SUBSCRIBE, u'')

    def setup(self):
        # Connect input if necessary
        self._connect_input(self._input_address)

        c = zmq.Context.instance()
        self.out = c.socket(zmq.PUB)
        self.out.bind(self._out_address)  

    def main(self):
        raise NotImplementedError("This must be implemented in subclass")

    def cleanup(self):    
        if self._input_address:
            self.inp.close()
        self.out.close()

    def loop(self):
        raise  NotImplementedError("This can be implemented in subclass")
        
    def run(self):
        '''
        Either run the `main` loop, giving full control over the process, or run `loop`
        that gets activated when there is an input, and returns the  
        '''
        self.setup()
        # See if main() is implemented
        try:
            self.main()
        except NotImplementedError:
            # if not, run the loop coroutine
            try:
                # Start the coroutine
                gen = self.loop()
                gen.send(None)
                while True:
                    i = self.inp.recv_pyobj()
                    o = gen.send(i)
                    if o is not None:
                        self.out.send_pyobj(o)
            except StopIteration:
                # if the generator exits, gracefully quit thread
                pass
        
        self.cleanup()

'''
Utility classes
'''
class Echo(Actor):
    '''
    Prints whatever is received, and send it back
    '''
    name = "Echo"
    _unique_actor = False

    def __init__(self, msg = None):
        if msg is not None:
            self.msg = msg
        else:
            self.msg = "Received value: {}"
        super(Echo, self).__init__()

    def loop(self):
        i = yield
        while True:
            print self.msg.format(i)    
            i = yield i

class FilterBool(Actor):
    '''
    Gets a value, and then runs the function on it. If the result
    is True, send a boolean to the output
    '''
    name = "FilterBool"
    _unique_actor = False

    def __init__(self, afun):
        self.afun = afun
        super(FilterBool, self).__init__()

    def loop(self):
        while True:
            i = yield
            yield self.afun(i)

class Filter(Actor):
    '''
    Gets a value, and then runs the function on it. If the result
    is True, send it to the output.
    '''
    name = "Filter"
    _unique_actor = False

    def __init__(self, afun):
        self.afun = afun
        super(Filter, self).__init__()

    def loop(self):
        while True:
            i = yield
            if self.afun(i):
                print "Outputting {}".format(i)
                yield i

class ReadEvery(Actor):
    '''
    Calls the objects `read()` method every `every` second
    '''
    def __init__(self, obj, every=5):
        self.every = every
        self.obj = obj
        super(ReadEvery, self).__init__(name = "ReadEvery_{}".format(every))

    def main(self):
        while True:
            if self._stop.is_set():
                break
            val = self.obj.read()
            self.out.send_pyobj(val)
            time.sleep(self.every)

'''
Example Usage
'''
class Producer(Actor):
    name = "producer"
    def main(self):
        i=0
        while True:
            if self._stop.is_set():
                break
                
            # Every `num_wait` second, output a value
            msg = "check: {}".format(i)
            self.out.send(msg)
            print "Sent " + msg
            time.sleep(2)#self._kwargs['num_wait'])
            i=i+1
            
class Consumer1(Actor):
    name = "consumer1"
    def main(self):
        while True:
            if self._stop.is_set():
                break
            i = self.inp.recv()
            print "Consumer1 received {}".format(i)
            self.out.send(i)            

class Consumer2(Actor):
    name = "consumer2" 
    def loop(self):
        i = yield
        while True:
            print "Consumer2 received {}".format(i)    
            i = yield i
