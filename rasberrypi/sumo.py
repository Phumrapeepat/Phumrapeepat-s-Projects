import RPi.GPIO as GPIO
import time
import random

# =========================
# ==== CONFIG & PINS ======
# =========================

GPIO.setmode(GPIO.BOARD)
GPIO.setwarnings(False)

# --- Ultrasonic pins (top array sharing TRIG_PIN) ---
TRIG_PIN   = 13
ECHO_PINR  = 19   # top right
ECHO_PINL  = 23   # top left
# Note: front upper (ECHO_PINM) removed

# --- Extra front-bottom ultrasonic (priority for attack) ---
TRIG_FRONT2 = 32   # bottom front trigger
ECHO_FRONT2 = 36   # bottom front echo

# --- IR edge sensors (0 = safe, 1 = edge) ---
BACK_SENSOR  = 5
FRONT_SENSOR = 3
# Left & Right IR sensors removed

# --- L298N motor pins ---
IN1_PIN = 31   # Left motor +
IN2_PIN = 33   # Left motor -
IN3_PIN = 35   # Right motor +
IN4_PIN = 37   # Right motor -

# --- Enable pins for PWM (speed control) ---
ENA_PIN = 40   # Left motor enable (PWM)
ENB_PIN = 38   # Right motor enable (PWM)

# --- PWM settings ---
PWM_FREQ = 100  # Hz

# --- Speeds (0–100) ---
SPEED_ATTACK     = 100   # full speed attack
SPEED_APPROACH   = 70    # forward when following opponent
SPEED_SEARCH     = 100 # spinning / turning while searching
SPEED_ESCAPE     = 90    # escaping edge

# --- Ultrasonic thresholds (cm) ---
FOLLOW_DIST  = 70.0      # within this = follow/face opponent
ATTACK_DIST  = 50.0      # within this = straight attack
NO_TARGET_DISTANCE = 200.0

# --- Ultrasonic timing ---
ULTRA_TIMEOUT = 0.02     # 20 ms timeout for each echo phase

# --- Turn timing (tune on your robot) ---
FULL_TURN_TIME = 0.55    # ~180° spin for edge escape

# --- Search direction: True = LEFT, False = RIGHT --

SEARCH_LEFT = False      # set True if you want left spin instead

# --- Detection stability counters ---
ATTACK_CONFIRM_HITS = 3   # bottom must see attack distance this many loops
FOLLOW_CONFIRM_HITS = 3    # sensors must see follow distance this many loops

DEBUG = True  # set False in competition

# =========================
# ===== GPIO SETUP ========
# =========================

# Motor pins
GPIO.setup(IN1_PIN, GPIO.OUT)
GPIO.setup(IN2_PIN, GPIO.OUT)
GPIO.setup(IN3_PIN, GPIO.OUT)
GPIO.setup(IN4_PIN, GPIO.OUT)

# PWM pins
GPIO.setup(ENA_PIN, GPIO.OUT)
GPIO.setup(ENB_PIN, GPIO.OUT)
ena_pwm = GPIO.PWM(ENA_PIN, PWM_FREQ)
enb_pwm = GPIO.PWM(ENB_PIN, PWM_FREQ)
ena_pwm.start(0)
enb_pwm.start(0)

# Ultrasonic top (left/right only)
GPIO.setup(TRIG_PIN, GPIO.OUT)
GPIO.setup(ECHO_PINR, GPIO.IN)
GPIO.setup(ECHO_PINL, GPIO.IN)

# Ultrasonic bottom
GPIO.setup(TRIG_FRONT2, GPIO.OUT)
GPIO.setup(ECHO_FRONT2, GPIO.IN)

# IR sensors (only front & back)
GPIO.setup(FRONT_SENSOR, GPIO.IN)
GPIO.setup(BACK_SENSOR,  GPIO.IN)

# =========================
# ===== MOTOR HELPERS =====
# =========================

def set_speed(left_speed, right_speed):
    left_speed  = max(0, min(100, left_speed))
    right_speed = max(0, min(100, right_speed))
    ena_pwm.ChangeDutyCycle(left_speed)
    enb_pwm.ChangeDutyCycle(right_speed)

def stop():
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.LOW)
    GPIO.output(IN3_PIN, GPIO.LOW)
    GPIO.output(IN4_PIN, GPIO.LOW)
    set_speed(0, 0)

