from typing import Dict, List, Tuple, Any
import logging
from rdkit import Chem
from rdkit.Chem import AllChem, Descriptors, Crippen
import numpy as np

logger = logging.getLogger(__name__)

class ChemistryEngine:
    """Handles chemistry calculations and reactions"""
    
    def __init__(self):
        self.molecules: Dict[str, Chem.Mol] = {}
        self.reactions: List[Dict] = []
    
    def create_molecule_from_smiles(self, smiles: str, mol_id: str) -> bool:
        """Create molecule from SMILES string"""
        try:
            mol = Chem.MolFromSmiles(smiles)
            if mol is None:
                logger.error(f"Invalid SMILES: {smiles}")
                return False
            
            # Add hydrogens
            mol = Chem.AddHs(mol)
            
            # Try to generate 3D coordinates
            try:
                # Embed molecule
                res = AllChem.EmbedMolecule(mol, randomSeed=42, maxAttempts=100)
                if res >= 0:
                    AllChem.UFFOptimizeMolecule(mol)
                else:
                    logger.warning(f"Embedding failed for SMILES: {smiles}, coordinates not generated.")
            except Exception as embed_err:
                logger.warning(f"3D coordinates embedding error: {embed_err}. Continuing with 2D representation.")
            
            self.molecules[mol_id] = mol
            logger.info(f"Created molecule: {mol_id}")
            return True
        except Exception as e:
            logger.error(f"Error creating molecule: {str(e)}")
            return False
    
    def get_molecular_properties(self, mol_id: str) -> Dict[str, Any]:
        """Get properties of a molecule"""
        if mol_id not in self.molecules:
            return {"error": f"Molecule {mol_id} not found"}
        
        mol = self.molecules[mol_id]
        
        try:
            properties = {
                "molecular_weight": float(Descriptors.MolWt(mol)),
                "logp": float(Crippen.MolLogP(mol)),
                "hbd": int(Descriptors.NumHDonors(mol)),  # H-bond donors
                "hba": int(Descriptors.NumHAcceptors(mol)),  # H-bond acceptors
                "rotatable_bonds": int(Descriptors.NumRotatableBonds(mol)),
                "aromatic_rings": int(Descriptors.NumAromaticRings(mol)),
                "tpsa": float(Descriptors.TPSA(mol)),  # Topological polar surface area
                "formula": str(Chem.rdMolDescriptors.CalcMolFormula(mol)),
                "num_atoms": int(mol.GetNumAtoms()),
                "num_bonds": int(mol.GetNumBonds())
            }
            return properties
        except Exception as e:
            logger.error(f"Error calculating properties for {mol_id}: {e}")
            return {"error": f"Property calculation error: {str(e)}"}
    
    def simulate_reaction(
        self, 
        reactant_smiles: List[str],
        product_smiles: List[str],
        conditions: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """Simulate a chemical reaction"""
        
        conditions = conditions or {}
        temperature = conditions.get("temperature", 298.15)  # Kelvin
        pressure = conditions.get("pressure", 1.0)  # atm
        
        # Create molecules
        reactants = []
        for smiles in reactant_smiles:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                reactants.append(mol)
        
        products = []
        for smiles in product_smiles:
            mol = Chem.MolFromSmiles(smiles)
            if mol:
                products.append(mol)
        
        if not reactants or not products:
            return {"error": "Invalid reactants or products"}
        
        # Calculate reaction properties
        reactant_weight = sum(Descriptors.MolWt(r) for r in reactants)
        product_weight = sum(Descriptors.MolWt(p) for p in products)
        
        # Energy estimation (simplified)
        energy_change = self._estimate_energy_change(reactants, products)
        
        reaction_data = {
            "reactants": [Chem.MolToSmiles(r) for r in reactants],
            "products": [Chem.MolToSmiles(p) for p in products],
            "reactant_weight": float(reactant_weight),
            "product_weight": float(product_weight),
            "mass_balance": bool(abs(reactant_weight - product_weight) < 0.1),
            "energy_change": float(energy_change),
            "temperature": float(temperature),
            "pressure": float(pressure),
            "feasible": bool(energy_change <= 0)  # Exothermic or neutral reactions are spontaneous
        }
        
        self.reactions.append(reaction_data)
        logger.info(f"Simulated reaction: {len(self.reactions)} reactions total")
        
        return reaction_data
    
    def _estimate_energy_change(self, reactants: List[Chem.Mol], products: List[Chem.Mol]) -> float:
        """Estimate energy change (simplified)"""
        reactant_energy = sum(self._estimate_molecule_energy(r) for r in reactants)
        product_energy = sum(self._estimate_molecule_energy(p) for p in products)
        return product_energy - reactant_energy
    
    def _estimate_molecule_energy(self, mol: Chem.Mol) -> float:
        """Estimate molecule energy (simplified)"""
        weight = Descriptors.MolWt(mol)
        atoms = mol.GetNumAtoms()
        bonds = mol.GetNumBonds()
        
        # Arbitrary energy estimation: weight * 0.1 + atoms * 5 + bonds * 2
        return weight * 0.1 + atoms * 5 + bonds * 2
    
    def predict_reaction_rate(
        self, 
        activation_energy: float,
        temperature: float
    ) -> float:
        """Predict reaction rate using Arrhenius equation"""
        # k = A * exp(-Ea/RT)
        # Assuming pre-exponential factor A = 1.0 for simplification
        R = 8.314  # J/(mol⋅K)
        
        if temperature <= 0:
            return 0.0
            
        try:
            rate_constant = np.exp(-activation_energy / (R * temperature))
            return float(rate_constant)
        except Exception:
            return 0.0
    
    def get_reaction_history(self) -> List[Dict]:
        """Get all simulated reactions"""
        return self.reactions
