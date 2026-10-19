# 4x3 keypad password checker
# '*' = check password
# '#' = reset / clear password

import RPi.GPIO as GPIO
import time
import yagmail
import secrets
import lcddriver
import pigpio
import threading
import sys
from mfrc522 import SimpleMFRC522
from hx711 import HX711

reader = SimpleMFRC522()

GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)


lcd = lcddriver.lcd()


yag = yagmail.SMTP('projectmailbox999@gmail.com','clkn qkdf oblw fito')
receiver= 'nitipat.rue@student.mahidol.edu'

startFlag = False
maxPinFlag = False
openedFlag = False
cardFlag = False

# -------- GPIO PIN SETUP --------
# Rows / Lines
L1 = 7
L2 = 15
L3 = 16
L4 = 18

# Columns (4x3 keypad has only 3 columns)
C1 = 32
C2 = 38
C3 = 40

# Servo Motor
servo = 18
servo1=pigpio.pi()
servo1.set_mode(servo,pigpio.OUTPUT)
servo1.set_PWM_frequency(servo,50)

# Loadcell
# --- CONFIGURATION ---
dout_pin = 29  # DT (Pin 29)
pd_sck_pin = 31  # SCK (Pin 31)

# Create the HX711 object
hx = HX711(dout_pin, pd_sck_pin)

# Set reading format
hx.set_reading_format("MSB", "MSB")

# HOW TO CALIBRATE:
# 1. Run this script.
# 2. The scale will "Tare" (zero itself) automatically.
# 3. Place a known weight (e.g., a phone, a can of soda) on the scale.
# 4. Look at the value printed. 
# 5. Divide the Value by the Known Weight. 
#    Example: If value is 45000 and weight is 100g. 
#    45000 / 100 = 450.
# 6. Stop the script, uncomment the line below, and put '450' in the parentheses.
hx.set_reference_unit(98.2) 

hx.reset()
hx.tare()

# The GPIO pin of the column of the key that is currently
# being held down or -1 if no key is pressed
keypadPressed = -1

secretCode = "4789"
user_input = ""

# -------- GPIO INIT --------

GPIO.setup(L1, GPIO.OUT)
GPIO.setup(L2, GPIO.OUT)
GPIO.setup(L3, GPIO.OUT)
GPIO.setup(L4, GPIO.OUT)

