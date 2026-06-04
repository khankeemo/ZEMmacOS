# license_generator.py — API-only license generation (PostgreSQL authoritative)

import json
import os
import re
from datetime import datetime, timedelta
from typing import Optional

from admin_api_client import AdminAPIClient, resolve_admin_key

DEFAULT_EXPIRY_DAYS = 365
PRODUCT_NAME = "ZEMmacOS"
PRODUCT_VERSION = "3.0"


def validate_email(email: str) -> bool:
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


class LicenseGenerator:
    """
    Requests license creation from ZEM API — does NOT hold production authority.
    Export produces a JSON license receipt for customer reference (activation is server-side).
    """

    def __init__(self, api_client: AdminAPIClient = None):
        self.api = api_client or AdminAPIClient(admin_key=resolve_admin_key())

    def _check_existing_by_email(self, email: str) -> dict:
        result = self.api.search_by_email(email)
        if result.get("success"):
            return {"exists": True, "data": result}
        return {"exists": False}

    def generate_license(
        self,
        customer_name: str,
        customer_email: str,
        expiry_days: int = DEFAULT_EXPIRY_DAYS,
        license_key: str = None,
        plan: str = "Standard",
        devices: int = 1,
        notes: str = "",
    ) -> dict:
        if not customer_name:
            return {"error": "Customer name is required"}
        if not customer_email:
            return {"error": "Customer email is required"}
        if not validate_email(customer_email):
            return {"error": f"Invalid email format: {customer_email}"}
        if expiry_days <= 0:
            return {"error": "Expiry days must be positive"}

        existing = self._check_existing_by_email(customer_email)
        result = self.api.create_license(
            name=customer_name,
            email=customer_email,
            expiry_days=expiry_days,
            plan=plan,
            max_devices=devices,
            notes=notes,
            license_key=license_key,
        )

        if not result.get("success"):
            return {"error": result.get("error", "API create license failed")}

        key = result.get("license_key", license_key)
        expiry_str = result.get("expiry_date") or result.get("expiry", "")
        if not expiry_str:
            expiry_dt = datetime.now() + timedelta(days=expiry_days)
            expiry_str = expiry_dt.strftime("%Y-%m-%d")

        license_data = {
            "customer_name": customer_name.strip(),
            "customer_email": customer_email.strip().lower(),
            "license_key": key,
            "expiry_date": expiry_str,
            "plan": plan,
            "max_devices": devices,
            "status": "active",
            "product_name": PRODUCT_NAME,
            "product_version": PRODUCT_VERSION,
            "notes": notes,
            "source": "zem_api",
            "generated_at": datetime.now().isoformat(),
            "message": "Activate in ZEMmacOS Settings with name, email, and license key.",
        }

        receipt_json = json.dumps(license_data, indent=2)
        filename = f"license_{customer_email.replace('@', '_at_')}.json"
        if existing.get("exists"):
            filename = f"license_{customer_email.replace('@', '_at_')}_updated.json"

        return {
            "success": True,
            "data": license_data,
            "content": receipt_json,
            "filename": filename,
            "updated_existing": result.get("updated_existing", False),
            "license_key": key,
            "expiry_date": expiry_str,
            "api_response": result,
        }

    def generate_test_license(self) -> dict:
        result = self.api.create_test_license()
        if not result.get("success"):
            return {"error": result.get("error", "Test license creation failed")}
        license_data = {
            "customer_name": "Test User",
            "customer_email": "test@example.com",
            "license_key": result.get("license_key"),
            "expiry_date": result.get("expiry_date") or result.get("expiry"),
            "plan": "Professional",
            "status": "active",
            "source": "zem_api_test",
            "generated_at": datetime.now().isoformat(),
        }
        return {
            "success": True,
            "data": license_data,
            "content": json.dumps(license_data, indent=2),
            "filename": "license_test_zemmacos.json",
            "license_key": result.get("license_key"),
            "expiry_date": license_data.get("expiry_date"),
            "api_response": result,
        }

    def save_license(self, content: str, filename: str = None, output_dir: str = ".") -> str:
        if filename is None:
            filename = f"license_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        path = os.path.join(output_dir, filename)
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return path

    def validate_license_content(self, content: str) -> dict:
        """Parse exported JSON receipt (informational only — server validates activation)."""
        try:
            data = json.loads(content)
            if data.get("license_key"):
                return {"valid": True, "data": data}
            return {"valid": False, "error": "Missing license_key in receipt"}
        except json.JSONDecodeError:
            return {"valid": False, "error": "Invalid JSON license receipt"}


