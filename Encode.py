import face_recognition as fr
import cv2
import numpy as np
import hashlib

class encode(object):

    def __init__(self):
        self.state = False
        self.camera = None
        self.locknum = []
        self.label = ""
        self.domain = ""
        self.continuous_count = 0
        self.frame_toggle = False
        self.prev_rounded_avg = []
        self.continuous_count_threshold = 5
        # self.prev_cached_frame = []

    def __del__(self):
        if self.camera != None:
            self.camera.release()        

    # Generate a continuous feed of images from camera for encoding
    def gen_encodefeed(self):
        while self.camera != None and self.state == True:
            ret, frame = self.camera.read()
            if ret:
                # Only process every other frame
                if self.frame_toggle:
                    # Resize frame to 1/4 size for faster face recognition
                    small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)

                    # Convert small_frame from OpenCV's BGR to RGB 
                    rgb_small_frame = small_frame[:, :, ::-1]

                    # Encode faces in frame and check rounded_avg for matches
                    #
                    # If there is a continuous stream of matches, then the user
                    # is likely in frame and in a good position to take a picture
                    face_encoding = fr.face_encodings(rgb_small_frame)
                    if len(face_encoding) > 0:
                        rounded_avg = np.around([abs(x*10) for x in face_encoding[0]])
                        match = True
                        # If all the locknums match the previous rounded_avg add 
                        # to continous count
                        if self.prev_rounded_avg != []:
                            for i in self.locknum:
                                if rounded_avg[i] != self.prev_rounded_avg[i]:
                                    match = False
                                    break
                            if (match):
                                self.continuous_count = self.continuous_count + 1
                            else:
                                self.continuous_count = 0

                            self.prev_rounded_avg = rounded_avg
                        else: self.prev_rounded_avg = rounded_avg

                self.frame_toggle = not self.frame_toggle

                # Draw a circle for user to put their face in
                center = (round(frame.shape[1] / 2), round(frame.shape[0] / 2))
                color = (0, 0, 255)

                # print(self.continuous_count)
                if (self.continuous_count > self.continuous_count_threshold):
                    color = (0, 255, 0)
                #     self.prev_cached_frame = frame
                # else:
                #     self.prev_cached_frame = []

                cv2.circle(frame, center, 77, color, 7)
                ret, jpeg = cv2.imencode('.jpg', frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg.tobytes() + b'\r\n\r\n')

    # Start "encoding" phase
    def start(self, locknum, label, domain):
        self.state = True
        self.camera = cv2.VideoCapture(0)
        self.frame_toggle = True
        self.prev_rounded_avg = []
        # self.prev_cached_frame = []
        self.continuous_count = 0
        self.locknum = locknum
        self.label = label
        self.domain = domain

    # Ends the "encoding" process and outputs the password as needed
    def end(self):
        self.state = False
        frames = []
        for i in range(5):
            ret, frame = self.camera.read()
            if ret:
                frames.append(frame)
        # ret, frame = self.camera.read()
        #
        # frame = self.prev_cached_frame
        # if frame == []:
        #     print("frame cache empty")
        #     self.state = True
        #     return None

        # If camera capture failed then don't do anything
        if not ret:
            print("CAMERA DIDNT RETURN ANYTHING")
            self.state = True
            return None

        print(frame)
        # small_frame = cv2.resize(frame, (0, 0), fx=0.25, fy=0.25)
        # Convert frame from OpenCV's BGR color to RGB color
        rgb_frame = [x[:, :, ::-1] for x in frames]
        face_encodings = [fr.face_encodings(x) for x in rgb_frame]
        # print(face_encoding)
    
        # If the image did not yield a face then don't do anything either
        face_encoding = []
        for i in face_encodings:
            if i != []:
                face_encoding = i
                break
        if len(face_encoding) <= 0:
            print("FACE_ENCODING DIDNT RETURN ANYTHING")
            self.state = True
            return None

        # Select all the key values using locknum
        rounded_avg = np.around([abs(x*10) for x in face_encoding[0]])
        face_values = []
        for i in self.locknum:
            face_values.append(rounded_avg[i])

        # Build the prehash string and then hash it to get password
        prehash = self.label + ":" + self.domain + ':'.join([str(round(x)) for x in face_values])
        password = hashlib.sha256(prehash.encode('utf-8')).hexdigest()

        # Turn off everything and release camera
        self.state = False
        self.camera.release()

        # Return final password
        return password

    def stop(self):
        self.camera.release()
        self.state = False

