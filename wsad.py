import pygame
import threading
import queue
import time
import math
import requests
import pyautogui

def get_external_value_left():
    URL = "http://192.168.221.221:8080/get?illum"
    try:
        r = requests.get(URL)
        r.raise_for_status()
        data = r.json()
        illum = data["buffer"]["illum"]["buffer"][0]
        return illum
    except Exception as e:
        print("Error in get_external_value_left:", e)
        return 0

def get_external_value_right():
    URL = "http://192.168.221.37:8080/get?illum"
    try:
        r = requests.get(URL)
        r.raise_for_status()
        data = r.json()
        illum = data["buffer"]["illum"]["buffer"][0]
        return illum
    except Exception as e:
        print("Error in get_external_value_right:", e)
        return 0

def data_worker_left(data_queue):
    while True:
        try:
            illum = get_external_value_left()
            timestamp = pygame.time.get_ticks() / 1000.0
            data_queue.put((timestamp, illum))
        except Exception as e:
            print("Error in data_worker_left:", e)

def data_worker_right(data_queue):
    while True:
        try:
            illum = get_external_value_right()
            timestamp = pygame.time.get_ticks() / 1000.0
            data_queue.put((timestamp, illum))
        except Exception as e:
            print("Error in data_worker_right:", e)

key_state = {"w": False, "a": False, "s": False, "d": False}


def get_left():
    if key_state["w"]:
        return "w"
    if key_state["s"]:
        return "s"
    return "None"

def get_right():
    if key_state["a"]:
        return "a"
    if key_state["d"]:
        return "d"
    return "None"


def press(key: str) -> None:
    """Press the key only if it isn’t already held down."""
    if not key_state[key]:
        pyautogui.keyDown(key)
        key_state[key] = True

def release(key: str) -> None:
    """Release the key only if it is currently held down."""
    if key_state[key]:
        pyautogui.keyUp(key)
        key_state[key] = False
