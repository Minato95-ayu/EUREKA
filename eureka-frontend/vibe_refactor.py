import os
import glob
import re
import shutil

moves = {
    "src/types/index.ts": "src/core/EurekaTypes.ts",
    "src/data/fallbackObjects.ts": "src/core/FallbackSynthesizer.ts",
    "src/data/constants.ts": "src/core/Constants.ts",
    "src/components/canvas/LabScene.tsx": "src/engine/HolographicLab.tsx",
    "src/components/canvas/ComponentMesh.tsx": "src/engine/MeshRenderer.tsx",
    "src/components/canvas/GltfModelWrapper.tsx": "src/engine/ModelLoader.tsx",
    "src/components/dashboard/StatusScreen.tsx": "src/hud/TelemetryScreen.tsx",
    "src/components/dashboard/MetricCard.tsx": "src/hud/MetricWidget.tsx",
    "src/components/dashboard/BatchScreen.tsx": "src/hud/SimulationBatch.tsx",
    "src/components/dashboard/PipelineScreen.tsx": "src/hud/AgentPipeline.tsx",
    "src/components/dashboard/ResearchScreen.tsx": "src/hud/KnowledgeGraph.tsx",
    "src/components/dashboard/ResultsScreen.tsx": "src/hud/AnalysisResults.tsx",
    "src/hooks/useVoiceControl.ts": "src/neural/AriaVoiceLink.ts",
    "src/hooks/useHandTracking.ts": "src/neural/MediaPipeVision.ts",
    "src/services/api.ts": "src/neural/DataRelay.ts",
    "src/components/layout/AriaPanel.tsx": "src/ui/AriaTerminal.tsx",
    "src/components/layout/TopBar.tsx": "src/ui/TopNav.tsx",
    "src/components/layout/BottomNav.tsx": "src/ui/BottomDock.tsx"
}

# 1. Move files
for src_path, dst_path in moves.items():
    if os.path.exists(src_path):
        os.makedirs(os.path.dirname(dst_path), exist_ok=True)
        shutil.move(src_path, dst_path)
        print(f"Moved {src_path} to {dst_path}")

# 2. String replacements across all files
replacements = [
    (r"useVoiceControl", "useAriaVoiceLink"),
    (r"useHandTracking", "useMediaPipeVision"),
    (r"LabScene", "HolographicLab"),
    (r"ComponentMesh", "MeshRenderer"),
    (r"GltfModelWrapper", "ModelLoader"),
    (r"StatusScreen", "TelemetryScreen"),
    (r"MetricCard", "MetricWidget"),
    (r"BatchScreen", "SimulationBatch"),
    (r"PipelineScreen", "AgentPipeline"),
    (r"ResearchScreen", "KnowledgeGraph"),
    (r"ResultsScreen", "AnalysisResults"),
    (r"AriaPanel", "AriaTerminal"),
    (r"TopBar", "TopNav"),
    (r"BottomNav", "BottomDock"),
]

def replace_in_file(filepath):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for old, new in replacements:
        content = re.sub(r'\b' + old + r'\b', new, content)
    
    # Fix import paths. Since all files are 1 level deep inside src (e.g. src/engine/HolographicLab.tsx),
    # imports to other domains are just ../domain/File
    
    # Imports to types
    content = re.sub(r"from ['\"].*?types(?:/index)?['\"]", "from '../core/EurekaTypes'", content)
    # Imports to constants/fallbackObjects
    content = re.sub(r"from ['\"].*?data/constants['\"]", "from '../core/Constants'", content)
    content = re.sub(r"from ['\"].*?data/fallbackObjects['\"]", "from '../core/FallbackSynthesizer'", content)
    
    # Imports to canvas
    content = re.sub(r"from ['\"].*?canvas/LabScene['\"]", "from '../engine/HolographicLab'", content)
    content = re.sub(r"from ['\"].*?canvas/ComponentMesh['\"]", "from '../engine/MeshRenderer'", content)
    content = re.sub(r"from ['\"].*?canvas/GltfModelWrapper['\"]", "from '../engine/ModelLoader'", content)
    
    # Imports to dashboard
    content = re.sub(r"from ['\"].*?dashboard/StatusScreen['\"]", "from '../hud/TelemetryScreen'", content)
    content = re.sub(r"from ['\"].*?dashboard/MetricCard['\"]", "from '../hud/MetricWidget'", content)
    content = re.sub(r"from ['\"].*?dashboard/BatchScreen['\"]", "from '../hud/SimulationBatch'", content)
    content = re.sub(r"from ['\"].*?dashboard/PipelineScreen['\"]", "from '../hud/AgentPipeline'", content)
    content = re.sub(r"from ['\"].*?dashboard/ResearchScreen['\"]", "from '../hud/KnowledgeGraph'", content)
    content = re.sub(r"from ['\"].*?dashboard/ResultsScreen['\"]", "from '../hud/AnalysisResults'", content)
    
    # Imports to layout
    content = re.sub(r"from ['\"].*?layout/AriaPanel['\"]", "from '../ui/AriaTerminal'", content)
    content = re.sub(r"from ['\"].*?layout/TopBar['\"]", "from '../ui/TopNav'", content)
    content = re.sub(r"from ['\"].*?layout/BottomNav['\"]", "from '../ui/BottomDock'", content)
    
    # Imports to hooks
    content = re.sub(r"from ['\"].*?hooks/useVoiceControl['\"]", "from '../neural/AriaVoiceLink'", content)
    content = re.sub(r"from ['\"].*?hooks/useHandTracking['\"]", "from '../neural/MediaPipeVision'", content)
    
    # Imports to services
    content = re.sub(r"from ['\"].*?services/api['\"]", "from '../neural/DataRelay'", content)

    # Fix intra-domain imports (like HolographicLab importing MeshRenderer)
    content = re.sub(r"from '\.\./engine/", "from './", content)
    content = re.sub(r"from '\.\./hud/", "from './", content)
    content = re.sub(r"from '\.\./core/", "from './", content)
    content = re.sub(r"from '\.\./neural/", "from './", content)
    content = re.sub(r"from '\.\./ui/", "from './", content)
    
    # App.tsx is in src/, so its imports should be ./domain/File
    if filepath.endswith("App.tsx") or filepath.endswith("App.css"):
        content = content.replace("from '../core/", "from './core/")
        content = content.replace("from '../engine/", "from './engine/")
        content = content.replace("from '../hud/", "from './hud/")
        content = content.replace("from '../neural/", "from './neural/")
        content = content.replace("from '../ui/", "from './ui/")
        # Remove barrel imports from App.tsx since we deleted index.ts files
        content = re.sub(r"from '\./components/.*?/index'", "", content)
        content = re.sub(r"from '\./components/.*?'", "", content)

    if content != original_content:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated {filepath}")

for root, _, files in os.walk("src"):
    for file in files:
        if file.endswith((".ts", ".tsx", ".css")):
            replace_in_file(os.path.join(root, file))

# 3. Delete old directories
for d in ["src/components/canvas", "src/components/dashboard", "src/components/layout", "src/components", "src/hooks", "src/services", "src/types", "src/data"]:
    if os.path.exists(d):
        try:
            for root, dirs, files in os.walk(d, topdown=False):
                for name in files:
                    os.remove(os.path.join(root, name))
                for name in dirs:
                    os.rmdir(os.path.join(root, name))
            os.rmdir(d)
            print(f"Removed dir {d}")
        except Exception as e:
            print(f"Could not remove {d}: {e}")
