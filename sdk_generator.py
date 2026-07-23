import os

TEMPLATES_DIR = os.path.join(os.path.dirname(__file__), 'sdk_templates')
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), 'WSD_SDKToolkit_ZEMMACOS')

TEMPLATES = {
    'universal_license_center.py': 'universal_license_center.tpl',
    'universal_email_dialog.py': 'universal_email_dialog.tpl',
}

VERSION = "1.0.0"
RUNTIME = "python"


def process_template(template_text: str) -> str:
    stripped = template_text.strip()
    if stripped.startswith("f'''"):
        stripped = stripped[4:]
    elif stripped.startswith("'''"):
        stripped = stripped[3:]
    if stripped.endswith("'''"):
        stripped = stripped[:-3]

    stripped = stripped.replace('{context.kitVersion}', VERSION)
    stripped = stripped.replace('{context.runtime}', RUNTIME)

    stripped = stripped.replace('{{', '{')
    stripped = stripped.replace('}}', '}')

    return stripped


def main():
    os.makedirs(TEMPLATES_DIR, exist_ok=True)
    for output_name, template_name in TEMPLATES.items():
        tpl_path = os.path.join(TEMPLATES_DIR, template_name)
        out_path = os.path.join(OUTPUT_DIR, output_name)
        if not os.path.exists(tpl_path):
            print(f"SKIP: {tpl_path} not found")
            continue
        with open(tpl_path, 'r', encoding='utf-8') as f:
            template_text = f.read()
        result = process_template(template_text)
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write(result)
        import py_compile
        try:
            py_compile.compile(out_path, doraise=True)
            print(f"OK: generated {output_name}")
        except py_compile.PyCompileError as e:
            print(f"FAIL: {output_name} -> {e}")


if __name__ == '__main__':
    main()
