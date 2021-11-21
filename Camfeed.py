import cv2
import datetime
import os

def gen_feed(camera):
    while True:
        frame = camera.get_frame()
        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n\r\n')

class camera(object):
    def __init__(self):
        self.video = cv2.VideoCapture(0)

    def __del__(self):
        self.video.release()        

    def get_frame(self):
        ret, frame = self.video.read()
        ret, jpeg = cv2.imencode('.jpg', frame)
        return jpeg.tobytes()

    def save_frame(self):
        ret, frame = self.video.read()
        now = datetime.datetime.now()
        p = os.path.sep.join(["snapshots", "{}.jpg".format(str(now).replace(":",''))])
        cv2.imwrite(p, frame)

