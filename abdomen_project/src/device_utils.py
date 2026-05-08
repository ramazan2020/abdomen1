"""
Apple Silicon (M1/M2/M3/M4/M5) MPS Hızlandırma Yardımcısı
============================================================
Metal Performance Shaders (MPS) backend için device yönetimi,
bellek optimizasyonu ve M5 özelinde ayarlar.

Kullanım:
    from device_utils import get_device, log_device_info, MPSMemoryManager
    device = get_device()
"""

import os
import platform
import sys
from typing import Optional
import torch


# ─────────────────────────────────────────────────────────────
# Device seçimi: MPS > CPU  (CUDA yoksa)
# ─────────────────────────────────────────────────────────────

def get_device(verbose: bool = True) -> torch.device:
    """
    En iyi kullanılabilir device'ı döner.
    Öncelik sırası: CUDA → MPS → CPU

    Apple M5 için MPS kullanılır.
    """
    if torch.cuda.is_available():
        device = torch.device("cuda")
        name = torch.cuda.get_device_name(0)
        if verbose:
            print(f"✅ CUDA GPU bulundu: {name}")

    elif torch.backends.mps.is_available():
        device = torch.device("mps")
        if verbose:
            print("✅ Apple Silicon MPS (Metal) aktif")
            print(f"   Chip   : {_get_chip_info()}")
            print(f"   PyTorch: {torch.__version__}")
            print(f"   Python : {sys.version.split()[0]}")
            _print_mps_tips()

    else:
        device = torch.device("cpu")
        if verbose:
            print("⚠️  GPU bulunamadı – CPU kullanılıyor (yavaş olacak)")
            import multiprocessing
            print(f"   CPU çekirdek: {multiprocessing.cpu_count()}")

    return device


def _get_chip_info() -> str:
    """macOS sistem bilgisinden çip adını döner."""
    try:
        import subprocess
        result = subprocess.run(
            ["sysctl", "-n", "machdep.cpu.brand_string"],
            capture_output=True, text=True
        )
        chip = result.stdout.strip()
        if not chip:
            result = subprocess.run(
                ["system_profiler", "SPHardwareDataType"],
                capture_output=True, text=True
            )
            for line in result.stdout.split("\n"):
                if "Chip" in line or "Processor" in line:
                    return line.strip()
        return chip or "Apple Silicon"
    except Exception:
        return "Apple Silicon"

def _print_mps_tips() -> None:
    print("\n   📌 MPS Optimizasyon İpuçları (M5):")
    print("   • AMP: bfloat16 kullanın (float16 desteklenmiyor)")
    print("   • DataLoader: spawn context + 4-6 worker (fork sorunu önlenir)")
    print("   • Batch size: 48+ (unified memory büyükse artırın)")
    print("   • PYTORCH_MPS_HIGH_WATERMARK_RATIO=0.0 → OOM önleme")
    print("   • torch.mps.empty_cache() her epoch sonrası")
    print()
