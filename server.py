from gevent import monkey
monkey.patch_all()

import cgi
import redis
from flask import Flask, render_template, request
from flask.ext.socketio import SocketIO

app = Flask(__name__)
db = redis.StrictRedis('localhost', 6379, 0)
socketio = SocketIO(app)

raspberry_connected = False
client_connected = 0

sensor_data = None
tempMax = 0
tempMin = 0
sensor_count = 0

@app.route('/')
def main():
    return render_template('main.html')

###########################
###   SOKET KE Client   ###
###########################
@socketio.on('connect', namespace='/socket')
def ws_conn():
    global raspberry_connected
    global client_connected
    client_connected = client_connected+1
    socketio.emit('status', {'data': '%s Klien terkoneksi' % client_connected}, namespace='/socket')
    if raspberry_connected:
        socketio.emit('relay_data', namespace="/socket_rpi")
        socketio.emit('sensor_data', sensor_data, namespace="/socket")
    else:
        socketio.emit('status', {'data': 'Raspberry tidak terkoneksi'}, namespace='/socket')

@socketio.on('disconnect', namespace='/socket')
def ws_disconn():
    global client_connected
    client_connected = client_connected-1

@socketio.on('relay', namespace='/socket')
def ws_relay(message):
    global raspberry_connected
    if raspberry_connected:
        socketio.emit('relay', message, namespace="/socket_rpi")
    else:
        data = {
            'relay_1': '1',
            'relay_2': '1',
            'relay_3': '1',
            'relay_4': '1',
        }
        socketio.emit('relay_data', data, namespace="/socket")
        socketio.emit('status', {'data': 'Raspberry tidak terkoneksi'}, namespace='/socket')

###########################
### SOKET KE RASPBERRY  ###
###########################
@socketio.on('connect', namespace='/socket_rpi')
def rpi_conn():
    global raspberry_connected
    raspberry_connected = True

@socketio.on('disconnect', namespace='/socket_rpi')
def rpi_disconn():
    global raspberry_connected
    raspberry_connected = False

@socketio.on('relay', namespace='/socket_rpi')
def rpi_relay(message):
    socketio.emit('relay_data', namespace="/socket_rpi")
    socketio.emit('relay', message, namespace="/socket")

@socketio.on('relay_data', namespace='/socket_rpi')
def rpi_relay_data(message):
    socketio.emit('relay_data', message, namespace="/socket")

@socketio.on('sensor_data', namespace='/socket_rpi')
def rpi_sensor_data(message):
    global sensor_data
    global sensor_count
    global tempMin
    global tempMax
    tempNow = message.get('temp')
    if sensor_count == 3:
        tempMax = tempNow
        tempMin = tempNow
    elif sensor_count > 100:
        sensor_count = 4

    if tempNow > tempMax:
        tempMax = tempNow
    if tempNow < tempMin:
        tempMin = tempNow

    datas = {
        'temp': tempNow,
        'temp_max': tempMax,
        'temp_min': tempMin,
    }
    if client_connected:
        socketio.emit('sensor_data', datas, namespace="/socket")
    sensor_data = datas
    sensor_count = sensor_count+1

if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", port=5008)