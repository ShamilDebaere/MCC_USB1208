import tkinter as tk
from mcculw import ul
from mcculw.enums import ULRange, DigitalIODirection, DigitalPortType
from mcculw.device_info import DaqDeviceInfo
import threading
import time
import csv
from datetime import datetime

BOARD_NUM = 0
AI_CH = 0
PORT = DigitalPortType.FIRSTPORTA
BIT = 0

ul.d_config_port(BOARD_NUM, PORT, DigitalIODirection.OUT)
daq_info = DaqDeviceInfo(BOARD_NUM)

running = False
confirm_stop = False
stop_timer = None
relay_on = False
csv_file = None
csv_writer = None

def set_relay(state: bool):
    global relay_on
    ul.d_bit_out(BOARD_NUM, PORT, BIT, 1 if state else 0)
    relay_on = state

def voltage_to_o2(volts, vmin, vmax, o2min, o2max):
    return o2min + (volts - vmin) * (o2max - o2min) / (vmax - vmin)


def start_logging():
    global csv_file, csv_writer
    date_str = datetime.now().strftime("%d%m%Y")
    filename = f"DO_log_{date_str}.csv"
    csv_file = open(filename, "w", newline="")
    csv_writer = csv.writer(csv_file)
    csv_writer.writerow(["Date and Time", "DO (% air sat)", "Flush Pump"])
    print(f"Logging to {filename}")


def close_logging():
    global csv_file
    if csv_file:
        csv_file.close()
        csv_file = None
        print("Logging stopped")


def monitor_loop():
    global running, relay_on

    start_time = time.time()

    v0 = float(v0_entry.get())
    v100 = float(v100_entry.get())
    low_thr = float(low_entry.get())
    high_thr = float(high_entry.get())

    while running:
        counts = ul.a_in(BOARD_NUM, AI_CH, ULRange.BIP5VOLTS)
        volts = ul.to_eng_units(BOARD_NUM, ULRange.BIP5VOLTS, counts)
        o2 = voltage_to_o2(volts, v0, v100, 0, 100)

        o2_label.config(text=f"DO: {o2:.2f}% air sat")
        volt_label.config(text=f"Voltage: {volts:.4f} V")

        if o2 < low_thr and not relay_on:
            set_relay(True)
        elif o2 > high_thr and relay_on:
            set_relay(False)

        state_text = "Supplying aerated water" if relay_on else "Pump closed"
        countdown_label.config(text=state_text, fg="blue" if relay_on else "blue")

        if csv_writer:
            csv_writer.writerow([
                datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
                f"{o2:.3f}",
                "ON" if relay_on else "OFF"
            ])
            csv_file.flush()

        time.sleep(1)

    set_relay(False)
    close_logging()

def toggle_loop():
    global running, confirm_stop, stop_timer

    if not running:
        try:
            float(v0_entry.get()); float(v100_entry.get())
            float(0); float(100)
            float(low_entry.get()); float(high_entry.get())
        except ValueError:
            countdown_label.config(text="Enter numeric values", fg="red")
            return

        root.focus()
        running = True
        confirm_stop = False
        toggle_button.config(text="Stop", bg="red")

        start_logging()
        thread = threading.Thread(target=monitor_loop, daemon=True)
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
            countdown_label.config(text="O₂ control stopped", fg="blue")
            set_relay(False)
            close_logging()

def reset_stop_confirmation():
    global confirm_stop
    confirm_stop = False
    if running:
        toggle_button.config(text="Stop", bg="red")

root = tk.Tk()
root.title("O₂ Control")
root.geometry("300x350")

tk.Label(root, text="Analog output calibration", font=("Arial", 10, "bold")).pack(pady=(5, 0))
frame_cal = tk.Frame(root)
frame_cal.pack(pady=5)

tk.Label(frame_cal, text="").grid(row=0, column=0)
tk.Label(frame_cal, text="0% air sat", font=("Arial", 10, "bold")).grid(row=0, column=1, padx=15)
tk.Label(frame_cal, text="100% air sat", font=("Arial", 10, "bold")).grid(row=0, column=2, padx=15)

tk.Label(frame_cal, text="Voltage (V)").grid(row=1, column=0, pady=3)
v0_entry = tk.Entry(frame_cal, width=8)
v0_entry.insert(0, "0.1")
v0_entry.grid(row=1, column=1, padx=5)
v100_entry = tk.Entry(frame_cal, width=8)
v100_entry.insert(0, "2.1")
v100_entry.grid(row=1, column=2, padx=5)

tk.Label(root, text="Thresholds", font=("Arial", 10, "bold")).pack(pady=(10, 0))
frame_thr = tk.Frame(root)
frame_thr.pack(pady=2)
tk.Label(frame_thr, text="Low (% air sat)").grid(row=0, column=0, padx=5)
low_entry = tk.Entry(frame_thr, width=8)
low_entry.insert(0, "60")
low_entry.grid(row=0, column=1)
tk.Label(frame_thr, text="High (% air sat)").grid(row=1, column=0, padx=5)
high_entry = tk.Entry(frame_thr, width=8)
high_entry.insert(0, "70")
high_entry.grid(row=1, column=1)

o2_label = tk.Label(root, text="DO: -- % air sat", font=("Arial", 12))
o2_label.pack(pady=(15, 0))
volt_label = tk.Label(root, text="Voltage: -- V", font=("Arial", 10))
volt_label.pack(pady=(5, 10))

toggle_button = tk.Button(root, text="Start", width=15, bg="lightgreen", command=toggle_loop)
toggle_button.pack(pady=10)

countdown_label = tk.Label(root, text="O₂ control OFF", fg="blue")
countdown_label.pack(pady=5)

root.mainloop()

