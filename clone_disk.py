import os
import sys
import subprocess
import threading
import curses
from tqdm import tqdm

def get_usb_devices():
    devices = []
    lsblk_result = subprocess.run(['lsblk', '-o', 'NAME,TYPE,TRAN'], stdout=subprocess.PIPE, text=True)
    for line in lsblk_result.stdout.split('\n')[1:]:
        parts = line.split()
        if len(parts) >= 3:
            name, dtype, tran = parts[:3]
            if dtype == 'disk' and name.startswith('sd') and tran == 'usb':
                devices.append(f"/dev/{name}")
    return devices

def run_command(cmd, target, progress_bars, lock):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)
    with process.stdout, process.stderr:
        stdout_thread = threading.Thread(target=print_stream, args=(process.stdout, target, progress_bars, lock, True))
        stderr_thread = threading.Thread(target=print_stream, args=(process.stderr, target, progress_bars, lock, False))
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
    return process.wait()

def print_stream(stream, target, progress_bars, lock, is_stdout):
    for line in iter(stream.readline, ''):
        if is_stdout:
            tqdm.write(f"{target}: {line.strip()}", file=sys.stdout)
        else:
            with lock:
                if "bytes" in line and "copied" in line:
                    parts = line.split()
                    copied_bytes = int(parts[0])
                    progress_bars[target].update(copied_bytes - progress_bars[target].n)
                    progress_bars[target].refresh()
                elif line.strip():  # Ensure the line is not empty
                    tqdm.write(f"{target} ERROR: {line.strip()}", file=sys.stderr)

def clone_drive(image, target, progress_bars, lock):
    cmd = f"sudo partclone.dd -s {image} -o {target} -N -f 1"
    print(f"Running command: {cmd}")  # Debug output
    return run_command(cmd, target, progress_bars, lock)

def main(stdscr, image, targets):
    curses.curs_set(0)  # Hide cursor
    lock = threading.Lock()
    progress_bars = {}
    
    for idx, target in enumerate(targets):
        progress_bars[target] = tqdm(total=os.path.getsize(image), position=idx, leave=True, unit='B', unit_scale=True, desc=target)
    
    threads = []
    results = {}

    for target in targets:
        thread = threading.Thread(target=lambda: results.update({target: clone_drive(image, target, progress_bars, lock)}))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    for target, result in results.items():
        if result != 0:
            tqdm.write(f"{target} finished with errors", file=sys.stderr)
        progress_bars[target].close()

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clone_drives.py /path/to/image.img")
        sys.exit(1)

    image = sys.argv[1]

    if not os.path.isfile(image):
        print(f"Image file {image} not found")
        sys.exit(1)

    targets = get_usb_devices()
    if not targets:
        print("No USB flash drives found")
        sys.exit(1)

    print(f"Found USB devices: {targets}")
    curses.wrapper(main, image, targets)
