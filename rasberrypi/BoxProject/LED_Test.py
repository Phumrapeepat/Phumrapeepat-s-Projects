import RPi.GPIO as GPIO
import time
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
led1 = 11
led2 = 13
GPIO.setup(led1,GPIO.OUT)
GPIO.setup(led2,GPIO.OUT)
while True:
	for i in range(0,3):
		GPIO.output(led1,GPIO.HIGH) #LED On
		GPIO.output(led2,GPIO.HIGH) #LED On
		time.sleep(0.5)
		GPIO.output(led1,GPIO.LOW) #LED Off
		GPIO.output(led2,GPIO.LOW) #LED On
		time.sleep(0.5)
	time.sleep(0.2)
