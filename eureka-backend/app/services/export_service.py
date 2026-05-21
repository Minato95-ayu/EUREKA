from typing import Dict, Any
import logging
import json
import csv
from io import StringIO, BytesIO
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from datetime import datetime

logger = logging.getLogger(__name__)

class ExportService:
    """Handles experiment export in various formats"""
    
    async def export_json(self, experiment: Dict[str, Any]) -> str:
        """Export experiment as JSON"""
        try:
            return json.dumps(experiment, indent=2, default=str)
        except Exception as e:
            logger.error(f"Error exporting JSON: {e}")
            return "{}"
            
    async def export_csv(self, experiment: Dict[str, Any]) -> str:
        """Export experiment data as CSV"""
        try:
            output = StringIO()
            writer = csv.writer(output)
            
            # Write metadata
            writer.writerow(["Experiment Metadata"])
            writer.writerow(["Name", experiment.get("name", "")])
            writer.writerow(["Description", experiment.get("description", "")])
            writer.writerow(["Created", experiment.get("created_at", "")])
            writer.writerow([])
            
            # Write results
            writer.writerow(["Results"])
            results = experiment.get("results", {})
            
            if "trajectory" in results:
                writer.writerow(["Time", "Particle", "X", "Y", "Z", "VX", "VY", "VZ"])
                
                # Check structure of trajectory
                trajectory = results.get("trajectory", [])
                if isinstance(trajectory, list):
                    for step in trajectory:
                        if not isinstance(step, dict):
                            continue
                        time = step.get("time", 0.0)
                        for particle in step.get("particles", []):
                            if not isinstance(particle, dict):
                                continue
                            pos = particle.get("position", (0.0, 0.0, 0.0))
                            vel = particle.get("velocity", (0.0, 0.0, 0.0))
                            
                            # Standardize to list if they are lists/tuples
                            p_x, p_y, p_z = pos if len(pos) == 3 else (0.0, 0.0, 0.0)
                            v_x, v_y, v_z = vel if len(vel) == 3 else (0.0, 0.0, 0.0)
                            
                            writer.writerow([
                                time,
                                particle.get("id", ""),
                                p_x, p_y, p_z,
                                v_x, v_y, v_z
                            ])
            
            return output.getvalue()
        except Exception as e:
            logger.error(f"Error exporting CSV: {e}")
            return ""
            
    async def export_pdf(self, experiment: Dict[str, Any]) -> bytes:
        """Export experiment as PDF"""
        try:
            buffer = BytesIO()
            pdf = canvas.Canvas(buffer, pagesize=letter)
            
            # Title
            pdf.setFont("Helvetica-Bold", 16)
            pdf.drawString(50, 750, f"Experiment: {experiment.get('name', 'Unknown')}")
            
            # Metadata
            pdf.setFont("Helvetica", 10)
            y = 720
            pdf.drawString(50, y, f"Created: {experiment.get('created_at', '')}")
            y -= 20
            pdf.drawString(50, y, f"Description: {experiment.get('description', '')}")
            y -= 40
            
            # Results summary
            pdf.setFont("Helvetica-Bold", 12)
            pdf.drawString(50, y, "Results Summary")
            y -= 20
            
            results = experiment.get("results", {})
            pdf.setFont("Helvetica", 10)
            
            final_energy = results.get("final_energy")
            if final_energy is not None:
                try:
                    pdf.drawString(50, y, f"Final Energy: {float(final_energy):.2f}")
                    y -= 15
                except ValueError:
                    pdf.drawString(50, y, f"Final Energy: {final_energy}")
                    y -= 15
            
            sim_time = results.get("simulation_time")
            if sim_time is not None:
                try:
                    pdf.drawString(50, y, f"Simulation Time: {float(sim_time):.2f}s")
                    y -= 15
                except ValueError:
                    pdf.drawString(50, y, f"Simulation Time: {sim_time}")
                    y -= 15
            
            # Particle count if available
            particles = results.get("particles", [])
            if particles:
                pdf.drawString(50, y, f"Total Particles: {len(particles)}")
                y -= 15
            
            pdf.save()
            buffer.seek(0)
            return buffer.getvalue()
        except Exception as e:
            logger.error(f"Error exporting PDF: {e}")
            return b""
            
    async def generate_doi(self, experiment_id: str) -> str:
        """Generate DOI for experiment (simplified)"""
        # In production, integrate with DataCite or similar service
        doi = f"10.5555/eureka.{experiment_id[:8]}"
        return doi
