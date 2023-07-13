#!/usr/bin/python3 python

import RPi.GPIO as GPIO
import threading
import time
import requests
from mfrc522 import SimpleMFRC522
from gpiozero import Buzzer, LED

import json
import logging
from AWSIoTPythonSDK.MQTTLib import AWSIoTMQTTShadowClient
from time import sleep


# initialize GPIO
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)
GPIO.cleanup()


GPIO.setwarnings(False)
GPIO.setmode(GPIO.BCM)

relay = 18
buzzer = 26
ir = 23

red = LED(16)
yellow = LED(20)
green = LED(21)

GPIO.setup(relay, GPIO.OUT)
GPIO.setup(ir, GPIO.IN)
GPIO.output(relay, 0)

reader = SimpleMFRC522()
buzzer1 = Buzzer(26)
GPIO.setup(buzzer, GPIO.OUT)
# buzzer1.beep(0.1, 0.1, 1)

objectDetected = False
unregisteredTagDetected = 0
timeUp = False
duration = 5


LEDPIN=16
relay = 18
GPIO.setmode(GPIO.BCM)
GPIO.setwarnings(False)    # Ignore warning for now
GPIO.setup(LEDPIN, GPIO.OUT, initial=GPIO.LOW)
GPIO.setup(relay, GPIO.OUT)


class shadowCallbackContainer:
    def __init__(self, deviceShadowInstance):
        self.deviceShadowInstance = deviceShadowInstance

    # Custom Shadow callback
    def customShadowCallback_Delta(self, payload, responseStatus, token):
        # payload is a JSON string ready to be parsed using json.loads(...)
        # in both Py2.x and Py3.x
        global LEDPIN
        payloadDict = json.loads(payload)
        isLockOn = payloadDict["state"]['delta']["on"]
        if isLockOn == True:
            GPIO.output(relay, 0)

            green.off()
        else:
            GPIO.output(relay, 1)
            green.on()

myShadowClient = AWSIoTMQTTShadowClient("myClient")
myShadowClient.configureEndpoint("az655a0dlvx64-ats.iot.us-east-1.amazonaws.com", 8883)
myShadowClient.configureCredentials("/home/pi/Documents/fyp/certs/AmazonRootCA1.pem", "/home/pi/Documents/fyp/certs/b7089c83dd-private.pem.key", "/home/pi/Documents/fyp/certs/b7089c83dd-certificate.pem.crt")
myShadowClient.configureConnectDisconnectTimeout(10) # 10 seconds
myShadowClient.configureMQTTOperationTimeout(5) # 5 seconds

print(myShadowClient.connect())
print("connected")
myDeviceShadowHandler = myShadowClient.createShadowHandlerWithName("my_pi", True)
shadowCallbackContainerBot = shadowCallbackContainer(myDeviceShadowHandler)
                
def countdownTimer():
    global timeUp
    global duration
    global barcodeArrayAsString
    while True:
        duration = 5
        time.sleep(0.5)
        reader = SimpleMFRC522()
        barcodeArrayAsString = ""
        while objectDetected:
            time.sleep(1)
            duration = duration - 1
            print(duration)
            if duration <= 0:
                timeUp = True
                print("Times up")
                scanUncheckedTag()
                break 

def objectDetector():
    global objectDetected
    global unregisteredTagDetected
    while True:
        time.sleep(0.01)
        if GPIO.input(ir) == False:
            red.off()
            yellow.on()
            objectDetected = True
        else:
            red.on()
            yellow.off()
            objectDetected = False
            unregisteredTagDetected = 0

def tagDetector():
    global unregisteredTagDetected
    global barcodeArrayAsString;
    while True:
        time.sleep(0.1)  
        value = reader.read_id()
        text = '{:08x}'.format(value)[0:8]
        buzzer1.beep(0.1, 0.1, 1)
        print(text)
        barcodeArrayAsString = barcodeArrayAsString + "," + text.replace(' ', '')
        print(barcodeArrayAsString)


def scanUncheckedTag():
    response = requests.post("https://zj9ohmm9uh.execute-api.us-east-1.amazonaws.com/dev/barcode/verify?" + "barcode=" + barcodeArrayAsString)
    jsonData = response.json()
    print("Tag: ")
    print(jsonData)
    if (jsonData['status'] == 'found'):
        buzzer1.beep(0.1, 0.1, 5)
    else:
        buzzer1.beep(0.1, 0.1, 2)

def qrCodeChecker():
    while True:
        value = input()
        print(value)
        verifyCode(value)

def verifyCode(myQr):
    response = requests.post("https://zj9ohmm9uh.execute-api.us-east-1.amazonaws.com/dev/my-qr/access?" + "qr=" + myQr)
    jsonData = response.json()
    
    print("qr: ")
    print(jsonData)

    if (jsonData['status'] == 'not found' or jsonData['status'] == 'out of operation'):
        buzzer1.beep(0.1, 0.1, 5)
    else:
        buzzer1.beep(0.1, 0.1, 2)


def iotCoreListener():
    while True:
        time.sleep(1)
        myDeviceShadowHandler.shadowGet(shadowCallbackContainerBot.customShadowCallback_Delta, 5)

try:
    threadTimer = threading.Thread(target=countdownTimer, args=())
    threadObjectDetector = threading.Thread(target=objectDetector, args=())
    threadTagDetector = threading.Thread(target=tagDetector, args=())
    threadQrCodeChecker = threading.Thread(target=qrCodeChecker, args=())
    threadIotCoreListener = threading.Thread(target=iotCoreListener, args=())
    
    threadTagDetector.start()
    threadTimer.start()
    threadObjectDetector.start()
    threadQrCodeChecker.start()
    threadIotCoreListener.start()
        
    while False:
        print("Reading")

        value = reader.read()

        text = value[1].strip()
        print(text)
        if (reader.read() == "qq"):
            # unlock solenoid lock
            GPIO.output(relay, 1)
        else:
            # lock solenoid lock 
            GPIO.output(relay, 0)
        buzzer1.beep(0.1, 0.1, 1)
        
	
finally:
    print("")
