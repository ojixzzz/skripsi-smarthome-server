from gevent import monkey
monkey.patch_all()

import os
import cgi
import redis
from flask import Flask, render_template, request, redirect, url_for
from flask.ext.socketio import SocketIO
from werkzeug import secure_filename
from PIL import Image

UPLOAD_IMAGE = 'static/images'
UPLOAD_IMAGE_THUMBS = 'static/images/thumbs'
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])

app = Flask(__name__)
app.debug = True

db = redis.StrictRedis('localhost', 6379, 0)
socketio = SocketIO(app)

raspberry_connected = False
client_connected = 0

sensor_data = None
tempMax = 0
tempMin = 0
sensor_count = 0

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

def list_files(path):
    files = []
    for name in os.listdir(path):
        if os.path.isfile(os.path.join(path, name)):
            files.append(name)
    return files

@app.route('/')
def main():
    return render_template('main.html')

@app.route('/upload_image', methods=['GET','POST'])
def upload_image():
    if request.method == 'POST':
        thumbnail_size = (100,100)
        file = request.files['file']
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            real_image = os.path.join(UPLOAD_IMAGE, filename)
            file.save(real_image)

            new_path = os.path.join(UPLOAD_IMAGE_THUMBS, filename)
            if os.path.exists(new_path):
                os.remove(new_path)

            im = Image.open(real_image)
            im.thumbnail(thumbnail_size)
            im.save(new_path, "JPEG")
            return 'OK'
    
    return '''
    <!doctype html>
    <title>Upload new File</title>
    <h1>Upload new File</h1>
    <form action="" method=post enctype=multipart/form-data>
      <p><input type=file name=file>
         <input type=submit value=Upload>
    </form>
    '''

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
    if sensor_count < 4:
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

@socketio.on('image_data', namespace='/socket_rpi')
def rpi_image_data(message):
    filerand = 'static/images/gambar%s.jpg' % randint(1,50)
    nf = open(filerand,'w')
    nf.write(message)
    nf.close()

if __name__ == '__main__':
    socketio.run(app, "0.0.0.0", port=5008)