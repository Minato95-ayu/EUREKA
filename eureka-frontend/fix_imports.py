import os
import re

fixes = [
    # Fix broken relative imports
    (r"from '\./EurekaTypes'", "from '../core/EurekaTypes'"),
    (r"from '\./Constants'", "from '../core/Constants'"),
    (r"from '\./FallbackSynthesizer'", "from '../core/FallbackSynthesizer'"),
    (r"from '\./HolographicLab'", "from '../engine/HolographicLab'"),
    (r"from '\./MeshRenderer'", "from '../engine/MeshRenderer'"),
    (r"from '\./ModelLoader'", "from '../engine/ModelLoader'"),
    (r"from '\./DataRelay'", "from '../neural/DataRelay'"),
    (r"from '\./AriaVoiceLink'", "from '../neural/AriaVoiceLink'"),
    (r"from '\./MediaPipeVision'", "from '../neural/MediaPipeVision'"),
    (r"from '\.\./canvas/HolographicLab'", "from '../engine/HolographicLab'"),
    
    # Fix implicit any by adding types to callbacks in maps/etc
    (r"\(sub\) =>", "(sub: any) =>"),
    (r"\(sub, idx\) =>", "(sub: any, idx: number) =>"),
    (r"\(component\) =>", "(component: any) =>"),
    (r"\(tab\) =>", "(tab: any) =>"),
    (r"\(state\) =>", "(state: any) =>"),
]

for root, _, files in os.walk("src"):
    for file in files:
        if file.endswith((".ts", ".tsx")):
            # Don't touch App.tsx for the relative imports since they ARE in fact ./core etc there
            if file == "App.tsx":
                continue
                
            filepath = os.path.join(root, file)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            original_content = content
            for old, new in fixes:
                content = re.sub(old, new, content)
            
            # Special case for App.tsx which is in root
            if content != original_content:
                with open(filepath, 'w', encoding='utf-8') as f:
                    f.write(content)
                print(f"Updated {filepath}")
