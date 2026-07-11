"""Hardware fingerprinting utilities"""
import platform
import uuid
import hashlib
import subprocess
import re
from typing import Dict

class HardwareFingerprint:
    @staticmethod
    def get_mac_addresses() -> list:
        try:
            result = subprocess.run(
                ['ip', 'link', 'show'],
                capture_output=True,
                text=True
            )
            matches = re.findall(r'link/ether ([0-9a-f:]{17})', result.stdout)
            return matches
        except:
            return [':'.join(['{:02x}'.format((uuid.getnode() >> i) & 0xff) for i in range(0, 8*6, 8)])]

    @staticmethod
    def get_cpu_info() -> str:
        try:
            if platform.system() == 'Windows':
                return platform.processor()
            else:
                with open('/proc/cpuinfo', 'r') as f:
                    for line in f:
                        if 'model name' in line:
                            return line.split(':')[1].strip()
        except:
            return platform.processor()

    @staticmethod
    def get_os_info() -> str:
        return f"{platform.system()}-{platform.release()}"

    @staticmethod
    def generate_fingerprint() -> Dict:
        macs = HardwareFingerprint.get_mac_addresses()
        combined = ':'.join(macs[:3]) if macs else ''
        combined += HardwareFingerprint.get_cpu_info()
        combined += HardwareFingerprint.get_os_info()
        fingerprint = hashlib.sha256(combined.encode('utf-8')).hexdigest()

        return {
            'fingerprint': fingerprint,
            'mac_addresses': macs[:3] if macs else [],
            'cpu': HardwareFingerprint.get_cpu_info(),
            'os': HardwareFingerprint.get_os_info(),
            'platform': platform.system()
        }
