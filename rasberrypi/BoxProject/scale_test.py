import time
import sys
import RPi.GPIO as GPIO
from hx711 import HX711

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

print("Tare done! Add weight now...")

while True:
    try:
        # Prints the raw value (or weight if you set the reference unit)
        # We take the median of 5 readings to smooth out noise
        val = hx.get_weight(5)
        
        print(f"Reading: {val}")

        hx.power_down()
        hx.power_up()
        time.sleep(0.1)

    except (KeyboardInterrupt, SystemExit):
        cleanAndExit()