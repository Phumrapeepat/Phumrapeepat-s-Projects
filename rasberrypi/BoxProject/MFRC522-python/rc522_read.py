import RPi.GPIO as GPIO
from mfrc522 import SimpleMFRC522

reader = SimpleMFRC522()

print("Place your RFID card/tag near the RC522...")

try:
    while True:
        id, text = reader.read()
        print("Card detected!")
        print("ID:", id)
        print("Text:", text.strip() if text else "(empty block)")
except KeyboardInterrupt:
    GPIO.cleanup()
