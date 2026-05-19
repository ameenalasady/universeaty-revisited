# dashboard/backend/app/utils/metrics.py
import os
import subprocess

def run_command(cmd_list):
    try:
        result = subprocess.run(cmd_list, capture_output=True, text=True, timeout=3)
        if result.returncode == 0:
            return result.stdout.strip()
        return f"Error: {result.stderr.strip()}"
    except Exception as e:
        return str(e)

def get_cpu_temp():
    try:
        if os.path.exists("/sys/class/thermal/thermal_zone0/temp"):
            with open("/sys/class/thermal/thermal_zone0/temp", "r") as f:
                return round(int(f.read().strip()) / 1000.0, 1)
    except Exception:
        pass
    return 0.0

def get_cpu_load():
    try:
        if os.path.exists("/proc/loadavg"):
            with open("/proc/loadavg", "r") as f:
                return " ".join(f.read().strip().split()[:3])
    except Exception:
        pass
    return "N/A"

def get_pi_uptime():
    try:
        if os.path.exists("/proc/uptime"):
            with open("/proc/uptime", "r") as f:
                uptime_seconds = float(f.read().strip().split()[0])
                days = int(uptime_seconds // 86400)
                hours = int((uptime_seconds % 86400) // 3600)
                minutes = int((uptime_seconds % 3600) // 60)
                return f"{days}d {hours}h {minutes}m" if days > 0 else f"{hours}h {minutes}m"
    except Exception:
        pass
    return "N/A"

def get_ram_usage():
    ram = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0.0}
    try:
        meminfo = run_command(["free", "-m"])
        lines = meminfo.split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            total = int(parts[1])
            free = int(parts[6])  # available memory is much more accurate
            used = total - free
            ram = {
                "total_mb": total,
                "used_mb": used,
                "free_mb": free,
                "percent": round((used / total) * 100, 1) if total > 0 else 0.0
            }
    except Exception:
        pass
    return ram

def get_disk_usage():
    disk = {"total_mb": 0, "used_mb": 0, "free_mb": 0, "percent": 0.0}
    try:
        dfinfo = run_command(["df", "-m", "/"])
        lines = dfinfo.split("\n")
        if len(lines) > 1:
            parts = lines[1].split()
            total = int(parts[1])
            used = int(parts[2])
            free = int(parts[3])
            disk = {
                "total_mb": total,
                "used_mb": used,
                "free_mb": free,
                "percent": round((used / total) * 100, 1) if total > 0 else 0.0
            }
    except Exception:
        pass
    return disk

def get_service_status(service_name="universeaty.service"):
    service = {"active_state": "inactive", "sub_state": "unknown", "pid": 0, "memory_mb": 0.0, "uptime": "N/A"}
    try:
        status_info = run_command(["systemctl", "show", service_name, "--property=ActiveState,SubState,MainPID,ActiveEnterTimestamp"])
        props = {}
        for line in status_info.split("\n"):
            if "=" in line:
                k, v = line.split("=", 1)
                props[k.strip()] = v.strip()
        
        service["active_state"] = props.get("ActiveState", "inactive")
        service["sub_state"] = props.get("SubState", "unknown")
        
        pid = int(props.get("MainPID", "0"))
        service["pid"] = pid
        
        raw_timestamp = props.get("ActiveEnterTimestamp", "")
        if raw_timestamp and raw_timestamp != "N/A":
            parts = raw_timestamp.split()
            if len(parts) >= 3:
                service["uptime"] = f"{parts[1]} {parts[2]}"

        # Calculate exact memory usage natively from /proc/{pid}/status (Resident Set Size)
        if pid > 0:
            status_path = f"/proc/{pid}/status"
            if os.path.exists(status_path):
                with open(status_path, "r") as f:
                    for line in f:
                        if line.startswith("VmRSS:"):
                            rss_kb = int(line.split()[1])
                            service["memory_mb"] = round(rss_kb / 1024.0, 1)
                            break
    except Exception as e:
        service["uptime"] = str(e)
    return service