def forward(speed=SPEED_ATTACK):
    GPIO.output(IN1_PIN, GPIO.HIGH)
    GPIO.output(IN2_PIN, GPIO.LOW)
    GPIO.output(IN3_PIN, GPIO.HIGH)
    GPIO.output(IN4_PIN, GPIO.LOW)
    set_speed(speed, speed)

def backward(speed=SPEED_ESCAPE):
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.HIGH)
    GPIO.output(IN3_PIN, GPIO.LOW)
    GPIO.output(IN4_PIN, GPIO.HIGH)
    set_speed(speed, speed)

def turn_left(speed=SPEED_SEARCH):
    GPIO.output(IN1_PIN, GPIO.HIGH)
    GPIO.output(IN2_PIN, GPIO.LOW)
    GPIO.output(IN3_PIN, GPIO.LOW)
    GPIO.output(IN4_PIN, GPIO.HIGH)
    set_speed(speed, speed)

def turn_right(speed=SPEED_SEARCH):
    GPIO.output(IN1_PIN, GPIO.LOW)
    GPIO.output(IN2_PIN, GPIO.HIGH)
    GPIO.output(IN3_PIN, GPIO.HIGH)
    GPIO.output(IN4_PIN, GPIO.LOW)
    set_speed(speed, speed)

# =========================
# === ULTRASONIC HELPERS ==
# =========================

def _measure_distance(trig_pin, echo_pin):
    """Measure distance (cm) using given TRIG/ECHO pins."""
    GPIO.output(trig_pin, GPIO.LOW)
    time.sleep(0.000002)
    GPIO.output(trig_pin, GPIO.HIGH)
    time.sleep(0.00001)
    GPIO.output(trig_pin, GPIO.LOW)

    # wait echo HIGH
    start_wait = time.monotonic()
    while GPIO.input(echo_pin) == 0:
        if time.monotonic() - start_wait > ULTRA_TIMEOUT:
            return NO_TARGET_DISTANCE

    pulse_start = time.monotonic()

    # wait echo LOW
    while GPIO.input(echo_pin) == 1:
        if time.monotonic() - pulse_start > ULTRA_TIMEOUT:
            return NO_TARGET_DISTANCE

    pulse_end = time.monotonic()
    pulse_duration = pulse_end - pulse_start

    distance = (pulse_duration * 34300.0) / 2.0  # cm

    if distance <= 0 or distance > NO_TARGET_DISTANCE:
        return NO_TARGET_DISTANCE
    return distance

def measure_front_bottom(samples=2):
    """Bottom front ultrasonic (priority for attack)."""
    dists = []
    for _ in range(samples):
        dists.append(_measure_distance(TRIG_FRONT2, ECHO_FRONT2))
        time.sleep(0.003)
    return min(dists)

def measure_left_top(samples=1):
    """Top left ultrasonic (for side detection)."""
    dists = []
    for _ in range(samples):
        dists.append(_measure_distance(TRIG_PIN, ECHO_PINL))
        time.sleep(0.003)
    return min(dists)

def measure_right_top(samples=1):
    """Top right ultrasonic (for side detection)."""
    dists = []
    for _ in range(samples):
        dists.append(_measure_distance(TRIG_PIN, ECHO_PINR))
        time.sleep(0.003)
    return min(dists)

# =========================
# === EDGE / IR LOGIC =====
# =========================

def read_edges():
    front = GPIO.input(FRONT_SENSOR)
    back  = GPIO.input(BACK_SENSOR)
    return front, back

def edge_escape():
    """Keep robot inside the ring using IR sensors.
       Return True if it performed an escape maneuver.
    """
    front, back = read_edges()

    if front or back:
        if DEBUG:
            print(f"[EDGE] F:{front} B:{back}")

    # Front edge: back away + full turn back into ring
    if front == 0:
        backward(SPEED_ESCAPE)
        time.sleep(0.4)
        if SEARCH_LEFT:
            if DEBUG:
                print("[EDGE] Front -> full LEFT turn")
            turn_left(SPEED_SEARCH)
        else:
            if DEBUG:
                print("[EDGE] Front -> full RIGHT turn")
            turn_right(SPEED_SEARCH)

        time.sleep(FULL_TURN_TIME)
        stop()
        return True

    # Back edge: go forward
    if back == 0:
        if DEBUG:
            print("[EDGE] Back -> forward escape")
        forward(SPEED_ESCAPE)
        time.sleep(0.4)
        stop()
        return True

    return False

# =========================
# ====== MAIN LOGIC =======
# =========================

