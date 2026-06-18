import threading
import time
import platform
import psutil
try:
    import pynvml
    NVML_AVAILABLE = True
except ImportError:
    NVML_AVAILABLE = False

# Global variables for tracking metrics across the background thread
_is_collecting = False
_peak_ram_mb = 0.0
_peak_vram_mb = 0.0
_cpu_samples = []
_collector_thread = None

def get_system_info() -> dict:
    """Return static system hardware information."""
    info = {
        "os_system": platform.system(),
        "os_release": platform.release(),
        "cpu_count_logical": psutil.cpu_count(logical=True),
        "cpu_count_physical": psutil.cpu_count(logical=False),
        "ram_total_gb": psutil.virtual_memory().total / (1024 ** 3),
        "gpu_available": False,
        "gpu_name": None,
        "vram_total_gb": 0.0
    }
    
    if NVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            info["gpu_available"] = True
            info["gpu_name"] = pynvml.nvmlDeviceGetName(handle)
            if isinstance(info["gpu_name"], bytes):
                info["gpu_name"] = info["gpu_name"].decode('utf-8')
            mem_info = pynvml.nvmlDeviceGetMemoryInfo(handle)
            info["vram_total_gb"] = mem_info.total / (1024 ** 3)
            pynvml.nvmlShutdown()
        except Exception:
            pass
            
    return info

def _poll_metrics(interval_sec: float = 0.5):
    """Background loop polling CPU, RAM, and VRAM."""
    global _is_collecting, _peak_ram_mb, _peak_vram_mb, _cpu_samples
    
    if NVML_AVAILABLE:
        try:
            pynvml.nvmlInit()
        except Exception:
            pass

    # Baseline memory before generation starts
    process = psutil.Process()
    baseline_ram = process.memory_info().rss / (1024 * 1024)
    baseline_vram = 0.0
    if NVML_AVAILABLE:
        try:
            handle = pynvml.nvmlDeviceGetHandleByIndex(0)
            baseline_vram = pynvml.nvmlDeviceGetMemoryInfo(handle).used / (1024 * 1024)
        except Exception:
            pass

    while _is_collecting:
        # Current Process RAM (MB) overhead
        current_ram = process.memory_info().rss / (1024 * 1024)
        overhead_ram = max(0.0, current_ram - baseline_ram)
        if overhead_ram > _peak_ram_mb:
            _peak_ram_mb = overhead_ram
            
        # GPU VRAM (MB) overhead
        if NVML_AVAILABLE:
            try:
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                current_vram = pynvml.nvmlDeviceGetMemoryInfo(handle).used / (1024 * 1024)
                overhead_vram = max(0.0, current_vram - baseline_vram)
                if overhead_vram > _peak_vram_mb:
                    _peak_vram_mb = overhead_vram
            except Exception:
                pass

        # CPU percent (non-blocking after first call)
        cpu_pct = psutil.cpu_percent(interval=None)
        _cpu_samples.append(cpu_pct)
        
        time.sleep(interval_sec)
        
    if NVML_AVAILABLE:
        try:
            pynvml.nvmlShutdown()
        except Exception:
            pass

def start_collection():
    """Start background metrics polling."""
    global _is_collecting, _peak_ram_mb, _peak_vram_mb, _cpu_samples, _collector_thread
    _is_collecting = True
    _peak_ram_mb = 0.0
    _peak_vram_mb = 0.0
    _cpu_samples = []
    
    _collector_thread = threading.Thread(target=_poll_metrics, args=(0.5,), daemon=True)
    _collector_thread.start()

def stop_collection() -> dict:
    """Stop polling and return peak RAM/VRAM and average CPU."""
    global _is_collecting, _collector_thread
    _is_collecting = False
    
    if _collector_thread is not None:
        _collector_thread.join(timeout=2.0)
        
    avg_cpu = sum(_cpu_samples) / len(_cpu_samples) if _cpu_samples else 0.0
    
    return {
        "peak_ram_mb": round(_peak_ram_mb, 2),
        "peak_vram_mb": round(_peak_vram_mb, 2),
        "avg_cpu_percent": round(avg_cpu, 2)
    }
