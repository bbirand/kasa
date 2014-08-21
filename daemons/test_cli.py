import zmq
import sys

def main():

    # Connect to the broker as a client
    port = "9800"
    context = zmq.Context()
    socket = context.socket(zmq.REQ)
    socket.connect("tcp://localhost:%s" % port)

    print "Sending request:'{}'".format(" ".join(sys.argv[1:]))
    socket.send(" ".join(sys.argv[1:]))

    message = socket.recv_multipart()
    print "Received reply:'{}'".format(message)


if __name__=="__main__": main()
