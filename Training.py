import numpy as np
import webbrowser
import Camfeed
import cv2
import face_recognition as fr
import random

class train(object):

    def __init__(self):
        self.state = False
        self.done = False
        self.camera = None
        self.src = []
        self.target_n = 0
        self.n = 0
        self.circle_offset_index = 0
        self.circle_offsets = [(0,0), (-20,20), (0,20), (20,20), (20,0), (20,-20), (0,-20), (-20,-20), (-20,0), (0,0)]

    def __del__(self):
        if self.camera != None:
            self.camera.release()        

    # Generate a continuous feed of images from camera for training
    def gen_trainfeed(self):
        while self.camera != None and self.state == True:
            ret, frame = self.camera.read()
            if ret:
                # Draw a circle for user to put their face in
                center = ((round(frame.shape[1] / 2) - self.circle_offsets[self.circle_offset_index][0], round(frame.shape[0] / 2) - self.circle_offsets[self.circle_offset_index][1]))
                cv2.circle(frame, center, 77, (0, 0, 255), 7)
                ret, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

    # Start "training" phase
    def start(self, n):
        self.done = False
        self.state = True
        self.n = 0
        self.target_n = n
        self.src = []
        self.camera = cv2.VideoCapture(0)
        self.circle_offset_index = 0

    # Captures a frame from camera and formats it for face_recognition
    def save_frame(self):
        ret, frame = self.camera.read()
        if ret:
            # Convert frame from OpenCV's BGR color to RGB  color
            rgb_frame = frame[:, :, ::-1]

            self.src.append(rgb_frame)
            self.n = self.n + 1
            self.circle_offset_index = self.circle_offset_index + 1
            self.circle_offset_index = self.circle_offset_index % len(self.circle_offsets)
            # If reached target number of sources, signal done
            if (self.n >= self.target_n):
                self.done = True

    # Ends the "training" process and outputs the key needed
    def end(self, n):
        self.state = False
        self.camera.release()

        # Encode all faces captured with face_recognition
        src_encodings = []
        for i in self.src:
            tmp = fr.face_encodings(i)
            if (len(tmp) != 0):
                src_encodings.append(tmp[0])

        # SUPER SCUFFED PROCESS, I KNOW. BUT THIS IS A HACKATHON. I COULD NOT
        # HAVE COME UP WITH ANYTHING BETTER IN A DAY.
        # 
        # PLEASE DON'T ACTUALLY USE THIS IN PRODUCTION, THIS IS A PROOF OF
        # CONCEPT.

        # Generate a rounded average of all 128 data points in the encoding
        rounded_avg = []
        for i in src_encodings:
            rounded_avg.append(np.around([abs(x*10) for x in i]))

        # Generate a locknum and values to use for recognition
        # Values can and should be discarded: They are not neccesarily to store
        locknum = []
        values = []
        for i in range(len(rounded_avg[0])):
            comp_stat = True
            comp_val = rounded_avg[0][i]
            for j in range(len(rounded_avg)):
                if rounded_avg[j][i] != comp_val:
                    comp_stat = False
                    break
            if comp_stat:
                locknum.append(i)
                values.append(comp_val)

        # If not locknum is not long enough, return nothing and start over again
        if len(locknum) < n:
            return None, None
        # Otherwise return first n indexes 
        return random.sample(locknum, k=n), random.sample(values, k=n)
        # return np.random.choice(locknum, size=None, replace=True, p=None)
        # TODO make this random to not focus on any features of the face too much
