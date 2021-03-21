
# import the necessary packages
from __future__ import print_function
from imutils.video import VideoStream
import argparse
import imutils
import time
import cv2
import os
import serial

def setupSerial(baudRate, serialPortName):    
    global  serialPort    
    serialPort = serial.Serial(port= serialPortName, baudrate = baudRate, timeout=0, rtscts=True)
    ("Serial port " + serialPortName + " opened  Baudrate " + str(baudRate))
    waitForArduino()

def sendToArduino(stringToSend):
# this adds the start- and end-markers before sending
    global startMarker, endMarker, serialPort
    stringWithMarkers = (startMarker)
    stringWithMarkers += stringToSend
    stringWithMarkers += (endMarker)
    serialPort.write(stringWithMarkers.encode('utf-8')) # encode needed for Python3

def recvLikeArduino():
    global startMarker, endMarker, serialPort, dataStarted, dataBuf, messageComplete
    if serialPort.inWaiting() > 0 and messageComplete == False:
        x = serialPort.read().decode("utf-8") # decode needed for Python3
        if dataStarted == True:
            if x != endMarker:
                dataBuf = dataBuf + x
            else:
                dataStarted = False
                messageComplete = True
        elif x == startMarker:
            dataBuf = ''
            dataStarted = True    
    if (messageComplete == True):
        messageComplete = False
        serialPort.reset_input_buffer()
        return dataBuf
    else:
        return "XXX"

def waitForArduino():
    # wait until the Arduino sends 'Arduino is ready' - allows time for Arduino reset
    # it also ensures that any bytes left over from a previous message are discarded
    print("Waiting for Arduino to reset")
    msg = ""
    while msg.find("Arduino is ready") == -1:
        msg = recvLikeArduino()
        if not (msg == 'XXX'):
            print(msg)

# position servos to present object at center of the frame
def mapServoPosition (x, y):
    global panAngle
    global tiltAngle
    global TiltPan
    angleStep = 1
    if (x < 220):
        tiltAngle += angleStep
        if tiltAngle > 140:
            tiltAngle = 140   
    if (x > 280):
        tiltAngle -= angleStep
        if tiltAngle < 40:
            tiltAngle = 40 
    if (y < 160):
        panAngle -= angleStep
        if panAngle < 40:
            panAngle = 40 
    if (y > 210):  
        panAngle += angleStep
        if panAngle > 140:
            panAngle = 140
    TiltPan = ("%s,%s"%(tiltAngle, panAngle))
    sendToArduino(str(TiltPan))

def _map(x, in_min, in_max, out_min, out_max):
    return int((x - in_min) * (out_max - out_min) / (in_max - in_min) + out_min)

# initialize the video stream and allow the camera sensor to warmup
print("[INFO] waiting for camera to warmup...")
vs = VideoStream(0).start()
time.sleep(2.0)

# define the lower and upper boundaries of the object
# to be tracked in the HSV color space
# colorLower = (162, 100, 100) #Red
# colorUpper = (182, 255, 255) #Red
# colorLower = (23, 100, 100) #Green
# colorUpper = (43, 255, 255) #Green
colorLower = (144, 100, 100) #Violet
colorUpper = (164, 255, 255) #Violet

# Initialize angle servos at 90-90 position
global panAngle
panAngle = 90
global tiltAngle
tiltAngle = 90
global distanceSensorValue
distanceSensorValue = 0
global TiltPan
TiltPan = "90,90"
global startMarker 
startMarker = '<'
global endMarker
endMarker = '>'
global dataStarted
dataStarted = False
messageComplete = False
dataBuf = ""
setupSerial(115200, "/dev/ttyACM0")
sendToArduino(TiltPan)

# loop over the frames from the video stream
while True:
# grab the next frame from the video stream, Invert 180o, resize the
# frame, and convert it to the HSV color space
    arduinoReply = recvLikeArduino()
    if not (arduinoReply == 'XXX'):
        print ("{ Arduino: %s  }" %(arduinoReply))
        
    frame = vs.read()
    frame = imutils.resize(frame, width=400)
    hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

# construct a mask for the object color, then perform
# a series of dilations and erosions to remove any small
# blobs left in the mask
    mask = cv2.inRange(hsv, colorLower, colorUpper)
    mask = cv2.erode(mask, None, iterations=2)
    mask = cv2.dilate(mask, None, iterations=2)

# find contours in the mask and initialize the current
# (x, y) center of the object
    cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
    cnts = cnts[0] #if imutils.is_cv2() else cnts[1]
    center = None

# only proceed if at least one contour was found
    if len(cnts) > 0:
# find the largest contour in the mask, then use
# it to compute the minimum enclosing circle and
# centroid
        c = max(cnts, key=cv2.contourArea)
        ((x, y), radius) = cv2.minEnclosingCircle(c)
        M = cv2.moments(c)
        center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))

# only proceed if the radius meets a minimum size
        if radius > 10:
# draw the circle and centroid on the frame,
# then update the list of tracked points
            cv2.circle(frame, (int(x), int(y)), int(radius),(0, 255, 255), 2)
            cv2.circle(frame, center, 5, (0, 0, 255), -1)
# position Servo at center of circle
            mapServoPosition(int(x), int(y))
# show the frame to our screen
    cv2.imshow("Frame", frame)

# if [ESC] key is pressed, stop the loop
    key = cv2.waitKey(1) & 0xFF
    if key == 27:
        sendToArduino("90,90")
        time.sleep(2.0)
        break

# do a bit of cleanup
print("\n [INFO] Exiting Program and cleanup stuff \n")
cv2.destroyAllWindows()
vs.stop()