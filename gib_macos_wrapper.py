# gib_macos_wrapper.py - Direct gibMacOS integration without subprocess
import os
import sys

class GibMacOSWrapper:
    """Direct wrapper for gibMacOS functionality"""
    
    def __init__(self, callback=None):
        """
        Initialize wrapper
        
        Args:
            callback: Function to call for log messages (msg, type)
        """
        self.callback = callback
        self.gib = None
        self.products = []
        self.initialized = False
        
    def _log(self, message, msg_type="info"):
        """Log message via callback if available"""
        if self.callback:
            try:
                self.callback(message, msg_type)
            except:
                pass
        else:
            print(f"[{msg_type.upper()}] {message}")
    
    def initialize(self, catalog="publicrelease", maxos=20):
        """
        Initialize gibMacOS and fetch catalog
        
        Args:
            catalog: publicrelease, public, customer, developer
            maxos: Max macOS version (default 20 for Sequoia)
        """
        try:
            self._log("Initializing gibMacOS...", "info")
            
            # Import gibMacOS class directly
            from gibMacOS import gibMacOS
            
            # Create instance with interactive=False for non-interactive mode
            self.gib = gibMacOS(interactive=False)
            
            # Set catalog and max OS version
            self.gib.set_catalog(catalog)
            self.gib.current_macos = maxos
            
            self._log(f"Using catalog: {catalog}", "info")
            self._log(f"Max macOS version: {self.gib.num_to_macos(maxos, for_url=False)}", "info")
            
            # Fetch catalog data
            self._log("Fetching catalog from Apple...", "info")
            if not self.gib.get_catalog_data():
                self._log("Failed to fetch catalog data!", "error")
                return False
            
            # Set products
            self._log("Parsing product data...", "info")
            self.gib.set_prods()
            
            # Store products
            self.products = self.gib.mac_prods
            self.initialized = True
            
            self._log(f"Found {len(self.products)} macOS versions", "success")
            return True
            
        except Exception as e:
            self._log(f"Initialization failed: {str(e)}", "error")
            return False
    
    def get_products(self):
        """Get list of available products"""
        if not self.initialized:
            return []
        return self.products
    
    def get_product_display_list(self):
        """Get formatted display strings for products"""
        if not self.initialized:
            return []
        
        display_list = []
        for idx, prod in enumerate(self.products, 1):
            title = prod.get("title", "Unknown")
            version = prod.get("version", "Unknown")
            build = prod.get("build", "")
            
            if build and build != "Unknown":
                display_list.append(f"{idx}. {title} {version} ({build})")
            else:
                display_list.append(f"{idx}. {title} {version}")
        
        return display_list
    
    def download_product(self, index, download_dir=None):
        """
        Download product by index (1-based)
        
        Args:
            index: Product index (1-based)
            download_dir: Custom download directory
            
        Returns:
            True if successful, False otherwise
        """
        if not self.initialized:
            self._log("Not initialized. Call initialize() first.", "error")
            return False
        
        if index < 1 or index > len(self.products):
            self._log(f"Invalid index: {index}. Choose 1-{len(self.products)}", "error")
            return False
        
        product = self.products[index - 1]
        self._log(f"Starting download: {product.get('title')} {product.get('version')}", "info")
        
        try:
            # Set download directory if provided
            if download_dir:
                self.gib.download_dir = download_dir
            
            # Download the product
            self.gib.download_prod(product, dmg=False)
            self._log("Download completed successfully!", "success")
            return True
            
        except Exception as e:
            self._log(f"Download failed: {str(e)}", "error")
            return False
    
    def get_download_urls(self, index):
        """Get download URLs for a product without downloading"""
        if not self.initialized:
            return []
        
        if index < 1 or index > len(self.products):
            return []
        
        product = self.products[index - 1]
        urls = []
        
        for pkg in product.get("packages", []):
            url = pkg.get("URL", "")
            if url:
                urls.append(url)
        
        return urls