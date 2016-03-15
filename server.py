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

@app.route('/')
def main():
    return render_template('main.html')

###########################
###   SOKET KE Client   ###
###########################
@socketio.on('connect', namespace='/socket')
def ws_conn():
    global client_connected
    client_connected = client_connected+1
    socketio.emit('msg', {'count': client_connected}, namespace='/socket')
    socketio.emit('relay_data', namespace="/socket_rpi")

@socketio.on('disconnect', namespace='/socket')
def ws_disconn():
    global client_connected
    client_connected = client_connected-1

@socketio.on('relay', namespace='/socket')
def ws_relay(message):
    socketio.emit('relay', message, namespace="/socket_rpi")

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
    socketio.emit('relay', message, namespace="/socket")

@socketio.on('relay_data', namespace='/socket_rpi')
def rpi_relay_data(message):
    socketio.emit('relay_data', message, namespace="/socket")

if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", port=5008)