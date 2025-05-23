import pygame
import threading
import queue
import time
import math
import requests

def get_external_value():
    URL = "http://192.168.29.59:8080/get?illum"
    try:
        r = requests.get(URL)
        r.raise_for_status()
        data = r.json()
        illum = data["buffer"]["illum"]["buffer"][0]
        return illum
    except Exception as e:
        print("Error in get_external_value:", e)
        return 0

def data_worker(data_queue):
    while True:
        try:
            illum = get_external_value()
            timestamp = pygame.time.get_ticks() / 1000.0
            data_queue.put((timestamp, illum))
        except Exception as e:
            print("Error in data_worker:", e)

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
    data_queue = queue.Queue()
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

