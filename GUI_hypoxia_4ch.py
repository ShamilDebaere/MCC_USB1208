import tkinter as tk
from mcculw import ul
from mcculw.enums import ULRange, DigitalIODirection, DigitalPortType
from mcculw.device_info import DaqDeviceInfo
import threading
import time
import csv
from datetime import datetime

BOARD_NUM = 0
PORT = DigitalPortType.FIRSTPORTA

AI_CHANNELS = [0, 1, 2, 3]

RELAY_BITS = [0, 1, 2, 3]

ul.d_config_port(BOARD_NUM, PORT, DigitalIODirection.OUT)
daq_info = DaqDeviceInfo(BOARD_NUM)

running = False
confirm_stop = False
stop_timer = None

relay_states = [False, False, False, False]

csv_file = None
csv_writer = None


def set_relay(index, state: bool):
    relay_states[index] = state
    ul.d_bit_out(BOARD_NUM, PORT, RELAY_BITS[index], 1 if state else 0)


def voltage_to_o2(volts, vmin, vmax):
    return 0 + (volts - vmin) * (100 - 0) / (vmax - vmin)


def start_logging():
    global csv_file, csv_writer
    date_str = datetime.now().strftime("%d%m%Y")
    filename = f"DO_log_{date_str}.csv"
    csv_file = open(filename, "w", newline="")
    csv_writer = csv.writer(csv_file)

    header = ["Date and Time"]
    for i in range(4):
        header += [f"DO{i+1} (% air sat)", f"Flush Pump Ch{i+1}"]
    csv_writer.writerow(header)

    print(f"Logging to {filename}")


def close_logging():
    global csv_file
    if csv_file:
        csv_file.close()
        csv_file = None
        print("Logging stopped")


def monitor_loop():
    global running

    v0 = [float(v0_entries[i].get()) for i in range(4)]
    v100 = [float(v100_entries[i].get()) for i in range(4)]
    low_thr = [float(low_entries[i].get()) for i in range(4)]
    high_thr = [float(high_entries[i].get()) for i in range(4)]

    while running:
        row = [datetime.now().strftime("%d/%m/%Y %H:%M:%S")]

        for i, ch in enumerate(AI_CHANNELS):
            counts = ul.a_in(BOARD_NUM, ch, ULRange.BIP5VOLTS)
            volts = ul.to_eng_units(BOARD_NUM, ULRange.BIP5VOLTS, counts)
            o2 = voltage_to_o2(volts, v0[i], v100[i])

            o2_labels[i].config(text=f"DO: {o2:.2f}% air sat")
            volt_labels[i].config(text=f"Voltage: {volts:.4f} V")

            if o2 < low_thr[i] and not relay_states[i]:
                set_relay(i, True)
            elif o2 > high_thr[i] and relay_states[i]:
                set_relay(i, False)

            relay_texts[i].config(
                text="Supplying aerated water" if relay_states[i] else "Pump closed",
                fg="blue" if relay_states[i] else "blue",
            )

            row += [f"{o2:.3f}", "ON" if relay_states[i] else "OFF"]

        if csv_writer:
            csv_writer.writerow(row)
            csv_file.flush()

        time.sleep(1)

    for i in range(4):
        set_relay(i, False)
    close_logging()


def toggle_loop():
    global running, confirm_stop, stop_timer

    if not running:
        try:
            for i in range(4):
                float(v0_entries[i].get())
                float(v100_entries[i].get())
                float(low_entries[i].get())
                float(high_entries[i].get())
        except ValueError:
            status_label.config(text="Enter numeric values", fg="red")
            return

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
            status_label.config(text="Control stopped", fg="blue")
            for i in range(4):
                set_relay(i, False)
            close_logging()


def reset_stop_confirmation():
    global confirm_stop
    confirm_stop = False
    if running:
        toggle_button.config(text="Stop", bg="red")

root = tk.Tk()
root.title("4-channel O₂ Control")
root.geometry("500x550")

tk.Label(root, text="Calibration & Thresholds",
         font=("Arial", 12, "bold")).pack(pady=10)

frame = tk.Frame(root)
frame.pack()

v0_entries = []
v100_entries = []
low_entries = []
high_entries = []

o2_labels = []
volt_labels = []
relay_texts = []

for i in range(4):
    block = tk.LabelFrame(frame, text=f"Channel {i+1}", padx=10, pady=10)
    block.grid(row=i//2, column=i % 2, padx=10, pady=10)

    tk.Label(block, text="Voltage 0% air sat").grid(row=0, column=0)
    e0 = tk.Entry(block, width=8)
    e0.insert(0, "0")
    e0.grid(row=0, column=1)
    v0_entries.append(e0)

    tk.Label(block, text="Voltage 100% air sat").grid(row=1, column=0)
    e1 = tk.Entry(block, width=8)
    e1.insert(0, "2")
    e1.grid(row=1, column=1)
    v100_entries.append(e1)

    tk.Label(block, text="Low (% air sat)").grid(row=2, column=0)
    e2 = tk.Entry(block, width=8)
    e2.insert(0, "60")
    e2.grid(row=2, column=1)
    low_entries.append(e2)

    tk.Label(block, text="High (% air sat)").grid(row=3, column=0)
    e3 = tk.Entry(block, width=8)
    e3.insert(0, "70")
    e3.grid(row=3, column=1)
    high_entries.append(e3)

    o2lbl = tk.Label(block, text="DO: -- % air sat")
    o2lbl.grid(row=4, column=0, columnspan=2)
    o2_labels.append(o2lbl)

    voltlbl = tk.Label(block, text="Voltage: -- V")
    voltlbl.grid(row=5, column=0, columnspan=2)
    volt_labels.append(voltlbl)

    relaylbl = tk.Label(block, text="O₂ control OFF", fg="blue")
    relaylbl.grid(row=6, column=0, columnspan=2)
    relay_texts.append(relaylbl)

toggle_button = tk.Button(root, text="Start", width=20, bg="lightgreen",
                          command=toggle_loop)
toggle_button.pack(pady=15)

status_label = tk.Label(root, text="O₂ control OFF", fg="blue")
status_label.pack(pady=5)

root.mainloop()
