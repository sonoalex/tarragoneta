#!/usr/bin/env python
"""Compile Babel translation files"""
import os
import subprocess
import sys

def compile_translations():
    """Compile .po files to .mo files"""
    translations_dir = 'babel/translations'
    
    for lang in ['ca', 'es']:
        po_file = f'{translations_dir}/{lang}/LC_MESSAGES/messages.po'
        mo_file = f'{translations_dir}/{lang}/LC_MESSAGES/messages.mo'
        
        if os.path.exists(po_file):
            try:
                # Try using msgfmt from gettext
                subprocess.run(['msgfmt', '-o', mo_file, po_file], check=True)
                print(f'✓ Compiled {lang}/LC_MESSAGES/messages.mo')
            except (subprocess.CalledProcessError, FileNotFoundError):
                # Fallback: use pybabel if available
                try:
                    subprocess.run(['pybabel', 'compile', '-d', translations_dir, '-l', lang], check=True)
                    print(f'✓ Compiled {lang} using pybabel')
                except (subprocess.CalledProcessError, FileNotFoundError):
                    print(f'⚠ Could not compile {lang}. Install gettext or pybabel.')
                    # Create empty .mo file as fallback
                    with open(mo_file, 'wb') as f:
                        f.write(b'')
                    print(f'  Created empty {mo_file}')

if __name__ == '__main__':
    compile_translations()

