import RPi.GPIO as GPIO
import pigpio
import time
servo = 26 # 37
servo2 = 18 #12
servo1=pigpio.pi()
servo1.set_mode(servo,pigpio.OUTPUT)
servo1.set_mode(servo2,pigpio.OUTPUT)
servo1.set_PWM_frequency(servo,50)


print("0 deg")
servo1.set_servo_pulsewidth(servo,1500);
servo1.set_servo_pulsewidth(servo2,1500);
time.sleep(3)

print("90 deg")
servo1.set_servo_pulsewidth(servo500);
servo1.set_servo_pulsewidth(servo2,500);
time.sleep(3) 

#print("180 deg")
#servo1.set_servo_pulsewidth(servo,2500);
#time.sleep(3)

#turning off servo
servo1.set_PWM_dutycycle(servo,0)
servo1.set_PWM_frequency(servo,0)
servo1.set_PWM_dutycycle(servo2,0)
servo1.set_PWM_frequency(servo2,0)