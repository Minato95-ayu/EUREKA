import os
import io
import time
import torch
import numpy as np
from PIL import Image
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.responses import FileResponse
import trimesh
import tempfile
import rembg

# We assume this runs in the context of the TripoSR repo
try:
    from tsr.system import TSR
    from tsr.utils import remove_background, resize_foreground
except ImportError:
    print("Warning: TSR not found, running in mock mode for testing without GPU")
    TSR = None

app = FastAPI(title="TripoSR Inference API")

# Global model instance to keep it in VRAM
model = None
device = "cuda:0" if torch.cuda.is_available() else "cpu"

@app.on_event("startup")
def load_model():
    global model
    if TSR is not None:
        print(f"Loading TripoSR model on {device}...")
        model = TSR.from_pretrained("stabilityai/TripoSR", config_name="config.yaml", weight_name="model.ckpt")
        model.renderer.set_chunk_size(8192)
        model.to(device)
        print("TripoSR model loaded successfully.")

@app.get("/health")
def health_check():
    return {"status": "healthy", "device": device, "model_loaded": model is not None}

@app.post("/generate")
async def generate_3d(file: UploadFile = File(...)):
    """
    Accepts an image file, removes background, generates 3D mesh via TripoSR, 
    and returns a .glb file.
    """
    if file.content_type not in ["image/jpeg", "image/png", "image/webp"]:
        raise HTTPException(status_code=400, detail="Invalid file format. Please upload JPEG, PNG, or WEBP.")

    try:
        image_bytes = await file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # If in mock mode (e.g. testing locally without huge weights)
        if TSR is None:
            time.sleep(2) # simulate work
            mesh = trimesh.creation.box()
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
            mesh.export(temp_file.name, file_type='glb')
            return FileResponse(temp_file.name, media_type="model/gltf-binary", filename="generated.glb")

        # 1. Remove background using rembg
        print("Removing background...")
        if image.mode == "RGBA":
            image = image.convert("RGB")
        image_nobg = remove_background(image, rembg.new_session())

        # 2. Resize foreground to fit model expectations
        print("Resizing foreground...")
        image_processed = resize_foreground(image_nobg, 0.85)

        # 3. Generate 3D
        print("Generating 3D model...")
        with torch.no_grad():
            scene_codes = model(image_processed, device=device)
        
        # 4. Extract mesh
        print("Extracting mesh...")
        meshes = model.extract_mesh(scene_codes)
        
        # 5. Export to GLB
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".glb")
        meshes[0].export(temp_file.name, file_type='glb')
        
        return FileResponse(
            temp_file.name, 
            media_type="model/gltf-binary", 
            filename="generated.glb",
            headers={"Content-Disposition": "attachment; filename=generated.glb"}
        )
        
    except Exception as e:
        print(f"Error during generation: {e}")
        raise HTTPException(status_code=500, detail=str(e))
