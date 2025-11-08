#!/usr/bin/env python
"""Compile Babel translation files using Babel's Python API"""
import os
import sys

def compile_translations():
    """Compile .po files to .mo files using Babel's Python API"""
    translations_dir = 'babel/translations'
    
    # Ensure translations directory exists
    if not os.path.exists(translations_dir):
        print(f'⚠ Translations directory not found: {translations_dir}')
        return False
    
    try:
        from babel.messages.catalog import Catalog
        from babel.messages.pofile import read_po, write_po
        from babel.messages.mofile import write_mo
    except ImportError:
        print('✗ Babel not installed. Trying subprocess method...')
        return compile_translations_subprocess()
    
    success = True
    
    for lang in ['ca', 'es']:
        po_file = f'{translations_dir}/{lang}/LC_MESSAGES/messages.po'
        mo_file = f'{translations_dir}/{lang}/LC_MESSAGES/messages.mo'
        
        if not os.path.exists(po_file):
            print(f'⚠ PO file not found: {po_file}')
            continue
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(mo_file), exist_ok=True)
        
        try:
            # Read PO file
            with open(po_file, 'rb') as f:
                catalog = read_po(f, locale=lang)
            
            # Write MO file
            with open(mo_file, 'wb') as f:
                write_mo(f, catalog)
            
            print(f'✓ Compiled {lang}/LC_MESSAGES/messages.mo ({len(catalog)} messages)')
        except Exception as e:
            print(f'✗ Error compiling {lang}: {e}')
            success = False
    
    return success

def compile_translations_subprocess():
    """Fallback: compile using subprocess"""
    import subprocess
    translations_dir = 'babel/translations'
    success = True
    
    for lang in ['ca', 'es']:
        po_file = f'{translations_dir}/{lang}/LC_MESSAGES/messages.po'
        
        if not os.path.exists(po_file):
            continue
        
        # Try using python -m babel
        try:
            result = subprocess.run(
                ['python', '-m', 'babel.messages.frontend', 'compile', 
                 '-d', translations_dir, '-l', lang],
                check=True,
                capture_output=True,
                text=True
            )
            print(f'✓ Compiled {lang} using babel.messages.frontend')
        except Exception as e:
            print(f'✗ Could not compile {lang}: {e}')
            success = False
    
    return success

if __name__ == '__main__':
    success = compile_translations()
    if not success:
        print('⚠ Some translations failed to compile, but continuing...')
    sys.exit(0 if success else 1)

