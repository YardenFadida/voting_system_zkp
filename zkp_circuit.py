import hashlib
import json

try:
    from zksnake.groth16 import Groth16, Proof
    from zksnake.arithmetization import ConstraintSystem, R1CS, Var
    from zksnake.constant import BN254_SCALAR_FIELD
except ImportError as e:
    print(f"[DEBUG] Error during imports {e}")


class VotingCircuit:
    """zk-SNARK implementation using zksnake lib"""
    
    _proof_system = None
    _r1cs = None
    
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
            if isinstance(point, (tuple, list)):
                if len(point) == 2:
                    if isinstance(point[0], (tuple, list)):
                        return [[str(p) for p in subpoint] for subpoint in point]
                    else:
                        return [str(point[0]), str(point[1])]
                else:
                    return [str(p) for p in point]
            elif hasattr(point, 'x') and hasattr(point, 'y'):
                return [str(point.x), str(point.y)]
            else:
                return str(point)

        except Exception as e:
            print(f"[DEBUG] Error during serialization: {e}")

    @staticmethod
    def _deserialize_point(data):
        """Deserialize points"""
        if isinstance(data, list):
            if len(data) == 2:
                if isinstance(data[0], list):
                    # G2 point (point B): nested list [[x0,x1],[y0,y1]]
                    return tuple(tuple(int(p) for p in subpoint) for subpoint in data)
                else:
                    # G1 point (points A and C): [x, y]
                    return (int(data[0]), int(data[1]))
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
            VotingCircuit._setup_circuit()
            
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
            
            VotingCircuit._setup_circuit()
            # Reconstruct proof object from A, B, C
            A = VotingCircuit._deserialize_point(proof_dict['proof']['A'])
            B = VotingCircuit._deserialize_point(proof_dict['proof']['B'])
            C = VotingCircuit._deserialize_point(proof_dict['proof']['C'])
            proof = Proof(A, B, C)
            public_inputs = proof_dict['public_inputs']

            is_valid = VotingCircuit._proof_system.verify(proof, public_inputs)

            if is_valid:
                return True, "Proof verified"
            else:
                return False, "Proof verification failed"
        
        except Exception as e:
            print(f"[ZKSNAKE] Verification error: {e}")
            return False, f"Verification error: {str(e)}"
