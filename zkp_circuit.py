import hashlib
import json
import time
import base64
import streamlit as st

try:
    from zksnake.groth16 import Groth16, Proof, ProvingKey, VerifyingKey
    from zksnake.arithmetization import ConstraintSystem, R1CS, Var
    from zksnake.constant import BN254_SCALAR_FIELD
    from zksnake.ecc import ec_bn254, EllipticCurve
    from zksnake.groth16.qap import QAP
    PointG1 = ec_bn254.PointG1
    PointG2 = ec_bn254.PointG2
except ImportError as e:
    print(f"[DEBUG] Error during imports {e}")


def measure_runtime(func):
    def wrapper(*args, **kwargs):
        start = time.perf_counter()
        result = func(*args, **kwargs)
        print(f"Proof runtime: {func.__name__}: {time.perf_counter() - start:.4f}s")
        return result
    return wrapper


class VotingCircuit:
    """zk-SNARK implementation using zksnake lib"""

    _proof_system = None
    _r1cs = None

    def __init__(self):
        VotingCircuit._setup_circuit()

    @staticmethod
    def _build_r1cs():
        candidate = Var('candidate')
        cs = ConstraintSystem(['candidate'], [], BN254_SCALAR_FIELD)
        # Constraint: Only one candidate
        # This equation equals 0 only when candidate is 1, 2, or 3 
        temp1 = Var('temp1')
        temp2 = Var('temp2')
        cs.add_constraint(temp1 == (candidate - 1) * (candidate - 2))
        cs.add_constraint(temp2 == temp1 * (candidate - 3))
        cs.add_constraint(temp2 == 0)
        cs.set_public(candidate)
        r1cs = R1CS(cs)
        r1cs.compile()
        return r1cs

    @staticmethod
    def _setup_circuit():
        if VotingCircuit._proof_system is not None:
            return

        try:
            if "ZKP_PROVING_KEY" in st.secrets and "ZKP_VERIFYING_KEY" in st.secrets:
                r1cs = VotingCircuit._build_r1cs()
                proof_system = Groth16.__new__(Groth16)
                proof_system.E = EllipticCurve("BN254")
                proof_system.order = proof_system.E.order
                proof_system.proving_key = ProvingKey.from_bytes(
                    base64.b64decode(st.secrets["ZKP_PROVING_KEY"])
                )
                proof_system.verifying_key = VerifyingKey.from_bytes(
                    base64.b64decode(st.secrets["ZKP_VERIFYING_KEY"])
                )
                if "ZKP_VK_IC" in st.secrets:
                    ic_data = json.loads(base64.b64decode(st.secrets["ZKP_VK_IC"]))
                    proof_system.verifying_key.ic = [
                        VotingCircuit._deserialize_point(p) for p in ic_data
                    ]
                qap = QAP(proof_system.order)
                qap.from_r1cs(r1cs)
                proof_system.qap = qap
                VotingCircuit._proof_system = proof_system
                VotingCircuit._r1cs = r1cs
                print("[CIRCUIT] Keys loaded from Streamlit secrets")
                return
        except Exception as e:
            print(f"[CIRCUIT] FAILED: {repr(e)}")

        print("[CIRCUIT] Falling back to generating new keys...")
        r1cs = VotingCircuit._build_r1cs()
        proof_system = Groth16(r1cs)
        proof_system.setup()
        VotingCircuit._proof_system = proof_system
        VotingCircuit._r1cs = r1cs
        print("[CIRCUIT] New keys generated")


    @staticmethod
    def _serialize_point(point):
        try:
            if hasattr(point, 'x') and hasattr(point, 'y'):
                x, y = point.x, point.y
                if isinstance(x, (tuple, list)):
                    return [[int(p) for p in x], [int(p) for p in y]]
                else:
                    return [int(x), int(y)]
            elif isinstance(point, (tuple, list)):
                if len(point) == 2 and isinstance(point[0], (tuple, list)):
                    return [[int(p) for p in subpoint] for subpoint in point]
                else:
                    return [int(p) for p in point]
            else:
                return int(point)
        except Exception as e:
            print(f"[DEBUG] Error during serialization: {e}")
            raise

    @staticmethod
    def _deserialize_point(data, is_g2=False):
        if isinstance(data, list):
            if len(data) == 2:
                if isinstance(data[0], list) or is_g2:
                    return PointG2(
                        int(data[0][0]),
                        int(data[0][1]),
                        int(data[1][0]),
                        int(data[1][1])
                    )
                else:
                    return PointG1(int(data[0]), int(data[1]))
            else:
                return tuple(int(p) for p in data)
        else:
            return int(data)

    @staticmethod
    @measure_runtime
    def generate_vote_proof(voter_token, candidate_id, voter_token_hash):
        """Generate zk-SNARK proof for vote"""
        # Validate inputs
        computed_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        if computed_hash != voter_token_hash:
            raise ValueError("Invalid voter token")
        
        if candidate_id not in [1, 2, 3]:
            raise ValueError("Invalid candidate ID")
        
        try:
            # Generate proof
            solution = VotingCircuit._r1cs.solve({'candidate': candidate_id})
            public_part, private_part = VotingCircuit._r1cs.generate_witness(solution)
            proof = VotingCircuit._proof_system.prove(public_part, private_part)
            
            # Serialize proof
            # Groth16 format, three elliptic curve points A, B, and C
            proof_data = {
                'proof_type': 'zksnake_groth16',
                'proof': {
                    'A': VotingCircuit._serialize_point(proof.A),
                    'B': VotingCircuit._serialize_point(proof.B),
                    'C': VotingCircuit._serialize_point(proof.C)
                },
                'public_inputs': [str(p) for p in public_part],
            }
            
            return json.dumps(proof_data)
        
        except Exception as e:
            print(f"[DEBUG] Error during proof generation: {e}")
            raise

    @staticmethod
    @measure_runtime
    def verify_vote_proof(proof_data):
        """Verify zk-SNARK proof"""
        try:
            proof_dict = json.loads(proof_data)
            
            if proof_dict.get('proof_type') != 'zksnake_groth16':
                return False, "Wrong proof format"

            if 'proof' not in proof_dict or 'public_inputs' not in proof_dict:
                return False, "Invalid proof structure"
            
            # Reconstruct proof object from A, B, C
            A = VotingCircuit._deserialize_point(proof_dict['proof']['A'])
            B = VotingCircuit._deserialize_point(proof_dict['proof']['B'], is_g2=True)
            C = VotingCircuit._deserialize_point(proof_dict['proof']['C'])
            proof = Proof(A, B, C)
            public_inputs = [int(p) for p in proof_dict['public_inputs']]

            is_valid = VotingCircuit._proof_system.verify(proof, public_inputs)

            if is_valid:
                return True, "Proof verified"
            else:
                return False, "Proof verification failed"

        except Exception as e:
            return False, f"Verification error: {e}"