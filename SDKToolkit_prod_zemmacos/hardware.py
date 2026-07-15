"""Hardware fingerprinting utilities"""
import hashlib
import platform
import re
import subprocess
import uuid
from typing import Dict, Optional


class HardwareDetector:
    def __init__(self):
        self._fingerprint: Optional[str] = None
        self._identifiers: Optional[Dict[str, str]] = None

    def get_fingerprint(self) -> str:
        if self._fingerprint is None:
            identifiers = self._collect_identifiers()
            combined = self._build_combined_string(identifiers)
            self._fingerprint = self._hash_identifiers(combined)
            self._identifiers = identifiers
        return self._fingerprint

    def get_identifiers(self) -> Dict[str, str]:
        if self._identifiers is None:
            self.get_fingerprint()
        return self._identifiers or {}

    def get_device_hash(self) -> str:
        return self.get_fingerprint()

    def _collect_identifiers(self) -> Dict[str, str]:
        identifiers = {}
        cpu_id = self._get_cpu_id()
        if cpu_id:
            identifiers['cpu_id'] = cpu_id
        motherboard_id = self._get_motherboard_id()
        if motherboard_id:
            identifiers['motherboard_id'] = motherboard_id
        if not motherboard_id:
            network_id = self._get_network_id()
            if network_id:
                identifiers['network_id'] = network_id
        os_info = self._get_os_info()
        if os_info:
            identifiers['os_info'] = os_info
        return identifiers

    def _get_cpu_id(self) -> Optional[str]:
        system = platform.system()
        try:
            if system == 'Windows':
                return self._get_cpu_id_windows()
            elif system == 'Darwin':
                return self._get_cpu_id_darwin()
            elif system == 'Linux':
                return self._get_cpu_id_linux()
        except Exception:
            pass
        return platform.processor() or None

    def _get_cpu_id_windows(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['wmic', 'cpu', 'get', 'ProcessorId', '/value'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'ProcessorId=(.+)', result.stdout)
                if match:
                    cpu_id = match.group(1).strip()
                    if cpu_id:
                        return cpu_id
        except Exception:
            pass
        return platform.processor() or None

    def _get_cpu_id_darwin(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'hw.model'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                model = result.stdout.strip()
                if model:
                    return f"mac-{model}"
        except Exception:
            pass
        try:
            result = subprocess.run(
                ['sysctl', '-n', 'machdep.cpu.brand_string'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                brand = result.stdout.strip()
                if brand:
                    return hashlib.sha256(brand.encode('utf-8')).hexdigest()[:16]
        except Exception:
            pass
        return platform.processor() or None

    def _get_cpu_id_linux(self) -> Optional[str]:
        try:
            with open('/proc/cpuinfo', 'r') as f:
                content = f.read()
            serial_match = re.search(r'Serials*:s*([0-9a-f]+)', content, re.IGNORECASE)
            if serial_match:
                return f"cpu-{serial_match.group(1)}"
            vendor = ''
            family = ''
            model_name = ''
            vendor_match = re.search(r'vendor_ids*:s*(.+)', content)
            if vendor_match:
                vendor = vendor_match.group(1).strip()
            family_match = re.search(r'cpu familys*:s*(.+)', content)
            if family_match:
                family = family_match.group(1).strip()
            model_match = re.search(r'model names*:s*(.+)', content)
            if model_match:
                model_name = model_match.group(1).strip()
            if vendor or family or model_name:
                model_short = model_name[:8] if model_name else 'unknown'
                return f"cpu-{vendor}-{family}-{model_short}"
        except Exception:
            pass
        return platform.processor() or None

    def _get_os_info(self) -> str:
        return f"{platform.system()}-{platform.release()}"

    def _get_motherboard_id(self) -> Optional[str]:
        system = platform.system()
        try:
            if system == 'Windows':
                return self._get_motherboard_id_windows()
            elif system == 'Darwin':
                return self._get_motherboard_id_darwin()
            elif system == 'Linux':
                return self._get_motherboard_id_linux()
        except Exception:
            pass
        return None

    def _get_motherboard_id_windows(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['wmic', 'baseboard', 'get', 'SerialNumber', '/value'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'SerialNumber=(.+)', result.stdout)
                if match:
                    serial = match.group(1).strip()
                    if serial and serial != 'To be filled by O.E.M.':
                        return serial
        except Exception:
            pass
        return None

    def _get_motherboard_id_darwin(self) -> Optional[str]:
        try:
            result = subprocess.run(
                ['ioreg', '-l', '-w', '0'],
                capture_output=True, text=True, timeout=5
            )
            if result.returncode == 0:
                match = re.search(r'"board-id"s*=s*"([^"]+)"', result.stdout)
                if match:
                    return match.group(1)
        except Exception:
            pass
        return None

    def _get_motherboard_id_linux(self) -> Optional[str]:
        try:
            with open('/sys/class/dmi/id/board_serial', 'r') as f:
                serial = f.read().strip()
                if serial and serial != 'To be filled by O.E.M.':
                    return serial
        except Exception:
            pass
        try:
            with open('/sys/class/dmi/id/product_name', 'r') as f:
                product = f.read().strip()
                if product:
                    return f"product-{product}"
        except Exception:
            pass
        return None

    def _get_network_id(self) -> Optional[str]:
        try:
            mac = uuid.getnode()
            if mac != 0xFFFFFFFFFFFF:
                return format(mac, '012x')
        except Exception:
            pass
        return None

    def _build_combined_string(self, identifiers: Dict[str, str]) -> str:
        parts = []
        if 'cpu_id' in identifiers:
            parts.append(f"cpu:{identifiers['cpu_id']}")
        if 'motherboard_id' in identifiers:
            parts.append(f"mb:{identifiers['motherboard_id']}")
        if 'motherboard_id' not in identifiers and 'network_id' in identifiers:
            parts.append(f"net:{identifiers['network_id']}")
        if not parts:
            raise RuntimeError(
                "Cannot generate hardware fingerprint: "
                "No stable hardware identifiers available."
            )
        return ':'.join(parts)

    def _hash_identifiers(self, combined: str) -> str:
        return hashlib.sha256(combined.encode('utf-8')).hexdigest().lower()
