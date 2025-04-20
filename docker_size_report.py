import docker  # type: ignore
import subprocess
import re
import os

client = docker.from_env()

def to_mb(size_bytes):
    return size_bytes / (1024 ** 2)

def to_gb(size_bytes):
    return size_bytes / (1024 ** 3)

def get_container_sizes():
    try:
        output = subprocess.check_output(
            ["docker", "ps", "-a", "--size", "--format", "{{.Names}} {{.Size}}"],
            text=True
        )
        total = 0
        rows = []

        for line in output.strip().split("\n"):
            parts = line.strip().split(" ", 1)
            if len(parts) < 2:
                continue
            name, size_str = parts

            # Match virtual size inside parentheses
            match = re.search(r'\(virtual\s+([\d\.]+)([kMG]?)B\)', size_str)
            if not match:
                continue

            size_val, unit = match.groups()
            size_val = float(size_val)
            if size_val == 0:
                continue

            multiplier = {'': 1, 'k': 1024, 'M': 1024 ** 2, 'G': 1024 ** 3}
            bytes_size = size_val * multiplier.get(unit, 1)
            rows.append((name, f"{to_mb(bytes_size):.2f} MB"))
            total += bytes_size

        print("\n🧱 Container Sizes:")
        if not rows:
            print(" - No containers with measurable virtual size.")
        else:
            print(f"{'CONTAINER NAME':<40} {'SIZE':>12}")
            for name, size in rows:
                print(f"{name:<40} {size:>12}")
            print(f"{'Total container size:':<40} {to_gb(total):>9.2f} GB")

        return total
    except Exception as e:
        print("Error checking container sizes:", e)
        return 0


def get_image_sizes():
    images = client.images.list()
    used_ids = {c.image.id for c in client.containers.list(all=True)}
    used = []
    unused = []
    for img in images:
        size = img.attrs['Size']
        if img.id in used_ids:
            used.append(size)
        else:
            unused.append(size)
    print("\n🖼️ Docker Images:")
    print(f"{'IMAGE TYPE':<20} {'SIZE':>12}")
    print(f"{'Used images':<20} {to_gb(sum(used)):>9.2f} GB")
    print(f"{'Unused images':<20} {to_gb(sum(unused)):>9.2f} GB")
    return sum(used), sum(unused)

def get_build_cache_size():
    try:
        result = subprocess.check_output(['docker', 'system', 'df', '-v'], text=True)
        match = re.search(r'Build cache\s+\d+\s+\d+\s+([\d\.]+)\s*(kB|MB|GB)', result)
        if match:
            size, unit = match.groups()
            size = float(size)
            multiplier = {'kB': 1024, 'MB': 1024**2, 'GB': 1024**3}
            total = size * multiplier.get(unit, 1)
        else:
            total = 0
        print("\n🛠️ Build Cache:")
        print(f"{'Build cache size:':<30} {to_gb(total):>9.2f} GB")
        return total
    except Exception as e:
        print("Error checking build cache:", e)
        return 0

def get_volume_sizes():
    try:
        volumes = client.volumes.list()
        valid_volumes = []
        total = 0

        for vol in volumes:
            mountpoint = vol.attrs['Mountpoint']
            if os.path.exists(mountpoint):
                valid_volumes.append(vol)

        print("\n📦 Docker Volumes:")
        if not valid_volumes:
            print(" - No Docker volumes with valid paths found.")
            return 0

        print(f"{'VOLUME NAME':<55} {'SIZE':>12}")
        for vol in valid_volumes:
            try:
                mountpoint = vol.attrs['Mountpoint']
                size_bytes = int(subprocess.check_output(["du", "-sb", mountpoint]).split()[0])
                print(f"{vol.name:<55} {to_mb(size_bytes):>9.2f} MB")
                total += size_bytes
            except PermissionError:
                print(f"{vol.name:<55} {'Permission Denied':>12}")
            except Exception as e:
                print(f"{vol.name:<55} Error: {str(e)}")
        print(f"\n{'Total volume size:':<55} {to_gb(total):>9.2f} GB")
        return total
    except Exception as e:
        print("Error checking volume sizes:", e)
        return 0

if __name__ == "__main__":
    total_containers = get_container_sizes()
    used_images, unused_images = get_image_sizes()
    build_cache = get_build_cache_size()
    volume_size = get_volume_sizes()

    total = total_containers + used_images + unused_images + build_cache + volume_size

    print("\n🧮 TOTAL Docker Disk Usage")
    print(f"{'-'*45}")
    print(f"{'TOTAL SPACE USED':<30} {to_gb(total):>9.2f} GB")
