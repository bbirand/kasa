import zmq
# 
# Kasa Broker
#
#
# (c) 2014 Berk Birand

def main():
    """ main method """

    url_clients = "tcp://*:9800"
    url_workers = "tcp://*:9801"

    # Prepare our context and sockets
    context = zmq.Context()
    clients = context.socket(zmq.ROUTER)
    clients.bind(url_clients)

    workers = context.socket(zmq.ROUTER)
    workers.bind(url_workers)
    
    poller = zmq.Poller()
    poller.register(clients, zmq.POLLIN)
    poller.register(workers, zmq.POLLIN)

    # Set of worker IDs that are currently available
    registered_workers = set([])

    print "Ready to broker"
    while True:
        socks = dict(poller.poll())

        if (clients in socks and socks[clients] == zmq.POLLIN):
            # Parse the three components of the message
            client_addr, empty, msg = clients.recv_multipart()

            assert empty == b""
            print "Client with address: {}".format(client_addr)
            print "Message is {}".format(msg)

            cmds = msg.split(' ')
            target = cmds[0]   # First part is the target device

            # If the worker is registered, send the message there
            # Also send the client address for the reply
            workers.send(target, zmq.SNDMORE)
            workers.send(client_addr, zmq.SNDMORE)
            workers.send(b'', zmq.SNDMORE)
            workers.send(' '.join(cmds[1:]))

        if (workers in socks and socks[workers] == zmq.POLLIN):
            # Parse the three components of the message
            _, client_addr, _, msg = workers.recv_multipart()
            print "Received response for client '{}' : {}".format(client_addr, msg)

            clients.send(client_addr, zmq.SNDMORE)
            clients.send(b'', zmq.SNDMORE)
            clients.send(msg)

    # Clean up on graceful exit
    workers.close()
    clients.close()
    context.term()

if __name__ == "__main__": main()
