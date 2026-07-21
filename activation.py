"""Custom activation dialog wrapper for ZEMmacOS.
Auto-closes the SDK activation dialog on successful activation
so the parent can proceed with dashboard refresh and restart popup."""
from WSD_SDKToolkit_ZEMMACOS import ActivationDialog as SDKActivationDialog


def show_activation_dialog(client, product_name='ZEM MAC OS', cache=None):
    """Show SDK activation dialog with auto-close on successful activation.
    
    Returns the same dict as SDK's ActivationDialog.show():
    {'activated': bool, 'cancelled': bool, 'license_key': str}
    """
    d = SDKActivationDialog(client, product_name=product_name, cache=cache)
    original_on_activate = d._on_activate
    def patched_on_activate():
        original_on_activate()
        if d._activated and d._root and d._root.winfo_exists():
            d._root.after(800, d._root.destroy)
    d._on_activate = patched_on_activate
    return d.show()
