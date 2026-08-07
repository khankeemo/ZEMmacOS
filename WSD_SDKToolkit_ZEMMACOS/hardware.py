"""Hardware fingerprint generation"""
import hashlib
import platform
import re
import subprocess
import uuid
from typing import Dict, Optional


class HardwareDetector:
    # Fingerprint algorithm version (SECTION 0D §12). Bump when the identifier
    # set or hash changes so stored bindings re-verify against the backend.
    FINGERPRINT_VERSION = "v1"

    def __init__(self):
        self._fingerprint: Optional[str] = None
        self._identifiers: Optional[Dict[str, str]] = None

    def get_fingerprint(self) -> str:
        if self._fingerprint is None:
            identifiers = self._collect_identifiers()
            combined = self._build_combined_string(identifiers)
            digest = self._hash_identifiers(combined)
            self._fingerprint = f"{self.FINGERPRINT_VERSION}:{digest}"
            self._identifiers = identifiers
        return self._fingerprint

    def fingerprint_version(self) -> str:
        """Return the current algorithm version (e.g. 'v1')."""
        return self.FINGERPRINT_VERSION

    @staticmethod
    def parse_fingerprint(fingerprint: str) -> Dict[str, str]:
        """Split a stored fingerprint into {version, hash}. Returns
        {'version': '', 'hash': raw} for legacy un-versioned fingerprints."""
        if not fingerprint:
            return {'version': '', 'hash': ''}
        if ':' in fingerprint:
            version, _, digest = fingerprint.partition(':')
            return {'version': version, 'hash': digest}
        return {'version': '', 'hash': fingerprint}

    def fingerprint_changed(self, stored_fingerprint: Optional[str]) -> bool:
        """A version mismatch means the algorithm changed — re-verify against the
        backend (SECTION 0B Rule 2), never re-bind locally."""
        if not stored_fingerprint:
            return False
        parsed = self.parse_fingerprint(stored_fingerprint)
        if parsed['version'] and parsed['version'] != self.FINGERPRINT_VERSION:
            return True
        return stored_fingerprint != self.get_fingerprint()

    def get_identifiers(self) -> Dict[str, str]:
        if self._identifiers is None:
            self.get_fingerprint()
        return self._identifiers or {}

    def _collect_identifiers(self) -> Dict[str, str]:
        identifiers: Dict[str, str] = {}
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
            serial_match = re.search(r'Serial\s*:\s*([0-9a-f]+)', content, re.IGNORECASE)
            if serial_match:
                return f"cpu-{serial_match.group(1)}"
            vendor = ''
            family = ''
            for line in content.splitlines():
                if line.startswith('vendor_id'):
                    vendor = line.split(':')[1].strip()
                elif line.startswith('cpu family'):
                    family = line.split(':')[1].strip()
            if vendor and family:
                return f"{vendor}-{family}"
        except Exception:
            pass
        return platform.processor() or None

    def _get_motherboard_id(self) -> Optional[str]:
        system = platform.system()
        try:
            if system == 'Windows':
                result = subprocess.run(
                    ['wmic', 'baseboard', 'get', 'SerialNumber', '/value'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    match = re.search(r'SerialNumber=(.+)', result.stdout)
                    if match:
                        serial = match.group(1).strip()
                        if serial and serial not in ('To be filled by O.E.M.', 'Default string'):
                            return f"mb-{serial}"
            elif system == 'Linux':
                result = subprocess.run(
                    ['dmidecode', '-s', 'baseboard-serial-number'],
                    capture_output=True, text=True, timeout=5
                )
                if result.returncode == 0:
                    serial = result.stdout.strip()
                    if serial and serial not in ('To be filled by O.E.M.', 'Default string'):
                        return f"mb-{serial}"
        except Exception:
            pass
        return None

    def _get_network_id(self) -> Optional[str]:
        try:
            mac = uuid.getnode()
            if mac and (mac >> 40) % 2 == 0:
                return hashlib.sha256(f"net-{mac:x}".encode('utf-8')).hexdigest()[:16]
        except Exception:
            pass
        return None

    def _get_os_info(self) -> Optional[str]:
        return f"{platform.system()}-{platform.release()}"

    def _build_combined_string(self, identifiers: Dict[str, str]) -> str:
        parts = []
        for key in ('cpu_id', 'motherboard_id', 'network_id'):
            if key in identifiers:
                parts.append(identifiers[key])
        return '|'.join(parts)

    def _hash_identifiers(self, data: str) -> str:
        return hashlib.sha256(data.encode('utf-8')).hexdigest()
