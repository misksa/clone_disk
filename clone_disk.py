import os
import sys
import subprocess
import threading
import shutil
from tqdm import tqdm
import curses

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

def copy_with_progress(src, dst, progress_bar):
    total_size = os.path.getsize(src)
    progress_bar.reset(total=total_size)

    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        copied = 0
        while True:
            buf = fsrc.read(1024 * 1024)
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            progress_bar.update(len(buf))
    progress_bar.n = total_size
    progress_bar.refresh()

def clone_drive(image, target, progress_bars, lock):
    try:
        copy_with_progress(image, target, progress_bars[target])
    except Exception as e:
        with lock:
            tqdm.write(f"{target} ERROR: {str(e)}", file=sys.stderr)
    return 0

def main(stdscr, image, targets):
    curses.curs_set(0)  # Hide cursor
    lock = threading.Lock()
    progress_bars = {}
    
    for idx, target in enumerate(targets):
        progress_bars[target] = tqdm(total=100, position=idx, leave=True, unit='B', unit_scale=True, desc=target)
    
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