def _print_api_status():
    """Check backend before generating."""
    api = AdminAPIClient(admin_key=resolve_admin_key())
    health = api.health_check()
    if health.get("status") == "ok" or health.get("success"):
        print(f"[OK] License API online - database: {health.get('database', '?')} ({health.get('latency_ms', '?')}ms)")
        return api
    print(f"[ERROR] License API offline: {health.get('error', 'unknown')}")
    print("  Start the server first:  cd ..  &&  run_backend.bat")
    print("  Or from project root:    start_license_api.bat")
    return None


def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="ZEMmacOS License Generator (API-only — requires ZEM_API backend running)",
    )
    sub = parser.add_subparsers(dest="command", help="command")

    sub.add_parser("status", help="Check API and database status")

    p_test = sub.add_parser("test", help="Create test license on server (test@example.com)")
    p_test.add_argument("-o", "--output", default=".", help="Output directory for JSON receipt")

    p_create = sub.add_parser("create", help="Create a paid license via API")
    p_create.add_argument("name", help="Customer full name")
    p_create.add_argument("email", help="Customer email")
    p_create.add_argument("-d", "--days", type=int, default=DEFAULT_EXPIRY_DAYS, help="Expiry days")
    p_create.add_argument("-p", "--plan", default="Standard", help="Plan name")
    p_create.add_argument("--devices", type=int, default=1, help="Max devices")
    p_create.add_argument("-k", "--key", default=None, help="Optional license key")
    p_create.add_argument("-o", "--output", default=".", help="Output directory")

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        print("\nExamples:")
        print("  python license_generator.py status")
        print("  python license_generator.py test")
        print('  python license_generator.py create "John Doe" john@example.com')
        print("\nFor full GUI use:  python license_admin_ui.py   (or run_admin_ui.bat from project root)")
        return 1

    if args.command == "status":
        api = _print_api_status()
        return 0 if api else 1

    api = _print_api_status()
    if not api:
        return 1

    gen = LicenseGenerator(api)

    if args.command == "test":
        print("[*] Creating test license via POST /admin/create-test-license ...")
        result = gen.generate_test_license()
        if result.get("error"):
            print(f"[ERROR] {result['error']}")
            return 1
        path = gen.save_license(result["content"], result["filename"], args.output)
        print("[SUCCESS] Test license created on server (PostgreSQL/SQLite)")
        print(f"  License key:  {result.get('license_key')}")
        print(f"  Expiry:       {result.get('expiry_date')}")
        print(f"  Receipt:      {path}")
        print("\nActivate in ZEMmacOS: Settings > Manage License")
        print("  Name:  Test User")
        print("  Email: test@example.com")
        print(f"  Key:   {result.get('license_key')}")
        return 0

    if args.command == "create":
        print(f"[*] Creating license for {args.email} ...")
        result = gen.generate_license(
            args.name,
            args.email,
            expiry_days=args.days,
            license_key=args.key,
            plan=args.plan,
            devices=args.devices,
        )
        if result.get("error"):
            print(f"[ERROR] {result['error']}")
            return 1
        path = gen.save_license(result["content"], result["filename"], args.output)
        print("[SUCCESS] License created on server")
        print(f"  License key:  {result.get('license_key')}")
        print(f"  Expiry:       {result.get('expiry_date')}")
        print(f"  Receipt:      {path}")
        return 0

    return 1


if __name__ == "__main__":
    raise SystemExit(main())