# Use internal pull-down resistors for columns
GPIO.setup(C1, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C2, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
GPIO.setup(C3, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)


# -------- CALLBACK & HELPERS --------
def keypadCallback(channel):
    """
    Called when a key makes the column line go HIGH.
    We just record *which column* is currently active,
    so we can wait for the key to be released.
    """
    global keypadPressed
    if keypadPressed == -1:
        keypadPressed = channel


GPIO.add_event_detect(C1, GPIO.RISING, callback=keypadCallback, bouncetime=200)
GPIO.add_event_detect(C2, GPIO.RISING, callback=keypadCallback, bouncetime=200)
GPIO.add_event_detect(C3, GPIO.RISING, callback=keypadCallback, bouncetime=200)


def setAllLines(state):
    """Set all row lines to the same state (HIGH or LOW)."""
    GPIO.output(L1, state)
    GPIO.output(L2, state)
    GPIO.output(L3, state)
    GPIO.output(L4, state)


def handleKey(key):
    """
    Handle what happens when a key is detected.
    '*' = check password
    '#' = reset / clear
    others = append to input
    """
    global user_input
    global startFlag
    global maxPinFlag
    global code
    global openedFlag    

    if key == '*':
        if startFlag == False and openedFlag == False:
            startFlag = True
            code = ''.join(str(secrets.randbelow(10)) for _ in range(6))
            print("Please Enter Code")
            lcd.lcd_clear()
            lcd.lcd_display_string("Enter Code:",1)
            contents=[

                "MailBox999 OTP : " + str(code)
            ]
            yag.send(receiver,'Open Box requested',contents)
        elif openedFlag == True:
            closeBox()
            
        elif maxPinFlag == True:
            # Check password
            if user_input == code:
                print("Code correct!")
                lcd.lcd_clear()
                lcd.lcd_display_string("Code Correct!",1)
                openBox()
            else:
                print("Incorrect code!")
                maxPinFlag = False
                lcd.lcd_clear()
                lcd.lcd_display_string("Incorrect Code",1)
                lcd.lcd_display_string("try again",2)
                time.sleep(3)
                lcd.lcd_clear()
                lcd.lcd_display_string("Enter Code:",1)
                # TODO: Sound an alarm, send an email, etc.
            user_input = ""  # clear after checking
            

    elif key == '#':
        # Reset the input
        print("Input reset!")
        user_input = ""
        lcd.lcd_clear()
        lcd.lcd_display_string("Enter Code:",1)
        lcd.lcd_display_string(user_input,2)

    else:
        if startFlag == True:
            if len(user_input) < 6:
                # Normal digit pressed
                user_input += key
                print("Current input:", user_input)
                lcd.lcd_clear()
                lcd.lcd_display_string("Enter Code:",1)
                lcd.lcd_display_string(user_input,2)
                if len(user_input) == 6:
                    maxPinFlag = True
                    
            else:
                print("Current input:" + user_input + " (exceed limit bit)")
        elif startFlag==False and openedFlag == False :
            print("Press '*' to start")
            lcd.lcd_display_string("Press '*'",1)
            lcd.lcd_display_string("to start",2)
            
            
        else :
            print("Press '*' to close")
            lcd.lcd_clear()
            lcd.lcd_display_string("Press '*'",1)
            lcd.lcd_display_string("to close",2)
            


def readLine(line, characters):
    """
    Scan one row.
    characters = [key on C1, key on C2, key on C3]
    """
    GPIO.output(line, GPIO.HIGH)

    # C1
    if GPIO.input(C1) == 1:
        handleKey(characters[0])
        # wait until key is released
        while GPIO.input(C1) == 1:
            time.sleep(0.02)

    # C2
    elif GPIO.input(C2) == 1:
        handleKey(characters[1])
        while GPIO.input(C2) == 1:
            time.sleep(0.02)

    # C3
    elif GPIO.input(C3) == 1:
        handleKey(characters[2])
        while GPIO.input(C3) == 1:
            time.sleep(0.02)

    GPIO.output(line, GPIO.LOW)
    
def closeBox() :
    global user_input
    global startFlag
    global maxPinFlag
    global code
    global openedFlag
    global cardFlag
    
    print("Closing Box")
    openedFlag = False
    startFlag = False
    cardFlag = False
    # Code for servo to close box
    lcd.lcd_clear()
    lcd.lcd_display_string("Box Closed",1)
    servo1.set_servo_pulsewidth(servo,1500);
    time.sleep(3)
    
def openBox() :
    global user_input
    global startFlag
    global maxPinFlag
    global code
    global openedFlag   
    
    openedFlag = True
    maxPinFlag = False
    lcd.lcd_display_string("Opening Box",1)
    print("Opening Box")
    servo1.set_servo_pulsewidth(servo,500);
    time.sleep(3)
    lcd.lcd_clear()
    lcd.lcd_display_string("Press '*'",1)
    lcd.lcd_display_string("to close",2)
    yag.send(receiver,'test',"The box is open")
    # TODO: Unlock a door, turn a light on, etc.
    # Servo opening box
    
    
def checkRFID():
    global user_input
    global startFlag
    global maxPinFlag
    global code
    global openedFlag
    global cardFlag
    try:
        while True:
            id, text = reader.read()
            if id == 426755380979:
                cardFlag = True
                print("cardFlag = " + str(cardFlag))
                openBox()
            
    except KeyboardInterrupt:
        print("\nApplication stopped!")

    finally:
        GPIO.cleanup()
        
def checkWeight():
    global user_input
    global startFlag
    global maxPinFlag
    global code
    global openedFlag
    global hx
    try:
        oldValue = -100 #Start value
        alertCount = 0
        putCount = 0
        while True:
            if cardFlag == False:
                # Prints the raw value (or weight if you set the reference unit)
                # We take the median of 5 readings to smooth out noise
                value = hx.get_weight(5)
                
                if oldValue != -100: #Not first time
                    if oldValue - value > 50:
                        alertCount += 1
                        if alertCount >= 10:
                            print("Package Missing!")
                            yag.send(receiver,'Alert!',"The Packet is Missing")
                            alertCount = 0
                            putCount = 0
                    elif value - oldValue > 50:
                        alertCount = 0
                        putCount += 1
                        if putCount >= 10:
                            oldValue = value
                    else:
                        alertCount = 0
                        putCount = 0
                
            
                print(f"Reading: value = {value}, oldValue = {oldValue}")

                hx.power_down()
                hx.power_up()
                time.sleep(1)
                
                if alertCount == 0 and putCount == 0                                              : #If not alerting always update oldValue
                    oldValue = value
                    
            else: #Reset after box close from card
                oldValue = -100
            
    except KeyboardInterrupt:
        print("\nApplication stopped!")

    finally:
        GPIO.cleanup()

# -------- MAIN LOOP --------
try:
    lcd.lcd_clear()
    lcd.lcd_display_string("Box Locked",1)
    lcd.lcd_display_string("Press *",2)
    threadA = threading.Thread(target = checkRFID)
    threadB = threading.Thread(target = checkWeight)
    threadA.start()
    threadB.start()

    while True:
        
        # If a key is held, wait until it is released
        if keypadPressed != -1:
            setAllLines(GPIO.HIGH)
            # When the column line goes LOW again, key is released
            if GPIO.input(keypadPressed) == 0:
                keypadPressed = -1
            time.sleep(0.05)

        else:
            # Scan keypad rows
            readLine(L1, ["1", "2", "3"])
            readLine(L2, ["4", "5", "6"])
            readLine(L3, ["7", "8", "9"])
            readLine(L4, ["*", "0", "#"])
            time.sleep(0.1)

except KeyboardInterrupt:
    print("\nApplication stopped!")

finally:
    GPIO.cleanup()