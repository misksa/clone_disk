import os
import sys
import subprocess
import threading
import shutil
from tqdm import tqdm
import curses
from multiprocessing import Pool, Manager

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

def copy_with_progress(src, dst, total_size, queue):
    copied = 0
    with open(src, 'rb') as fsrc, open(dst, 'wb') as fdst:
        while True:
            buf = fsrc.read(1024 * 1024 * 16)  # 16MB buffer size
            if not buf:
                break
            fdst.write(buf)
            copied += len(buf)
            queue.put(len(buf))  # Send the amount of data copied to the queue
    queue.put(total_size - copied)  # Ensure progress bar completes

def clone_drive(image, target, total_size):
    try:
        queue = Manager().Queue()
        pbar = tqdm(total=total_size, unit='B', unit_scale=True, desc=target)

        def update_progress_bar(q, pbar):
            while True:
                chunk = q.get()
                if chunk is None:
                    break
                pbar.update(chunk)

        thread = threading.Thread(target=update_progress_bar, args=(queue, pbar))
        thread.start()

        copy_with_progress(image, target, total_size, queue)
        queue.put(None)  # Signal the progress bar to finish
        thread.join()
        pbar.close()
    except Exception as e:
        print(f"{target} ERROR: {str(e)}", file=sys.stderr)

def main(stdscr, image, targets):
    curses.curs_set(0)  # Hide cursor
    total_size = os.path.getsize(image)
    
    args = [(image, target, total_size) for target in targets]

    with Pool(processes=min(len(targets), os.cpu_count())) as pool:
        pool.starmap(clone_drive, args)

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
