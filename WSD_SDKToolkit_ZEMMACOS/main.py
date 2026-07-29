"""SDK Entry Point — demonstrates correct startup architecture.

Architecture (per UNIVERSAL_LICENSE_PLATFORM_IMPLEMENTATION.md):

1. LicenseEngine.initialize() runs exactly once at startup.
   It is the single source of truth for license state.
2. The returned LicenseStatus is passed to UniversalLicenseCenter
   as initial_status.
3. ULC never calls LicenseEngine.initialize() or makes its own
   license decision. It only displays the pre-initialized status.
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from universal_license_center import UniversalLicenseCenter
from license_engine import LicenseEngine


def main():
    engine = LicenseEngine()
    status = engine.initialize()

    print(f"Startup decision: status={status.status}, valid={status.valid}")

    center = UniversalLicenseCenter(
        initial_status=status,
        on_license_ready=lambda valid: print(
            f"License ready callback: valid={valid}"
        ),
    )

    result = center.show()

    if result.get("unlocked"):
        print("Application unlocked and running.")
    else:
        print("Application remains locked.")
        sys.exit(0)


if __name__ == "__main__":
    main()
