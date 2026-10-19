import RPi.GPIO as GPIO
import time

GPIO.setmode(GPIO.BOARD)

GPIO.setup(5,GPIO.OUT)
servo1=GPIO.PWM(5,50)

servo1.start(2)
#print("waiting for 2 sec")
#time.sleep(2)          
print("Turn back to 90 degrees for 2 sec")
servo1.ChangeDutyCycle(2)
time.sleep(2)
servo1.stop()
print("Turn back to 0 degrees")
#servo1.ChangeDutyCycle(2)


time.sleep(1)
servo1.ChangeDutyCycle(7)
time.sleep(2)

servo1.stop()
GPIO.clenup()
print("Finish")
