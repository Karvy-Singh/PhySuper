import pygame
import threading
import queue
import time
import math
import requests

import websocket
data_queue = queue.Queue()
SERVER_URI = "ws://10.134.21.123:8765"
def on_message(ws, message):
    illum = float(message)
    timestamp = pygame.time.get_ticks() / 1000.0
    data_queue.put((timestamp, illum))

def on_error(ws, error):
    print(f"[!] Error: {error}")

def on_close(ws, close_status_code, close_msg):
    print("[!] Connection closed.")

def on_open(ws):
    print(f"[+] Connected to sensor server at {SERVER_URI}")


def data_worker(data_queue):
    ws = websocket.WebSocketApp(
        SERVER_URI,
        on_open=on_open,
        on_message=on_message,
        on_error=on_error,
        on_close=on_close,
    )
    ws.run_forever()
def main():
    pygame.init()
    width, height = 900, 600
    screen = pygame.display.set_mode((width, height))
    pygame.display.set_caption("Illuminance Graph Demo")
    clock = pygame.time.Clock()
    scale_x = 100
    axis_y = int(height * 0.7)
    points = []
    current_raw_value = 0
    smoothed_value = 0
    smoothing_alpha = 0.1
    worker_thread = threading.Thread(target=data_worker, args=(data_queue,))
    worker_thread.daemon = True
    worker_thread.start()
    start_time = pygame.time.get_ticks() / 1000.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
        while not data_queue.empty():
            _, new_raw = data_queue.get()
            current_raw_value = new_raw
        smoothed_value = smoothing_alpha * current_raw_value + (1 - smoothing_alpha) * smoothed_value
        current_time = pygame.time.get_ticks() / 1000.0 - start_time
        points.append((current_time, smoothed_value))
        offset = current_time * scale_x - width
        points = [pt for pt in points if pt[0] * scale_x - offset >= 0]
        visible_values = [val for _, val in points]
        if visible_values:
            max_val = max(abs(val) for val in visible_values)
            scale_y = (height / 2 * 0.9) / max_val if max_val != 0 else 1
        else:
            scale_y = 1
        screen.fill((255, 255, 255))
        pygame.draw.line(screen, (0, 0, 0), (0, axis_y), (width, axis_y), 2)
        window_size = 5
        if len(points) >= 2:
            smoothed_points = []
            for i in range(len(points)):
                window = points[max(0, i - window_size // 2):min(len(points), i + window_size // 2 + 1)]
                if window:
                    avg_y = sum(p[1] for p in window) / len(window)
                    smoothed_points.append((points[i][0], avg_y))
            transformed_points = []
            for t_val, val in smoothed_points:
                x_coord = t_val * scale_x - offset
                y_coord = axis_y - val * scale_y
                transformed_points.append((int(x_coord), int(y_coord)))
            if len(transformed_points) >= 2:
                pygame.draw.lines(screen, (255, 0, 0), False, transformed_points, 2)
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()

