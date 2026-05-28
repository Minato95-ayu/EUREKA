import runpod
import base64
import io
import os
import uuid
from PIL import Image
from rembg import remove
# Import the TRELLIS pipeline (adjust imports based on the specific repo structure)
from trellis.pipelines import TrellisImageTo3DPipeline
from trellis.utils.render_utils import export_to_glb

# Global variable for the model to keep it in memory while the pod is warm
pipeline = None

def load_model():
    """Load the model only once when the worker starts."""
    global pipeline
    if pipeline is None:
        print("Loading TRELLIS model into VRAM...")
        # Load the pre-trained pipeline and move to GPU
        pipeline = TrellisImageTo3DPipeline.from_pretrained('JeffreyXiang/TRELLIS-image-large')
        pipeline.cuda()
        print("Model loaded successfully.")

def process_image(image_base64):
    """Decode base64 and remove background."""
    # Decode base64 to PIL Image
    image_data = base64.b64decode(image_base64)
    img = Image.open(io.BytesIO(image_data))
    
    # Remove background (Crucial for TRELLIS to understand object boundaries)
    no_bg_img = remove(img)
    return no_bg_img

def handler(job):
    """
    This is the core function RunPod calls when an API request comes in.
    The 'job' dictionary contains the input sent from your EUREKA backend.
    """
    try:
        job_input = job['input']
        
        # Expecting a base64 encoded image string from the Vite/FastAPI frontend
        if 'image_base64' not in job_input:
            return {"error": "Missing 'image_base64' in input"}
        
        # 1. Process Image
        processed_image = process_image(job_input['image_base64'])

        # 2. Run Inference (Image to 3D representation)
        # TRELLIS usually returns a structured object containing the multi-view latent data
        print("Running TRELLIS Inference...")
        outputs = pipeline.run(processed_image, seed=42)
        
        # 3. Export to GLB (Mesh + Textures)
        output_filename = f"/tmp/{uuid.uuid4()}.glb"
        # The export function extracts geometry and bakes PBR textures
        export_to_glb(outputs, output_filename)

        # 4. Read the generated .glb file and convert to base64 to send back
        with open(output_filename, "rb") as f:
            glb_data = f.read()
        
        glb_base64 = base64.b64encode(glb_data).decode('utf-8')
        
        # Clean up temporary file
        os.remove(output_filename)

        return {
            "status": "success",
            "glb_base64": glb_base64
        }

    except Exception as e:
        return {"error": str(e)}

# Start the RunPod Serverless worker
if __name__ == '__main__':
    load_model()
    runpod.serverless.start({"handler": handler})
