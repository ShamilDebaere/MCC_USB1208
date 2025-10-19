import tkinter as tk
from mcculw import ul
from mcculw.enums import DigitalIODirection
import threading
import time
from datetime import datetime

BOARD_NUM = 0       #Board nr. Instacal
FIRSTPORTA = 10     #Port A
BIT = 0             #Channel 0

ul.d_config_port(BOARD_NUM, FIRSTPORTA, DigitalIODirection.OUT)

running = False
confirm_stop = False
stop_timer = None 

def set_relay(state: bool):
    ul.d_bit_out(BOARD_NUM, FIRSTPORTA, BIT, 1 if state else 0)

def relay_loop(on_time, off_time):
    global running
    while running:
        set_relay(True)
        for remaining in range(int(on_time), 0, -1):
            if not running:
                break
            countdown_label.config(text=f"Flush pump ON - switching off in {remaining}s")
            time.sleep(1)
        if not running:
            break
        set_relay(False)
        for remaining in range(int(off_time), 0, -1):
            if not running:
                break
            countdown_label.config(text=f"Flush pump OFF - switching on in {remaining}s")
            time.sleep(1)
    set_relay(False)
    countdown_label.config(text="Flush pump stopped")

def toggle_loop():
    global running, confirm_stop, stop_timer
    if not running:
        try:
            on_time = float(on_time_entry.get())
            off_time = float(off_time_entry.get())
        except ValueError:
            countdown_label.config(text="Enter numeric value")
            return
        root.focus()
        running = True
        toggle_button.config(text="Stop", bg="red")
        thread = threading.Thread(target=relay_loop, args=(on_time, off_time), daemon=True)
        thread.start()
    else:
        if not confirm_stop:
            confirm_stop = True
            toggle_button.config(text="Confirm Stop", bg="orange")
            stop_timer = root.after(3000, reset_stop_confirmation)
        else:
            if stop_timer:
                root.after_cancel(stop_timer)
            confirm_stop = False
            running = False
            toggle_button.config(text="Start", bg="lightgreen")
            set_relay(False)
            countdown_label.config(text="Flush pump stopped")

def reset_stop_confirmation():
    global confirm_stop
    confirm_stop = False
    if running:
        toggle_button.config(text="Stop", bg="red")

root = tk.Tk()
root.title("Flush Pump Control")
root.geometry("280x250")

tk.Label(root, text="Flushing period (seconds):").pack(pady=(10, 0))
on_time_entry = tk.Entry(root, width=10)
on_time_entry.insert(0, "300")
on_time_entry.pack(pady=5)

tk.Label(root, text="Closed period (seconds):").pack(pady=(10, 0))
off_time_entry = tk.Entry(root, width=10)
off_time_entry.insert(0, "600")
off_time_entry.pack(pady=5)

toggle_button = tk.Button(root, text="Start", width=15, bg="lightgreen", command=toggle_loop)
toggle_button.pack(pady=10)

countdown_label = tk.Label(root, text="Flush pump OFF", fg="blue", wraplength=250)
countdown_label.pack(pady=5)

root.mainloop()