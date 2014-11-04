
var zmq = require('zmq');
var port = 'tcp://127.0.0.1:9801';

var socket = zmq.socket('dealer');

// Connect to the broker
socket['identity'] = "SensorTag";
socket.connect(port);
console.log('connected to broker');

// Carry out the action upon receiving data
socket.on('message', function(client, empty, data) {
    console.log('From:\'' + client + '\'');
    console.log('Data:\'' + data   + '\'');
});
