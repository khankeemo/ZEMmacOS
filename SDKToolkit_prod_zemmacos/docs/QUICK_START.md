# Quick Start Guide

## 1. Copy SDK Folder

Copy `WSD_SDK_PROJECTNAME_PRODUCTID/` into your project.

## 2. Import License Engine

```python
from WSD_SDK_PROJECTNAME_PRODUCTID.license_engine import LicenseEngine
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.dashboard_widget import LicenseWidget
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.activation_button import ActivationButton
from WSD_SDK_PROJECTNAME_PRODUCTID.widgets.settings_widget import SettingsWidget
```

## 3. Add Dashboard Widget

```python
widget = LicenseWidget(parent)
widget.build()
```

Place in the top-right corner of your dashboard.

## 4. Add Activation Button

```python
btn = ActivationButton(parent, engine)
btn.build()
```

## 5. Add Settings Widget

```python
settings = SettingsWidget(parent, engine)
settings.build()
```

Place under: `Settings > License`

## 6. Run

```bash
pip install requests
python main.py
```

That is all. No additional licensing code is required.
