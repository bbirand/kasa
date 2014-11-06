#!/usr/bin/env python
import zmq
import pexpect

import sys, threading, time

def _st_connect_helper(gatt):
    '''
    Helper that tries to connect to the device 3 times
    If a connection cannot be established at that time,
    it raises an exception
    '''
    retry_num = 3
    while (retry_num > 0):
        try:
            #print "Preparing to connect. You might need to press the side button..."
            gatt.sendline('connect')
            # test for success of connect
            gatt.expect('\[CON\].*>', timeout=3)
            return
        except pexpect.TIMEOUT:
            retry_num -= 1

    # Could not connect after 3 retries, raise exception
    print "Cannot connect to device. Is it discoverable?"
    gatt.close(force=True)
    raise IOError('Cannot connect')

def st_connect(bluetooth_addr):
    '''
    Spawns a new pexpect call, connects, and returns the handle
    Raises IOError if cannot connect
    '''
    # Receive the bluetooth address as the first argument
    gatt = pexpect.spawn('gatttool -b ' + bluetooth_addr + ' --interactive')
    gatt.expect('\[LE\]>')
    _st_connect_helper(gatt)
    return gatt

def st_read_value(gatt, ctrl_addr, read_addr, enable_cmd, disable_cmd, sleep_amount=0.3):
    '''
    Convenience funciton for enabling a reading, and then performing it
    '''
    st_write(gatt, ctrl_addr, enable_cmd)
    #time.sleep(0.3)   # Sleep so that we can have time to take the reading
    time.sleep(sleep_amount)   # Sleep so that we can have time to take the reading
    rval = st_read(gatt, read_addr)
    st_write(gatt, ctrl_addr, disable_cmd)
    return rval

def st_write(gatt, write_addr, write_value):
    '''
    Write value from an already established GATT interface
    '''
    # Make sure that we're connected
    gatt.sendline(' ')
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])
    if stat == 1:
        # We're not connected, try to reconnect
        _st_connect_helper(gatt)
        #raise IOError("Not connected")

    gatt.sendline('char-write-cmd {} {}'.format(write_addr, write_value))
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])
    if stat == 1:
        # We're not connected
        #raise IOError("Not connected")
        return False

def st_check_connected(gatt):
    ''' Make sure that we're connected
    Checks that the connection is alive, and otherwise, tries to connect
    Raises IOError if connection can't be established.
    Returns True if connection is alive
    '''
    gatt.sendline(' ')
    stat = gatt.expect(['\[CON\].*>', '\[   \].*>'])

    # Connection is alive, return True
    if stat == 0:
        return True

    # Not connected, try to connect
    try:
        print "Reconnecting"
        gatt.sendline('connect')
        gatt.expect('\[CON\].*>', timeout=3)
        return True
    except pexpect.TIMEOUT:
        raise IOError("Unable to set up connection.")

def st_read(gatt, read_addr):
    '''
    Read value from an already established GATT interface
    '''
    st_check_connected(gatt)

    # Read the value
    gatt.sendline('char-read-hnd {}'.format(read_addr))
    gatt.expect('descriptor: (?P<value>.*) \r\n') 
    rval = gatt.match.group('value')
    gatt.expect('\[CON\].*>')
    st_check_connected(gatt)

    return rval

def st_disconnect(gatt):
    gatt.sendline('disconnect')
    gatt.expect('\[   \].*>')
    gatt.close(force=True)

