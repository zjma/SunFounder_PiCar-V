from flask import Flask, jsonify, request
from flask_cors import CORS, cross_origin
import json
import logging
import picar
from picar import new_driving_wheels as dw
from picar import Servo
from pprint import pprint
from threading import Thread
import time

import signal
import sys

logging.getLogger('werkzeug').setLevel(logging.ERROR)

picar.setup()

ShuttingDown = False

def signal_handler(sig, frame):
    global ShuttingDown
    ShuttingDown = True
    print('Shutting down.')

signal.signal(signal.SIGINT, signal_handler)


class MunyaCar:
    def __init__(self):
        self.TargetLeftWheelVelocity = 0
        self.TargetRightWheelVelocity = 0
        self.CurrentLeftWheelVelocity = 0
        self.CurrentRightWheelVelocity = 0
        self.PanVelocity = 0
        self.TiltVelocity = 0
        self.CurrentTiltAngle = 90
        self.CurrentPanAngle = 90
        self.LastTargetUpdateTime = 0.0
bot = MunyaCar()

def apiMain():
    app = Flask(__name__)
    cors = CORS(app)
    app.config['CORS_HEADERS'] = 'Content-Type'

    @app.route('/', methods=['POST'])
    @cross_origin()
    def newTarget():
        bot.TargetLeftWheelVelocity = request.json['TargetLeftWheelVelocity']
        bot.TargetRightWheelVelocity = request.json['TargetRightWheelVelocity']
        bot.PanVelocity = request.json['PanVelocity']
        bot.TiltVelocity = request.json['TiltVelocity']
        bot.LastTargetUpdateTime = time.time()
        return jsonify({'Accepted':True})
    app.run(host='0.0.0.0', port=8002, debug=False, use_reloader=False)

def motorOperationMain():
    tiltServo = Servo.Servo(1)
    panServo = Servo.Servo(2)
    while not ShuttingDown:
        dw.setSpeed(int(bot.CurrentLeftWheelVelocity*100),int(bot.CurrentRightWheelVelocity*100))
        tiltServo.write(bot.CurrentTiltAngle)
        panServo.write(bot.CurrentPanAngle)

def currentUpdaterMain():
    # Parameters.
    DesiredMotorZeroToOneTimeInSeconds = 1.0
    DesiredServoTurnaroundTimeInSeconds = 0.1
    DesiredRefreshFrequency = 20
    
    # Derived.
    VelocityDiffMax = 0.6 / (DesiredRefreshFrequency * DesiredMotorZeroToOneTimeInSeconds)
    AngleDiffMax = 180.0 / (DesiredRefreshFrequency * DesiredServoTurnaroundTimeInSeconds)
    
    def getNextVelocity(current, target):
        if abs(target)>=0.4 and current*target>0 and abs(current)<0.4:
            return 0.4*current/abs(current)

        diff = target-current
        diff = min(diff,VelocityDiffMax)
        diff = max(diff,-VelocityDiffMax)
        return current+diff

    def getNextAngle(current, velocity):
        next = current + velocity*AngleDiffMax
        next = min(next, 180)
        next = max(next, 0)
        return next

    while not ShuttingDown:
        bot.CurrentLeftWheelVelocity = getNextVelocity(bot.CurrentLeftWheelVelocity, bot.TargetLeftWheelVelocity)
        bot.CurrentRightWheelVelocity = getNextVelocity(bot.CurrentRightWheelVelocity, bot.TargetRightWheelVelocity)
        bot.CurrentTiltAngle = getNextAngle(bot.CurrentTiltAngle, bot.TiltVelocity)
        bot.CurrentPanAngle = getNextAngle(bot.CurrentPanAngle, bot.PanVelocity)
        time.sleep(1/DesiredRefreshFrequency)

def targetUpdaterMain():
    while not ShuttingDown:
        if bot.LastTargetUpdateTime < time.time()-0.1:
            bot.TargetLeftWheelVelocity = 0
            bot.TargetRightWheelVelocity = 0
        time.sleep(0.05)

if __name__=='__main__':
    apiThread = Thread(target=apiMain, daemon=True)
    motorOperationThread = Thread(target=motorOperationMain)
    currentUpdaterThread = Thread(target=currentUpdaterMain)
    targetUpdaterThread = Thread(target=targetUpdaterMain)
    apiThread.start()
    motorOperationThread.start()
    currentUpdaterThread.start()
    targetUpdaterThread.start()
    motorOperationThread.join()
    currentUpdaterThread.join()
    targetUpdaterThread.join()

