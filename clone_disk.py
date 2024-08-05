import os
import sys
import subprocess
import threading

def run_command(cmd, target):
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=1, universal_newlines=True)
    with process.stdout, process.stderr:
        threading.Thread(target=print_stream, args=(process.stdout, target, True)).start()
        threading.Thread(target=print_stream, args=(process.stderr, target, False)).start()
    process.wait()

def print_stream(stream, target, is_stdout):
    for line in iter(stream.readline, ''):
        if is_stdout:
            print(f"{target}: {line.strip()}")
        else:
            print(f"{target} ERROR: {line.strip()}", file=sys.stderr)

def clone_drive(image, target):
    cmd = f"pv {image} | sudo dd of={target} bs=128M iflag=fullblock oflag=direct status=progress"
    run_command(cmd, target)

def main(image, targets):
    threads = []
    for target in targets:
        thread = threading.Thread(target=clone_drive, args=(image, target))
        threads.append(thread)
        thread.start()
    
    for thread in threads:
        thread.join()

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python clone_drives.py /path/to/image.img /dev/sdY /dev/sdZ /dev/sdA")
        sys.exit(1)

    image = sys.argv[1]
    targets = sys.argv[2:]

    if not os.path.isfile(image):
        print(f"Image file {image} not found")
        sys.exit(1)

    main(image, targets)
