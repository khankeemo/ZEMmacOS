# hardware_id.py - Professional Hardware ID Generator
# Generates stable, unique hardware fingerprint for license locking
# Works across Windows reinstalls, blocks different PCs

import os
import sys
import hashlib
import subprocess
import platform
import re
import uuid
from typing import Optional, List

class HardwareID:
    """Generate stable hardware fingerprint for license validation"""
    
    @staticmethod
    def get_mac_addresses() -> List[str]:
        """Get all MAC addresses (excluding virtual/loopback)"""
        macs = []
        try:
            if sys.platform == "win32":
                # Windows: use getmac with verbose output
                result = subprocess.run(
                    ['getmac', '/v', '/fo', 'csv', '/nh'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split('\n'):
                    parts = [p.strip().strip('"') for p in line.split(',')]
                    if len(parts) >= 2:
                        mac = parts[1].replace('-', ':').upper()
                        # Filter out virtual/loopback/blank
                        if mac and mac != '00:00:00:00:00:00' and not mac.startswith('00:50:56'):
                            macs.append(mac)
            else:
                # Linux/macOS: parse ifconfig/ip
                result = subprocess.run(
                    ['ip', 'link'] if sys.platform.startswith('linux') else ['ifconfig', '-a'],
                    capture_output=True, text=True, timeout=10
                )
                # Match MAC addresses in standard format
                pattern = r'(?:ether|link/ether)\s+([0-9a-fA-F:]{17})'
                for match in re.finditer(pattern, result.stdout):
                    mac = match.group(1).upper()
                    if mac and mac != '00:00:00:00:00:00':
                        macs.append(mac)
        except Exception:
            pass
        return sorted(set(macs)) if macs else ['NO_MAC']
    
    @staticmethod
    def get_disk_serials() -> List[str]:
        """Get disk serial numbers (Windows prioritized)"""
        serials = []
        try:
            if sys.platform == "win32":
                # Try wmic first (most reliable)
                result = subprocess.run(
                    ['wmic', 'diskdrive', 'get', 'serialnumber'],
                    capture_output=True, text=True, timeout=15
                )
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    serial = line.strip()
                    if serial and serial != 'SerialNumber':
                        # Clean and normalize
                        serial = re.sub(r'[^A-Za-z0-9]', '', serial).upper()
                        if serial:
                            serials.append(serial[:32])  # Truncate for consistency
                
                # Fallback: PowerShell if wmic failed
                if not serials:
                    result = subprocess.run(
                        ['powershell', '-Command', 
                         'Get-WmiObject Win32_DiskDrive | Select-Object -ExpandProperty SerialNumber'],
                        capture_output=True, text=True, timeout=15
                    )
                    for line in result.stdout.strip().split('\n'):
                        serial = line.strip()
                        if serial:
                            serial = re.sub(r'[^A-Za-z0-9]', '', serial).upper()
                            if serial:
                                serials.append(serial[:32])
            else:
                # Linux: try lsblk or udev
                for cmd in [['lsblk', '-ndo', 'SERIAL'], ['udevadm', 'info', '--query=property', '--name=/dev/sda']]:
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
                        for line in result.stdout.split('\n'):
                            if 'ID_SERIAL=' in line or (cmd[0] == 'lsblk' and line.strip()):
                                serial = line.split('=')[-1].strip().upper()
                                if serial:
                                    serials.append(re.sub(r'[^A-Za-z0-9]', '', serial)[:32])
                                break
                    except:
                        continue
        except Exception:
            pass
        return sorted(set(serials)) if serials else ['NO_DISK']
    
    @staticmethod
    def get_bios_info() -> str:
        """Get BIOS/UEFI identifier (most stable across reinstalls)"""
        try:
            if sys.platform == "win32":
                # Get BIOS serial/UUID via wmic
                for query in ['bios get serialnumber', 'csproduct get uuid']:
                    result = subprocess.run(
                        ['wmic'] + query.split(),
                        capture_output=True, text=True, timeout=10
                    )
                    for line in result.stdout.strip().split('\n')[1:]:
                        value = line.strip()
                        if value and value.lower() not in ['serialnumber', 'uuid', 'to be filled by o.e.m.']:
                            return re.sub(r'[^A-Za-z0-9]', '', value).upper()[:32]
            else:
                # Linux: read from sysfs
                for path in ['/sys/class/dmi/id/product_uuid', '/sys/class/dmi/id/board_serial']:
                    if os.path.exists(path):
                        with open(path, 'r') as f:
                            value = f.read().strip().upper()
                            if value and value != '00000000-0000-0000-0000-000000000000':
                                return re.sub(r'[^A-Za-z0-9]', '', value)[:32]
        except Exception:
            pass
        return 'NO_BIOS'
    
    @staticmethod
    def get_system_uuid() -> str:
        """Get system UUID as fallback"""
        try:
            # Python's uuid.getnode() uses MAC, but we want system UUID
            if sys.platform == "win32":
                result = subprocess.run(
                    ['wmic', 'csproduct', 'get', 'uuid'],
                    capture_output=True, text=True, timeout=10
                )
                for line in result.stdout.strip().split('\n')[1:]:
                    uuid_val = line.strip()
                    if uuid_val and uuid_val.lower() != 'uuid':
                        return re.sub(r'[^A-Za-z0-9]', '', uuid_val).upper()[:32]
            # Fallback to Python UUID (less stable but better than nothing)
            return uuid.getnode()
        except:
            return str(uuid.getnode())
    
    @staticmethod
    def generate_stable_id() -> str:
        """
        Generate stable hardware ID that survives Windows reinstall
        but changes on different hardware
        
        Priority order (most stable first):
        1. BIOS/UEFI serial/UUID
        2. Primary disk serial
        3. MAC addresses (sorted, concatenated)
        4. System UUID fallback
        """
        components = []
        
        # 1. BIOS info (most stable)
        bios = HardwareID.get_bios_info()
        if bios != 'NO_BIOS':
            components.append(f"BIOS:{bios}")
        
        # 2. Disk serials (stable unless drive replaced)
        disks = HardwareID.get_disk_serials()
        if disks and disks != ['NO_DISK']:
            # Use first non-generic disk serial
            for disk in disks:
                if disk not in ['NO_DISK', '']:
                    components.append(f"DISK:{disk}")
                    break
        
        # 3. MAC addresses (sorted for consistency)
        macs = HardwareID.get_mac_addresses()
        if macs and macs != ['NO_MAC']:
            # Concatenate all real MACs, sorted
            real_macs = [m for m in macs if m not in ['NO_MAC', '']]
            if real_macs:
                components.append(f"MAC:{':'.join(sorted(real_macs)[:3])}")  # Limit to 3
        
        # 4. System UUID fallback
        sys_uuid = HardwareID.get_system_uuid()
        if sys_uuid:
            components.append(f"UUID:{str(sys_uuid)[:32]}")
        
        # Combine and hash
        combined = '|'.join(components) if components else 'UNKNOWN_HARDWARE'
        
        # SHA256 hash, truncated to 32 chars for license key compatibility
        hardware_id = hashlib.sha256(combined.encode('utf-8')).hexdigest()[:32].upper()
        
        return hardware_id
    
    @staticmethod
    def get_detailed_info() -> dict:
        """Get detailed hardware info for debugging/admin use"""
        return {
            "hardware_id": HardwareID.generate_stable_id(),
            "bios_info": HardwareID.get_bios_info(),
            "disk_serials": HardwareID.get_disk_serials(),
            "mac_addresses": HardwareID.get_mac_addresses(),
            "system_uuid": HardwareID.get_system_uuid(),
            "platform": platform.system(),
            "platform_release": platform.release(),
            "platform_version": platform.version(),
            "machine": platform.machine(),
            "processor": platform.processor(),
            "hostname": platform.node(),
            "generated_at": __import__('datetime').datetime.now().isoformat()
        }


def get_hardware_id() -> str:
    """Convenience function to get hardware ID"""
    return HardwareID.generate_stable_id()


def get_hardware_info() -> dict:
    """Convenience function to get detailed hardware info"""
    return HardwareID.get_detailed_info()


if __name__ == "__main__":
    # Test mode: print hardware info
    print("\n" + "="*60)
    print("ZEMmacOS Hardware ID Generator - Test Mode")
    print("="*60)
    
    info = get_hardware_info()
    for key, value in info.items():
        if isinstance(value, list):
            print(f"{key:20s}: {', '.join(value)}")
        else:
            print(f"{key:20s}: {value}")
    
    print("\n" + "-"*60)
    print(f"Final Hardware ID: {info['hardware_id']}")
    print("="*60 + "\n")