def main():
    global SEARCH_LEFT
    # Detection counters
    bottom_attack_hits = 0
    bottom_follow_hits = 0
    left_follow_hits   = 0
    right_follow_hits  = 0

    try:
        if DEBUG:
            print("Starting sumo bot with counters in 2 seconds...")
        time.sleep(2)

        while True:
            # 1. IR edge protection
            if edge_escape():
                # reset counters after big movement
                bottom_attack_hits = 0
                bottom_follow_hits = 0
                left_follow_hits   = 0
                right_follow_hits  = 0
                continue

            # 2. Read ultrasonic distances
            d_bottom = measure_front_bottom()
            d_left   = measure_left_top()
            d_right  = measure_right_top()

            # 3. Raw detection flags
            raw_bottom_attack = d_bottom <= ATTACK_DIST
            raw_bottom_follow = (d_bottom <= FOLLOW_DIST)
            raw_left_follow   = (d_left   <= FOLLOW_DIST)
            raw_right_follow  = (d_right  <= FOLLOW_DIST)

            # 4. Update counters (debounce / confirm)
            bottom_attack_hits = bottom_attack_hits + 1 if raw_bottom_attack else 0
            bottom_follow_hits = bottom_follow_hits + 1 if raw_bottom_follow else 0
            left_follow_hits   = left_follow_hits   + 1 if raw_left_follow   else 0
            right_follow_hits  = right_follow_hits  + 1 if raw_right_follow  else 0

            # 5. Stable decisions based on counters
            stable_attack_bottom = bottom_attack_hits >= ATTACK_CONFIRM_HITS
            stable_follow_front  = bottom_follow_hits >= FOLLOW_CONFIRM_HITS
            stable_follow_left   = left_follow_hits   >= FOLLOW_CONFIRM_HITS
            stable_follow_right  = right_follow_hits  >= FOLLOW_CONFIRM_HITS

            if DEBUG:
                print(
                    f"[US] dB:{d_bottom:5.1f} dL:{d_left:5.1f} dR:{d_right:5.1f} | " 
                    f"hits A:{bottom_attack_hits} FB:{bottom_follow_hits} L:{left_follow_hits} R:{right_follow_hits}"
                )

            # 6. Behaviour

            # 6.1 ATTACK: confirmed bottom close distance
            if stable_attack_bottom:
                if DEBUG:
                    print(f"[ATTACK] Confirmed bottom target at {d_bottom:.1f} cm -> FULL SPEED!")
                forward(SPEED_ATTACK)

            # 6.2 FOLLOW/FACE: confirmed opponent in follow zone
            elif stable_follow_front or stable_follow_left or stable_follow_right:

                # Opponent in front (bottom) -> go forward to close distance
                if stable_follow_front:
                    if DEBUG:
                        print(f"[FOLLOW] Front confirmed at {d_bottom:.1f} cm -> FORWARD")
                    forward(SPEED_APPROACH)

                # Opponent on one side only -> rotate to face
                elif stable_follow_left or stable_follow_right:
                    if stable_follow_left and stable_follow_right:
                        forward(SPEED_APPROACH)
                    elif stable_follow_left and (not stable_follow_right):
                        if DEBUG:
                            print(f"[FOLLOW] LEFT confirmed at {d_left:.1f} cm -> turn LEFT")
                        turn_left(SPEED_SEARCH)
                        SEARCH_LEFT = True
                        time.sleep(0.1)
                        stop()
                    else:
                        if DEBUG:
                            print(f"[FOLLOW] RIGHT confirmed at {d_right:.1f} cm -> turn RIGHT")
                        turn_right(SPEED_SEARCH)
                        SEARCH_LEFT = False
                        time.sleep(0.1)
                        stop()

            # 6.3 SEARCH: nothing stable detected -> spin
            else:
                if SEARCH_LEFT:
                    if DEBUG:
                        print("[SEARCH] No stable target -> spin LEFT")
                    turn_left(SPEED_SEARCH)
                    time.sleep(0.1)
                else:
                    if DEBUG:
                        print("[SEARCH] No stable target -> spin RIGHT")
                    turn_right(SPEED_SEARCH)
                    time.sleep(0.05)

            time.sleep(0.01)

    except KeyboardInterrupt:
        print("Stopping (Ctrl+C)...")
    finally:
        stop()
        ena_pwm.stop()
        enb_pwm.stop()
        GPIO.cleanup()
        print("GPIO cleaned up.")

if __name__ == "__main__":
    main()
