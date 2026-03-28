import sys
from unittest.mock import MagicMock

# Mock streamlit so zkp_circuit.py loads cleanly outside Streamlit
sys.modules['streamlit'] = MagicMock()

from zkp_circuit import VotingCircuit
from zksnake.groth16 import Groth16

# Force fresh key generation
r1cs = VotingCircuit._build_r1cs()
proof_system = Groth16(r1cs)
proof_system.setup()
VotingCircuit._proof_system = proof_system
VotingCircuit._r1cs = r1cs

vk = VotingCircuit._proof_system.verifying_key
print(f"[DEBUG] vk.ic length = {len(vk.ic)}")

VotingCircuit.export_keys_as_secrets()