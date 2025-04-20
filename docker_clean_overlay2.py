import os
import subprocess
import shutil

OVERLAY2_DIR = "/mnt/docker-data/overlay2"
DELETED_LOG = "/tmp/deleted_overlay2_layers.log"

def get_used_overlay2_ids():
    """Returns a set of overlay2 layer IDs used by containers and images."""
    try:
        inspect_cmd = (
            "docker inspect $(docker ps -aq) $(docker images -q) "
            "| grep -oP '(?<=overlay2/)[^/\\\"]+'"
        )
        output = subprocess.check_output(inspect_cmd, shell=True, text=True)
        return set(output.strip().splitlines())
    except subprocess.CalledProcessError:
        print("[ERROR] Failed to collect overlay2 layer references from Docker.")
        return set()

def get_all_overlay2_dirs():
    """List all subdirectories in overlay2."""
    return [d for d in os.listdir(OVERLAY2_DIR) if os.path.isdir(os.path.join(OVERLAY2_DIR, d))]

def get_directory_size(path):
    """Get directory size safely, handle permission errors."""
    try:
        size = subprocess.check_output(["du", "-sh", path], stderr=subprocess.DEVNULL).split()[0].decode()
        return size
    except subprocess.CalledProcessError:
        return "PermissionDenied"

def delete_orphaned_dirs(used_ids):
    deleted = []

    print("[INFO] Scanning for orphaned overlay2 directories...\n")
    for folder in get_all_overlay2_dirs():
        if folder not in used_ids:
            path = os.path.join(OVERLAY2_DIR, folder)
            size = get_directory_size(path)
            if size == "PermissionDenied":
                print(f"[SKIPPED] {folder} (Permission denied)")
                continue

            print(f"[ORPHANED] {folder} ({size}) -> deleting...")
            try:
                shutil.rmtree(path)
                deleted.append(f"{folder} ({size})")
            except Exception as e:
                print(f"[ERROR] Failed to delete {folder}: {e}")

    if deleted:
        with open(DELETED_LOG, "w") as f:
            for entry in deleted:
                f.write(entry + "\n")
        print(f"\n[INFO] Deleted {len(deleted)} orphaned directories. Logged to {DELETED_LOG}")
    else:
        print("[INFO] No orphaned directories found to delete.")

if __name__ == "__main__":
    used_ids = get_used_overlay2_ids()
    delete_orphaned_dirs(used_ids)