def worker_thread(worker_url, bluetooth_addr, context=None):
    '''
    Thread that establishes a connection and waits for input on the PAIR socket

    Arguments:
    - worker_url: URL for the PAIR socket that will be used for communicating with the
    main process
    - bluetooth_addr: Bluetooth address of the device to be connected

    The items on the socket should be a string, corresponding to space-separated list
    'read ctrl_add read_addr enable_cmd disable_cmd'

    '''
    context = context or zmq.Context.instance()

    # Connected to the paired main thread
    socket = context.socket(zmq.PAIR)
    socket.connect(worker_url)

    # Poller to implement timeout on the socket
    p = zmq.Poller()
    p.register(socket, zmq.POLLIN)

    # Connect to the BT device
    try:
        gatt = st_connect(bluetooth_addr)
        socket.send(b'ok')
    except IOError:
        socket.send(b'fail')
        return

    while True:
        # Poll the socket for new commands. If we don't receive any new commands
        # within 5 seconds, make sure that the connection is active
        msgs = dict(p.poll(10e3)) 

        if socket not in msgs:
            # Timeout event
            if gatt is not None:
                st_check_connected(gatt)
            continue

        cmd = socket.recv().split()

        if cmd[0] == 'read':
            read_addr = cmd[1]
            rval = st_read(gatt, read_addr)
            socket.send(rval)

        elif cmd[0] == 'write':
            write_addr = cmd[1]
            write_value = cmd[2]
            st_write(gatt, write_addr, write_value)
            socket.send(b'ok')

        elif cmd[0] == 'read_value':
            # Make sure that we're connected
            ctrl_addr, read_addr, enable_cmd, disable_cmd = cmd[1:5]

            # Default amount to sleep between the readings
            sleep_amount = 0.3
            if len(cmd) == 6:
                sleep_amount = float(cmd[5])
            rval = st_read_value(gatt, ctrl_addr, read_addr, enable_cmd, disable_cmd, sleep_amount = sleep_amount)
            socket.send(rval)
            #TODO Send the reading via a PUB/SUB socket

        elif cmd[0] == 'disconnect':
            # Disconnect and exit the thread
            st_disconnect(gatt)
            socket.send(b"ok")
            break

        else:
            raise ValueError('Command not understood')

def main():
    '''
    Server routine
    '''
    port = "9801"
    context = zmq.Context.instance()

    # Receive input from the outside world
    socket = context.socket(zmq.DEALER)
    # Specify unique identity
    socket.setsockopt(zmq.IDENTITY, b"GATT")
    socket.connect("tcp://*:%s" % port)

    print "Ready to receive"

    # Where we will store references to the worker threads
    worker_sockets = {}

    while True:
        # Get the outside message in several parts
        # Store the client_addr
        client_addr, _, msg = socket.recv_multipart()
        print "Received request {} from '{}'".format(msg, client_addr)
        msg = msg.split(' ')

        command = msg[0]

        # Return list of active connections
        if command == 'active':
            active_socks = worker_sockets.keys()
            socket.send_multipart([client_addr, b'', ",".join(active_socks)])
            continue

        # Parse bluetooth address
        bluetooth_addr = msg[1]
        command_args = msg[2:]

        # Worker URL to be shared
        url_worker = "inproc://{}".format(bluetooth_addr)

        # Connect: Set up socket and start thread
        if command == 'connect':
            # Check if we're already connected (if so, don't do anything)
            if bluetooth_addr in worker_sockets:
                socket.send_multipart([client_addr, b'', b'ok'])
                continue

            # Create socket to be shared with worker thread
            worker = context.socket(zmq.PAIR)
            worker.bind(url_worker)

            #Start the worker thread
            thread = threading.Thread(target=worker_thread, args=(url_worker, bluetooth_addr))
            thread.start()
                
            # Check to see if the operation was successful
            stats = worker.recv()
            if stats == 'ok':
                # Save the socket object if the call was successful
                worker_sockets[bluetooth_addr] = worker
                socket.send_multipart([client_addr, b'', b'ok'])
            else:
                # Connection is not successful, pass on error message
                socket.send_multipart([client_addr, b'', stats])

        elif command == 'disconnect':
            # Send disconnect to thread, and close and remove the socket
            # from the dict
            worker = worker_sockets[bluetooth_addr]
            worker.send(b'disconnect')
            stats = worker.recv()
            if stats == 'ok':
                socket.send_multipart([client_addr, b'', b'ok'])
                del worker_sockets[bluetooth_addr]
            else:
                # Connection is not successful
                socket.send_multipart([client_addr, b'', b'error'])

        else:
            # Fetch the right socket
            worker = worker_sockets[bluetooth_addr]

            worker.send(command + ' ' + ' '.join(command_args))
            worker_result = worker.recv()

            # Relay reply to the original thread
            socket.send_multipart([client_addr, b'', worker_result]) 

if __name__=="__main__": main()
