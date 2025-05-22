# fix_imports.py
import os

def fix_imports(directory):
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                filepath = os.path.join(root, file)
                with open(filepath, 'r') as f:
                    content = f.read()
                
                # Skip __init__.py files that are already fixed
                if file == '__init__.py' and '.holographic_controller' in content:
                    continue
                
                # Fix same-directory imports
                if 'from power_management import' in content:
                    content = content.replace('from power_management import', 'from .power_management import')
                if 'from holographic_controller import' in content:
                    content = content.replace('from holographic_controller import', 'from .holographic_controller import')
                if 'from system_interface import' in content:
                    content = content.replace('from system_interface import', 'from .system_interface import')
                
                # Write modified content back
                with open(filepath, 'w') as f:
                    f.write(content)
                    print(f"Fixed imports in {filepath}")

if __name__ == "__main__":
    fix_imports("src")