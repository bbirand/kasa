/*
 *
 * Kasa module for connecting with SensorTag
 *
 * Mostly an adapter over the node.js `sensortag` module
 *
 * (c) 2014 Berk Birand
 *
 */

var zmq = require('zmq');
var util = require('util');
var async = require('async');
var SensorTag = require('sensortag');

var port = 'tcp://127.0.0.1:9801';
var socket = zmq.socket('dealer');

// Connect to the broker
socket['identity'] = "SensorTag";
socket.connect(port);
console.log('connected to broker');

currently_connected_devs = {}

var queue = async.queue(function(arg, callback) {
      console.log('Starting processing' + timeStamp());
      process_msg(arg.client, arg.data);
      console.log('Done processing' + timeStamp() );
      callback();
}, 1);


function process_msg(client, data) {
    // Given client and the data as recieved from the zmq socket, obtain the reading

    msg = data.toString().split(' ')

    // Discover command
    if (msg[0] == "discover") {
        console.log("Discover");
        // First send list of currently connected devices, if any
        for (var k in currently_connected_devs) {
            console.log("Already connected to " + k);
            socket.send([client, '', k]);
        }

        // Then actually run the discovery routine
        SensorTag.discover(function(sensorTag) {
            console.log("Discovered: " + sensorTag);
            socket.send([client, '', sensorTag['uuid']]);
        });
        return
    }
    // Connect command
    else if (msg[0] == "connect") {
        console.log("Connecting to: " + msg[1]);
        target_uuid = msg[1];

        // If we are already connected, just return OK
        if (target_uuid in currently_connected_devs) {
            socket.send([client, '', 'OK']);
            console.log("Already connected.");
            return
        }

        SensorTag.discover(function(sensorTag) {
            // Connect to the right peripheral
            sensorTag.connect(function(err) {
                //TODO: Add to a global data structure that we're connected
                currently_connected_devs[target_uuid] = sensorTag;
                sensorTag.discoverServicesAndCharacteristics(function(){
                    socket.send([client, '', 'OK']);
                    console.log("Connected.");
                });
            });
        }, target_uuid); // Connect to device with 'uuid==msg[1]'
        return
    }
    // Disconnect command
    else if (msg[0] == "disconnect") {
        throw new Error('Disconnect not implemented');
    }

    //
    // Parse per-device arguments
    //
    cmd = msg[0]
    uuid = msg[1]
    args = msg.slice(2)

    // Make sure that we have a connection to the device
    if (!(uuid in currently_connected_devs)) {
        //TODO: If not, connect to the device?
        throw new Error('Not connected to ' + uuid);
    }

    // Fetch right SensorTag object
    sensorTag = currently_connected_devs[uuid];

    switch(cmd) {
        // Temperature chip
        case "enableIrTemperature":
            sensorTag.enableIrTemperature(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableIrTemperature":
            sensorTag.disableIrTemperature(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readIrTemperature":
            sensorTag.readIrTemperature(function(objectTemperature, ambientTemperature) {
                console.log('\tobject temperature = %d °C', objectTemperature.toFixed(1));
                console.log('\tambient temperature = %d °C', ambientTemperature.toFixed(1));
                socket.send([client, '', ambientTemperature.toFixed(2)]);
            });
            break;

        // Humidity chip
        case "enableHumidity":
            sensorTag.enableHumidity(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableHumidity":
            sensorTag.disableHumidity(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readHumidity":
            sensorTag.readHumidity(function(temp, humidity) {
                console.log('\ttemperature = %d °C', temp.toFixed(2));
                console.log('\thumidity = %d °C', humidity.toFixed(2));
                socket.send([client, '', humidity.toFixed(2)]); // + "," + temp.toFixed(2)]);
            });
            break;

        // Barometric Pressure chip
        case "enableBarometricPressure":
            sensorTag.enableBarometricPressure(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableBarometricPressure":
            sensorTag.disableBarometricPressure(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readBarometricPressure":
            sensorTag.readBarometricPressure(function(pressure) {
                console.log('\tpressure = %d °C', pressure.toFixed(12));
                socket.send([client, '', pressure.toFixed(2)]);
            });
            break;

        // Magnetometer chip
        case "enableMagnetometer":
            sensorTag.enableMagnetometer(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableMagnetometer":
            sensorTag.disableMagnetometer(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readMagnetometer":
            sensorTag.readMagnetometer(function(x,y,z) {
                console.log('\tmagnetometer = %d,%d,%d', x.toFixed(2), y.toFixed(2), z.toFixed(2));
                socket.send([client, '', [x,y,z].join() ]);
            });
            break;

        // Accelerometer chip
        case "enableAccelerometer":
            sensorTag.enableAccelerometer(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableAccelerometer":
            sensorTag.disableAccelerometer(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readAccelerometer":
            sensorTag.readAccelerometer(function(x,y,z) {
                console.log('\taccelerometer = %d,%d,%d', x.toFixed(2), y.toFixed(2), z.toFixed(2));
                socket.send([client, '', [x,y,z].join() ]);
            });
            break;

        // Gyroscope chip
        case "enableGyroscope":
            sensorTag.enableGyroscope(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "disableGyroscope":
            sensorTag.disableGyroscope(function() {
                socket.send([client, '', 'OK']);
            });
            break;
        case "readGyroscope":
            sensorTag.readGyroscope(function(x,y,z) {
                console.log('\tgyroscope = %d,%d,%d', x.toFixed(2), y.toFixed(2), z.toFixed(2));
                socket.send([client, '', [x,y,z].join() ]);
            });
            break;
    }

}


function timeStamp() {
    return ' - ' + ((new Date()).valueOf() - 1416344387300) ;
}

// Carry out the action upon receiving data
socket.on('message', function(client, empty, data) {
    console.log('From:\'' + client + '\'' + timeStamp() );
    console.log('Data:\'' + data   + '\'');
    queue.push({client: client, data: data});
    console.log('Pushed to queue' + timeStamp());
});


process.stdin.resume();//so the program will not close instantly

function exitHandler(options, err) {
    if (options.cleanup) {
        for (var k in currently_connected_devs) {
            console.log("Disconnecting " + k);
            currently_connected_devs[k].disconnect();
        }
        console.log("Done cleanup");
    }

    if (err) console.log(err.stack);
    
    if (options.exit) process.exit();
}

//do something when app is closing
process.on('exit', exitHandler.bind(null,{cleanup:true}));

//catches ctrl+c event
process.on('SIGINT', exitHandler.bind(null, {exit:true}));

//catches uncaught exceptions
process.on('uncaughtException', exitHandler.bind(null, {exit:true}));
