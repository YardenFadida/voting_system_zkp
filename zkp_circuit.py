import hashlib
import json

try:
    from zksnake.groth16 import Groth16, Proof
    from zksnake.arithmetization import ConstraintSystem, R1CS, Var
    from zksnake.constant import BN254_SCALAR_FIELD
    from zksnake.ecc import ec_bn254
    PointG1 = ec_bn254.PointG1
    PointG2 = ec_bn254.PointG2
except ImportError as e:
    print(f"[DEBUG] Error during imports {e}")


class VotingCircuit:
    """zk-SNARK implementation using zksnake lib"""
    
    _proof_system = None
    _r1cs = None

    def __init__(self):
        VotingCircuit._setup_circuit()
    
    @staticmethod
    def _setup_circuit():
        """Setup a voting circuit"""
        
        if VotingCircuit._proof_system is not None:
            return
        
        # Define circuit: candidate must be 1, 2, or 3, can be expended.
        candidate = Var('candidate')
        cs = ConstraintSystem(['candidate'], [], BN254_SCALAR_FIELD)
        
        # Constraint: Only one candidate
        # This equation equals 0 only when candidate is 1, 2, or 3  
        temp1 = Var('temp1')
        temp2 = Var('temp2')
        
        cs.add_constraint(temp1 == (candidate - 1) * (candidate - 2))
        cs.add_constraint(temp2 == temp1 * (candidate - 3))
        cs.add_constraint(temp2 == 0)
        
        # Generate
        r1cs = R1CS(cs)
        r1cs.compile()
        
        proof_system = Groth16(r1cs)
        proof_system.setup()
        
        VotingCircuit._proof_system = proof_system
        VotingCircuit._r1cs = r1cs
    
    @staticmethod
    def _serialize_point(point):
        """Serialize points into a proper JSON format"""
        try:
            if hasattr(point, 'x') and hasattr(point, 'y'):
                x, y = point.x, point.y
                if isinstance(x, (tuple, list)):
                    # G2 point: x and y are [x0, x1] and [y0, y1]
                    return [[int(p) for p in x], [int(p) for p in y]]
                else:
                    # G1 point: x and y are plain integers
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
        """Deserialize points into zksnake point objects"""
        
        if isinstance(data, list):
            if len(data) == 2:
                if isinstance(data[0], list) or is_g2:
                    # G2 point (point B)
                    return PointG2(
                            int(data[0][0]),  # x0
                            int(data[0][1]),  # x1
                            int(data[1][0]),  # y0
                            int(data[1][1])   # y1
                            )
                else:
                    # G1 point (points A and C): [x, y]
                    return PointG1(int(data[0]), int(data[1]))
            else:
                return tuple(int(p) for p in data)
        else:
            return int(data)

    
    @staticmethod
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
            # Plug in voter choice
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
            return False, f"Verification error: {str(e)}"
