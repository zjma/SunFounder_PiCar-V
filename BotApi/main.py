from fastapi import Request, FastAPI
from fastapi.middleware.cors import CORSMiddleware
import json
from picar import new_driving_wheels as dw
from picar import Servo
from threading import Thread
import time

app = FastAPI()

DesiredState = {
    'PanSpeed': 0,
    'TiltSpeed': 0,
}

def applier():
    tiltServo = Servo.Servo(1)
    panServo = Servo.Servo(2)
    currentPanDegree = 90
    currentTiltDegree = 90

    while True:
        currentPanDegree = ensureGoodAngle(currentPanDegree+DesiredState['PanSpeed']*60)
        currentTiltDegree = ensureGoodAngle(currentTiltDegree+DesiredState['TiltSpeed']*60)
        tiltServo.write(currentTiltDegree)
        panServo.write(currentPanDegree)
        time.sleep(0.1)

T = Thread(target=applier).start()

app.add_middleware(
    CORSMiddleware,
    allow_origins=['*'],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/")
async def newState(request: Request):
    global DesiredState
    body = await request.body()
    DesiredState = json.loads(body)
