import json
import os
import platform
import subprocess

import matplotlib
import numpy
import pandas


def run_cmd(cmd):
    try:
        res = subprocess.run(
            cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, shell=True
        )
        return res.stdout.strip()
    except Exception:
        return ""


def get_windows_specs():
    os_str = run_cmd(
        'powershell -NoProfile -Command "$o = Get-CimInstance Win32_OperatingSystem; '
        'Write-Output ($o.Caption + \' \' + $o.Version + \' (\' + $o.OSArchitecture + \')\')"'
    ) or f"{platform.system()} {platform.release()} ({platform.machine()})"

    cpu_raw = run_cmd(
        'powershell -NoProfile -Command "Get-CimInstance Win32_Processor | '
        'Select-Object Name, NumberOfCores, NumberOfLogicalProcessors, MaxClockSpeed | ConvertTo-Json"'
    )
    cpu_str = platform.processor() or "Unknown CPU"
    if cpu_raw:
        try:
            data = json.loads(cpu_raw)
            if isinstance(data, list):
                data = data[0]
            name = str(data.get("Name", "")).strip()
            cores = data.get("NumberOfCores", "?")
            logical = data.get("NumberOfLogicalProcessors", "?")
            clock = data.get("MaxClockSpeed", "?")
            cpu_str = f"{name} ({cores} cores, {logical} logical processors, {clock} MHz)"
        except Exception:
            pass

    ram_raw = run_cmd(
        'powershell -NoProfile -Command "(Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory"'
    )
    try:
        ram_gb = f"{int(ram_raw) / (1024 ** 3):.2f} GB"
    except Exception:
        ram_gb = "Unknown"

    return os_str, cpu_str, ram_gb


def main():
    os.makedirs("results", exist_ok=True)
    os_str, cpu_str, ram_gb = get_windows_specs()

    java_lines = [ln.strip() for ln in run_cmd("java -version").splitlines() if ln.strip()]
    java_str = " | ".join(java_lines[:2]) if java_lines else "java (not found)"
    javac_str = run_cmd("javac -version") or "javac (not found)"

    info = {
        "os": os_str,
        "cpu": cpu_str,
        "ram": ram_gb,
        "java": java_str,
        "javac": javac_str,
        "jvm_flags": "-Xms2g -Xmx4g",
        "python": platform.python_version(),
        "pandas": pandas.__version__,
        "numpy": numpy.__version__,
        "matplotlib": matplotlib.__version__,
    }

    with open("results/machine.json", "w", encoding="utf-8") as f:
        json.dump(info, f, ensure_ascii=False, indent=2)

    lines = [
        f"OS: {info['os']}",
        f"CPU: {info['cpu']}",
        f"RAM: {info['ram']}",
        f"Java Runtime: {info['java']}",
        f"Java Compiler: {info['javac']}",
        f"JVM Flags: {info['jvm_flags']}",
        f"Python: {info['python']} (pandas {info['pandas']}, numpy {info['numpy']}, matplotlib {info['matplotlib']})",
    ]
    with open("results/machine.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")

    print("Da luu thong tin cau hinh may vao results/machine.txt")


if __name__ == "__main__":
    main()
