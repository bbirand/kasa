'''
Base Threaded Actor class

'''
import zmq
import threading
import time, types
import uuid

from zmq.error import ZMQError

class Actor(threading.Thread):
    ''' Base Actor class

    Runs in its own thread, and works by using ZMQ queues for input and output

    '''
    # These variables can be overwritten in subclasses

    # String identification of the actor. Should be overwritten in subclass
    # Can also be given to __init__ as an argument
    name = None

    # If this is true, then the actor must be unique, and another actor
    # cannot exist by the same name. If false, a unique uuid is appended to the
    # name so that the name is always different.
    # This can be overwritten by a subclass
    _unique_actor = True

    def __init__(self, loop = None, name = None, input_address = None, *args, **kwargs):
        super(Actor, self).__init__(*args, **kwargs)
        
        # If loop function was given, use it (instead of subclassing?)
        # The function's signature has to be loop(self, arg)
        # TODO: Create a separate dict instead of self, so that functions can't overwrite import values
        if loop is not None:
            self.loop = types.MethodType(loop, self)
            self.name = loop.func_name

        # If name was given, overwrite it
        if name:
            self.name = name

        # Input socket
        # Created upon subscription (or can be created but not connected?)
        self.inp = None

        # If this actor doesn't have to be unique, add a uuid
        if not self._unique_actor:
            self.name = self.name + str(uuid.uuid1())

        # ZMQ Addresses 
        # Input
        self._inp_address  =  input_address
        # Output
        self._out_address  = 'inproc://{}/out'.format(self.name)      
        # Control
        self._ctrl_address = 'inproc://{}/ctrl'.format(self.name) 

        # Used for signaling this thread to stop
        self._stop = threading.Event()  

        # Store just in cast
        self._kwargs = kwargs
        
    def subscribe(self, other):
        ''' Adds `other` as a subscriber
        Takes the object as an argument
        '''

        # If a class is given as an argument, initalize first
        import inspect
        if inspect.isclass(other):
            other = other()

        elif callable(other):
            #For callables, create a new Actor
            other = Actor(other)

        # Notify the `other` to connect to itself
        # And starts it
        other._connect_input(input_address = self._out_address)
        other.start()
        return other
    __or__ = subscribe
    
    def stop(self):
        self._stop.set()
    
    def _connect_input(self, input_address = None):
        '''
        Notify this actor to connects its input address to the one
        given as an argument

        '''
        self._inp_address = input_address

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
        # Connect input if already given
        if self._inp_address:
            self._connect_input(self._inp_address)

        c = zmq.Context.instance()
        self.out = c.socket(zmq.PUB)

        #NOTE If there are several actors with the same name, this will raise
        # a zmq.error.ZMQError of 'Address already in use'
        try:
            self.out.bind(self._out_address)  
        except ZMQError, e:
            print "Cannot start actor {}. Already running".format(self.name)
            self.stop()


    def main(self):
        '''
        Function that takes full control of the input/output.
        Low-level API
        '''
        raise NotImplementedError("This must be implemented in subclass")

    def loop(self, arg):
        '''
        Take a value from the input at each iteration.
        Must be a coroutine, so receives the new value using a `yield` call
        '''
        raise  NotImplementedError("This can be implemented in subclass")

    def cleanup(self):    
        if self._inp_address:
            self.inp.close()
        self.out.close()
        
    def run(self):
        '''
        Either run the `main` loop, giving full control over the process, or run `loop`
        that gets activated when there is an input, and returns the  
        '''
        self.setup()

        # Run main() if implemented
        try:
            self.main()
        except NotImplementedError:
            # If none is given, run the loop() function (must be implemented)
            # Stops when the event `_stop` is set
            try:
                while not self._stop.is_set():
                    #TODO Check control port

                    if self.inp is None:
                        # If no input, run the loop
                        o = self.loop(None)

                    else:
                        # Else wait to get a response
                        i = self.inp.recv_pyobj()
                        o = self.loop(i)

                    # If we had an output, broadcast to output
                    if o is not None:
                        self.out.send_pyobj(o)

            except StopIteration:
                # if the generator exits, gracefully quit thread
                pass
        
        self.cleanup()


'''
Convenience functions
'''
class ReadEvery(Actor):
    '''
    Calls the objects `read()` method every `every` second
    '''
    #Doesn't have to be unique for now
    _unique_actor = False

    def __init__(self, obj, every=5, name=""):
        '''
        Argument `name` has to be used carefully
        '''
        self.every = every
        self.obj = obj
        super(ReadEvery, self).__init__(name = "ReadEvery{}_{}".format(name, every))

    def loop(self, arg):
        # Read from the object
        val = self.obj.read()

        # Send to the output
        # Low-level API accessing self.out socket directly, before returning
        self.out.send_pyobj(val)

        # Wait for the next loop
        time.sleep(self.every)


'''
Utility classes
'''
class echo(Actor):
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
        super(echo, self).__init__()

    def loop(self, arg):
        print self.msg.format(arg)    


class filterBool(Actor):
    '''
    Gets a value, and then runs the function on it. If the result
    is True, send a boolean to the output
    '''
    name = "FilterBool"
    _unique_actor = False

    def __init__(self, afun):
        self.afun = afun
        super(filterBool, self).__init__()

    def loop(self, arg):
        return self.afun(arg)


class filter(Actor):
    '''
    Gets a value, and then runs the function on it. If the result
    is True, send it to the output.
    '''
    name = "Filter"
    _unique_actor = False

    def __init__(self, afun):
        self.afun = afun
        super(filter, self).__init__()

    def loop(self, arg):
        if self.afun(arg):
            return arg


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
