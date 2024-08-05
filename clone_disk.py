import os
import sys
import subprocess
import threading
import curses
from tqdm import tqdm

def run_command(cmd, target, progress_bars, lock):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)
    with process.stdout, process.stderr:
        stdout_thread = threading.Thread(target=print_stream, args=(process.stdout, target, progress_bars, lock, True))
        stderr_thread = threading.Thread(target=print_stream, args=(process.stderr, target, progress_bars, lock, False))
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
    process.wait()

def print_stream(stream, target, progress_bars, lock, is_stdout):
    for line in iter(stream.readline, ''):
        if is_stdout:
            if "bytes" in line:
                parts = line.split()
                copied_bytes = int(parts[0])
                with lock:
                    progress_bars[target].update(copied_bytes - progress_bars[target].n)
        else:
            with lock:
                tqdm.write(f"{target} ERROR: {line.strip()}", file=sys.stderr)

def clone_drive(image, target, progress_bars, lock):
    cmd = f"pv {image} | sudo dd of={target} bs=128M iflag=fullblock oflag=direct status=none"
    run_command(cmd, target, progress_bars, lock)

def main(stdscr, image, targets):
    curses.curs_set(0)  # Hide cursor
    lock = threading.Lock()
    progress_bars = {}
    max_len = max(len(t) for t in targets)
    
    for idx, target in enumerate(targets):
        progress_bars[target] = tqdm(total=os.path.getsize(image), position=idx, leave=True, unit='B', unit_scale=True, desc=target)
    
    threads = []
    for target in targets:
        thread = threading.Thread(target=clone_drive, args=(image, target, progress_bars, lock))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()
    
    for bar in progress_bars.values():
        bar.close()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python clone_drives.py /path/to/image.img /dev/sdY /dev/sdZ /dev/sdA")
        sys.exit(1)

    image = sys.argv[1]
    targets = sys.argv[2:]

    if not os.path.isfile(image):
        print(f"Image file {image} not found")
        sys.exit(1)

    curses.wrapper(main, image, targets)
