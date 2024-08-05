import os
import sys
import asyncio
import subprocess

async def read_stream(stream, target, is_stdout=True):
    while True:
        line = await stream.readline()
        if not line:
            break
        if is_stdout:
            print(f"{target}: {line.decode().strip()}")
        else:
            print(f"{target} ERROR: {line.decode().strip()}", file=sys.stderr)

async def run_command(cmd, target):
    process = await asyncio.create_subprocess_exec(
        *cmd,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE
    )

    await asyncio.gather(
        read_stream(process.stdout, target),
        read_stream(process.stderr, target, is_stdout=False)
    )

    await process.wait()

async def clone_drive(image, target):
    cmd = ["sh", "-c", f"pv {image} | sudo dd of={target} bs=128M iflag=fullblock oflag=direct status=progress"]
    await run_command(cmd, target)

async def main(image, targets):
    tasks = [clone_drive(image, target) for target in targets]
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python clone_drives.py /path/to/image.img /dev/sdY /dev/sdZ /dev/sdA")
        sys.exit(1)

    image = sys.argv[1]
    targets = sys.argv[2:]

    if not os.path.isfile(image):
        print(f"Image file {image} not found")
        sys.exit(1)

    asyncio.run(main(image, targets))
