"""Welcome Dialog - First-launch onboarding for SDK customers"""
import json
import os
import threading
import webbrowser
from http.server import HTTPServer, BaseHTTPRequestHandler
from typing import Optional, Dict
from .client import Client
from .hardware import HardwareFingerprint
from .cache import CacheManager

class _WelcomeHandler(BaseHTTPRequestHandler):
    client: Optional[Client] = None
    cache: Optional[CacheManager] = None
    hardware: Optional[Dict] = None
    config: Optional[Dict] = None
    html: str = ""
    result: Dict = {}
    ready = threading.Event()

    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Access-Control-Allow-Origin', '*')
            self.end_headers()
            self.wfile.write(self.html.encode('utf-8'))
        elif self.path == '/api/countries':
            try:
                import urllib.request
                resp = urllib.request.urlopen(
                    'https://restcountries.com/v3.1/all?fields=name,idd,cca2,flag',
                    timeout=10
                )
                data = json.loads(resp.read().decode('utf-8'))
                countries = []
                for c in data:
                    idd = c.get('idd', {})
                    root = idd.get('root', '')
                    suffixes = idd.get('suffixes', [''])
                    code = root + (suffixes[0] if suffixes else '')
                    if code:
                        countries.append({
                            'code': c['cca2'],
                            'name': c['name']['common'],
                            'dial': code,
                            'flag': c.get('flag', '')
                        })
                countries.sort(key=lambda x: x['name'])
                self._json_response({'success': True, 'data': countries})
            except:
                fallback = [
                    {'code': 'US', 'name': 'United States', 'dial': '+1', 'flag': '🇺🇸'},
                    {'code': 'GB', 'name': 'United Kingdom', 'dial': '+44', 'flag': '🇬🇧'},
                    {'code': 'IN', 'name': 'India', 'dial': '+91', 'flag': '🇮🇳'},
                    {'code': 'CA', 'name': 'Canada', 'dial': '+1', 'flag': '🇨🇦'},
                    {'code': 'AU', 'name': 'Australia', 'dial': '+61', 'flag': '🇦🇺'},
                    {'code': 'DE', 'name': 'Germany', 'dial': '+49', 'flag': '🇩🇪'},
                    {'code': 'FR', 'name': 'France', 'dial': '+33', 'flag': '🇫🇷'},
                    {'code': 'BR', 'name': 'Brazil', 'dial': '+55', 'flag': '🇧🇷'},
                    {'code': 'JP', 'name': 'Japan', 'dial': '+81', 'flag': '🇯🇵'},
                    {'code': 'NG', 'name': 'Nigeria', 'dial': '+234', 'flag': '🇳🇬'},
                ]
                self._json_response({'success': True, 'data': fallback})
        elif self.path == '/api/status':
            onboarding = self.cache.is_onboarding_complete() if self.cache else False
            self._json_response({
                'success': True,
                'onboarding_complete': onboarding
            })
        else:
            self.send_response(404)
            self.end_headers()

    def do_POST(self):
        content_length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(content_length).decode('utf-8')
        data = json.loads(body) if body else {}

        try:
            if self.path == '/api/send-otp':
                email = data.get('email', '')
                result = self.client.send_otp(email)
                self._json_response({'success': True, 'message': 'OTP sent'})

            elif self.path == '/api/verify-otp':
                email = data.get('email', '')
                otp = data.get('otp', '')
                result = self.client.verify_otp(email, otp)
                self._json_response({'success': True, 'message': 'OTP verified'})

            elif self.path == '/api/complete-onboarding':
                name = data.get('name', '')
                email = data.get('email', '')
                mobile = data.get('mobile', '')
                country_code = data.get('country_code', '')
                company_name = data.get('company_name', '')
                hardware = self.hardware or HardwareFingerprint.generate_fingerprint()
                hardware_id = hardware['fingerprint']

                self.client.store_customer(name, email, mobile, country_code, company_name, hardware_id)
                self.client.start_trial(hardware_id, email, name)

                if self.cache:
                    self.cache.set_onboarding_complete()

                self.result = {
                    'name': name,
                    'email': email,
                    'hardware_id': hardware_id,
                    'onboarding_complete': True
                }
                self.ready.set()

                self._json_response({
                    'success': True,
                    'message': 'Welcome! Your trial has started.',
                    'hardware_id': hardware_id
                })

            else:
                self._json_response({'success': False, 'error': 'Not found'}, 404)

        except Exception as e:
            self._json_response({'success': False, 'error': str(e)}, 400)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()

    def _json_response(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(json.dumps(data).encode('utf-8'))

    def log_message(self, format, *args):
        pass


def _load_api_config() -> Dict:
    cfg_path = os.path.join(os.path.dirname(__file__), 'config', 'api-config.json')
    try:
        with open(cfg_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return {}


def _build_welcome_html(config: Dict) -> str:
    product = config.get('product', {})
    trial = config.get('trial', {})
    license_cfg = config.get('license', {})
    branding = config.get('branding', {})
    product_name = product.get('name', 'Software')
    product_version = product.get('version', '1.0.0')
    trial_days = trial.get('days', 7)
    max_devices = license_cfg.get('max_devices', 1)
    company = branding.get('company_name', '')
    support_email = branding.get('support_email', '')
    primary_color = branding.get('primary_color', '#6366f1')

    html_path = os.path.join(os.path.dirname(__file__), 'welcome.html')
    try:
        with open(html_path, 'r', encoding='utf-8') as f:
            html = f.read()
    except:
        html = '<html><body><h1>Welcome Dialog</h1><p>Failed to load dialog.</p></body></html>'

    config_json = json.dumps({
        'product_name': product_name,
        'product_version': product_version,
        'trial_days': trial_days,
        'max_devices': max_devices,
        'company': company,
        'support_email': support_email,
        'primary_color': primary_color
    })
    script_tag = f'<script>const PRODUCT_CONFIG = {config_json};</script>'
    html = html.replace('</head>', script_tag + '</head>')
    return html


class WelcomeDialog:
    def __init__(self, client: Client, product_name: str = 'websmith',
                 cache: Optional[CacheManager] = None):
        self.client = client
        self.product_name = product_name
        self.cache = cache or CacheManager(product_name)
        self.hardware = HardwareFingerprint.generate_fingerprint()
        self.config = _load_api_config()
        self._result: Optional[Dict] = None

    def is_onboarding_complete(self) -> bool:
        return self.cache.is_onboarding_complete()

    def show(self) -> Dict:
        if self.is_onboarding_complete():
            return {'skipped': True, 'message': 'Onboarding already completed'}

        port = self._find_free_port()
        server = self._start_server(port)

        url = f'http://localhost:{port}/'
        webbrowser.open(url)

        _WelcomeHandler.ready.wait(timeout=600)

        server.shutdown()
        self._result = _WelcomeHandler.result
        return self._result or {'skipped': True}

    def _find_free_port(self) -> int:
        import socket
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(('', 0))
            return s.getsockname()[1]

    def _start_server(self, port: int) -> HTTPServer:
        _WelcomeHandler.client = self.client
        _WelcomeHandler.cache = self.cache
        _WelcomeHandler.hardware = self.hardware
        _WelcomeHandler.config = self.config
        _WelcomeHandler.html = _build_welcome_html(self.config)
        _WelcomeHandler.ready.clear()

        server = HTTPServer(('127.0.0.1', port), _WelcomeHandler)

        t = threading.Thread(target=server.serve_forever, daemon=True)
        t.start()
        return server
