import pygame
import threading
import queue
import time
import math
import requests

def get_external_value():
    URL = "http://10.82.228.165:8080/get?illum"
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
    pygame.display.set_caption("Illuminance & Polarizer Angle Demo")
    clock = pygame.time.Clock()
    scale_x = 100
    axis_y = height // 2
    points = []
    calibration_high = None
    calibration_low = None
    current_raw_value = 0
    smoothed_value = 0
    smoothing_alpha = 0.1
    data_queue = queue.Queue()
    worker_thread = threading.Thread(target=data_worker, args=(data_queue,))
    worker_thread.daemon = True
    worker_thread.start()
    font = pygame.font.SysFont("Arial", 20)
    button_cal_high = pygame.Rect(20, 20, 160, 40)
    button_cal_low = pygame.Rect(20, 70, 160, 40)
    start_time = pygame.time.get_ticks() / 1000.0
    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.MOUSEBUTTONDOWN:
                if button_cal_high.collidepoint(event.pos):
                    calibration_high = smoothed_value
                    print("Calibration High set to:", calibration_high)
                elif button_cal_low.collidepoint(event.pos):
                    calibration_low = smoothed_value
                    print("Calibration Low set to:", calibration_low)
        if not data_queue.empty():
            while not data_queue.empty():
                _, new_raw = data_queue.get()
                current_raw_value = new_raw
        smoothed_value = smoothing_alpha * current_raw_value + (1 - smoothing_alpha) * smoothed_value
        current_time = pygame.time.get_ticks() / 1000.0 - start_time
        points.append((current_time, smoothed_value))
        graph_width = 600
        offset = current_time * scale_x - graph_width
        points = [pt for pt in points if pt[0] * scale_x - offset >= 0]
        visible_values = [val for _, val in points]
        if visible_values:
            max_val = max(abs(val) for val in visible_values)
            scale_y = (height / 2 * 0.9) / max_val if max_val != 0 else 1
        else:
            scale_y = 1
        screen.fill((255, 255, 255))
        pygame.draw.rect(screen, (200, 200, 200), button_cal_high)
        high_text = font.render("Calibrate High", True, (0, 0, 0))
        screen.blit(high_text, (button_cal_high.x + 5, button_cal_high.y + 10))
        pygame.draw.rect(screen, (200, 200, 200), button_cal_low)
        low_text = font.render("Calibrate Low", True, (0, 0, 0))
        screen.blit(low_text, (button_cal_low.x + 5, button_cal_low.y + 10))
        graph_rect = pygame.Rect(0, 0, graph_width, height)
        pygame.draw.rect(screen, (0, 0, 0), graph_rect, 2)
        pygame.draw.line(screen, (0, 0, 0), (0, axis_y), (graph_width, axis_y), 2)
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
        if calibration_high is not None and calibration_low is not None and calibration_high > calibration_low:
            normalized_intensity = (smoothed_value - calibration_low) / (calibration_high - calibration_low)
            normalized_intensity = max(0.0, min(normalized_intensity, 1.0))
            try:
                theta_rad = math.acos(math.sqrt(normalized_intensity))
                theta_deg = math.degrees(theta_rad)
            except ValueError:
                theta_rad = math.pi / 2
                theta_deg = 90
        else:
            theta_rad = None
            theta_deg = None
        indicator_center = (750, 150)
        bar_length = 50
        if theta_rad is not None:
            end_x = indicator_center[0] + bar_length * math.cos(theta_rad)
            end_y = indicator_center[1] - bar_length * math.sin(theta_rad)
            pygame.draw.line(screen, (0, 0, 255), indicator_center, (end_x, end_y), 5)
            angle_text = font.render(f"Angle: {theta_deg:.1f}°", True, (0, 0, 0))
            screen.blit(angle_text, (indicator_center[0] - 40, indicator_center[1] + 60))
        else:
            no_cal_text = font.render("Not calibrated", True, (0, 0, 0))
            screen.blit(no_cal_text, (indicator_center[0] - 40, indicator_center[1] + 60))
        if calibration_high is not None:
            cal_high_text = font.render(f"High: {calibration_high:.1f}", True, (0, 0, 0))
            screen.blit(cal_high_text, (20, 120))
        if calibration_low is not None:
            cal_low_text = font.render(f"Low: {calibration_low:.1f}", True, (0, 0, 0))
            screen.blit(cal_low_text, (20, 150))
        pygame.display.flip()
        clock.tick(60)
    pygame.quit()

if __name__ == "__main__":
    main()