def main():
    pygame.init()
    width, height = 650, 500
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("WASD Emulation via Polarizers")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("Arial", 20)
    left_cal_high = None
    left_cal_low = None
    right_cal_high = None
    right_cal_low = None
    left_current_raw = 0
    left_smoothed = 0
    right_current_raw = 0
    right_smoothed = 0
    smoothing_alpha = 0.1
    emulation_active = False
    left_queue = queue.Queue()
    right_queue = queue.Queue()
    left_thread = threading.Thread(target=data_worker_left, args=(left_queue,))
    left_thread.daemon = True
    left_thread.start()
    right_thread = threading.Thread(target=data_worker_right, args=(right_queue,))
    right_thread.daemon = True
    right_thread.start()
    button_left_cal_high = pygame.Rect(20, 20, 140, 40)
    button_left_cal_low = pygame.Rect(20, 70, 140, 40)
    button_right_cal_high = pygame.Rect(490, 20, 140, 40)
    button_right_cal_low = pygame.Rect(490, 70, 140, 40)
    button_start_stop = pygame.Rect(255, 20, 140, 40)
    left_zone  = None
    right_zone = None
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if button_left_cal_high.collidepoint(event.pos):
                    left_cal_high = left_smoothed
                    print("Left Cal High:", left_cal_high)
                elif button_left_cal_low.collidepoint(event.pos):
                    left_cal_low = left_smoothed
                    print("Left Cal Low:", left_cal_low)
                elif button_right_cal_high.collidepoint(event.pos):
                    right_cal_high = right_smoothed
                    print("Right Cal High:", right_cal_high)
                elif button_right_cal_low.collidepoint(event.pos):
                    right_cal_low = right_smoothed
                    print("Right Cal Low:", right_cal_low)
                elif button_start_stop.collidepoint(event.pos):
                    emulation_active = not emulation_active
                    if not emulation_active:
                        for k in key_state:
                            release(k)
                    print("Emulation Active:", emulation_active)
        if not left_queue.empty():
            while not left_queue.empty():
                _, val = left_queue.get()
                left_current_raw = val
        if not right_queue.empty():
            while not right_queue.empty():
                _, val = right_queue.get()
                right_current_raw = val
        left_smoothed = smoothing_alpha * left_current_raw + (1 - smoothing_alpha) * left_smoothed
        right_smoothed = smoothing_alpha * right_current_raw + (1 - smoothing_alpha) * right_smoothed
        left_angle = None
        right_angle = None
        if left_cal_high is not None and left_cal_low is not None and left_cal_high > left_cal_low:
            norm = (left_smoothed - left_cal_low) / (left_cal_high - left_cal_low)
            norm = max(0.0, min(norm, 1.0))
            try:
                left_angle = math.degrees(math.acos(math.sqrt(norm)))
            except:
                left_angle = 90
        if right_cal_high is not None and right_cal_low is not None and right_cal_high > right_cal_low:
            norm = (right_smoothed - right_cal_low) / (right_cal_high - right_cal_low)
            norm = max(0.0, min(norm, 1.0))
            try:
                right_angle = math.degrees(math.acos(math.sqrt(norm)))
            except:
                right_angle = 90
        left_key = "None"
        right_key = "None"

        if emulation_active:
            # ---- LEFT SENSOR -------------------------------------------
            new_left_zone = None
            if left_angle is not None:
                if left_angle >= 60:
                    new_left_zone = "hi"   # W
                elif left_angle <= 30:
                    new_left_zone = "lo"   # S
            # (angle between 30‑60 ° → None zone)

            if new_left_zone != left_zone:        # ❶ zone has changed!
                # first, release whatever was pressed before
                release("w"); release("s")
                if new_left_zone == "hi":
                    press("w")
                elif new_left_zone == "lo":
                    press("s")
                left_zone = new_left_zone

            # ---- RIGHT SENSOR ------------------------------------------
            new_right_zone = None
            if right_angle is not None:
                if right_angle >= 60:
                    new_right_zone = "hi"  # A
                elif right_angle <= 30:
                    new_right_zone = "lo"  # D

            if new_right_zone != right_zone:      # ❶ zone has changed!
                release("a"); release("d")
                if new_right_zone == "hi":
                    press("a")
                elif new_right_zone == "lo":
                    press("d")
                right_zone = new_right_zone
        else:
            # make absolutely sure nothing is stuck down
            for k in key_state:
                release(k)
                    
        screen.fill((255, 255, 255))
        pygame.draw.rect(screen, (200, 200, 200), button_left_cal_high)
        left_cal_high_text = font.render("L Cal High", True, (0, 0, 0))
        screen.blit(left_cal_high_text, (button_left_cal_high.x + 5, button_left_cal_high.y + 10))
        pygame.draw.rect(screen, (200, 200, 200), button_left_cal_low)
        left_cal_low_text = font.render("L Cal Low", True, (0, 0, 0))
        screen.blit(left_cal_low_text, (button_left_cal_low.x + 5, button_left_cal_low.y + 10))
        pygame.draw.rect(screen, (200, 200, 200), button_right_cal_high)
        right_cal_high_text = font.render("R Cal High", True, (0, 0, 0))
        screen.blit(right_cal_high_text, (button_right_cal_high.x + 5, button_right_cal_high.y + 10))
        pygame.draw.rect(screen, (200, 200, 200), button_right_cal_low)
        right_cal_low_text = font.render("R Cal Low", True, (0, 0, 0))
        screen.blit(right_cal_low_text, (button_right_cal_low.x + 5, button_right_cal_low.y + 10))
        pygame.draw.rect(screen, (200, 200, 200), button_start_stop)
        start_stop_text = font.render("Stop" if emulation_active else "Start", True, (0, 0, 0))
        screen.blit(start_stop_text, (button_start_stop.x + 20, button_start_stop.y + 10))
        start_indicator = font.render("Emulation Active" if emulation_active else "Emulation Inactive", True, (0, 0, 0))
        screen.blit(start_indicator, (button_start_stop.x, button_start_stop.y + 50))
        left_center = (100, 300)
        right_center = (500, 300)
        left_length = 50
        right_length = 50
        if left_angle is not None:
            left_rad = math.radians(left_angle)
        else:
            left_rad = 0
        if right_angle is not None:
            right_rad = math.radians(right_angle)
        else:
            right_rad = 0
        left_end = (left_center[0] + left_length * math.cos(left_rad), left_center[1] - left_length * math.sin(left_rad))
        right_end = (right_center[0] + right_length * math.cos(right_rad), right_center[1] - right_length * math.sin(right_rad))
        pygame.draw.line(screen, (0, 0, 255), left_center, left_end, 5)
        pygame.draw.line(screen, (0, 0, 255), right_center, right_end, 5)
        left_angle_text = font.render(f"{left_angle:.1f}°" if left_angle is not None else "N/A", True, (0, 0, 0))
        right_angle_text = font.render(f"{right_angle:.1f}°" if right_angle is not None else "N/A", True, (0, 0, 0))
        screen.blit(left_angle_text, (left_center[0] - 30, left_center[1] + 60))
        screen.blit(right_angle_text, (right_center[0] - 30, right_center[1] + 60))
        left_key_text = font.render(f"Left Key: {get_left()}", True, (0, 0, 0))
        right_key_text = font.render(f"Right Key: {get_right()}", True, (0, 0, 0))
        screen.blit(left_key_text, (left_center[0] - 40, left_center[1] + 100))
        screen.blit(right_key_text, (right_center[0] - 40, right_center[1] + 100))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()
    pyautogui.keyUp('s')
    pyautogui.keyUp('a')
    pyautogui.keyUp('w')
    pyautogui.keyUp('d')


if __name__ == "__main__":
    main()

