import os
import sys
import subprocess
import threading
import curses
from tqdm import tqdm

def run_command(cmd, target, progress_bars, screen, lock):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)
    with process.stdout, process.stderr:
        stdout_thread = threading.Thread(target=print_stream, args=(process.stdout, target, progress_bars, screen, lock, True))
        stderr_thread = threading.Thread(target=print_stream, args=(process.stderr, target, progress_bars, screen, lock, False))
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
    process.wait()

def print_stream(stream, target, progress_bars, screen, lock, is_stdout):
    for line in iter(stream.readline, ''):
        if is_stdout and "s" in line:
            progress = line.split("s")[1].strip()
            with lock:
                progress_bars[target].n = int(progress.split()[0])
                progress_bars[target].refresh()
        else:
            with lock:
                screen.addstr(f"{target} ERROR: {line.strip()}\n")
                screen.refresh()

def clone_drive(image, target, progress_bars, screen, lock):
    cmd = f"pv {image} | sudo dd of={target} bs=16M iflag=fullblock oflag=direct status=progress"
    run_command(cmd, target, progress_bars, screen, lock)

def main(screen, image, targets):
    progress_bars = {}
    lock = threading.Lock()
    max_len = max(len(t) for t in targets)
    
    for idx, target in enumerate(targets):
        screen.addstr(idx, 0, f"Cloning {target}:")
        progress_bars[target] = tqdm(total=100, position=idx + 1, bar_format='{l_bar}{bar}| {n_fmt}/{total_fmt} [{elapsed}<{remaining}, {rate_fmt}{postfix}]')
    
    threads = []
    for target in targets:
        thread = threading.Thread(target=clone_drive, args=(image, target, progress_bars, screen, lock))
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
