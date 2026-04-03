import hashlib
from zkp_circuit import VotingCircuit

class VotingClient:
    """
    Client-side Responsibilities:
    1. Generate the ZK proof for the voter's choice
    2. Hand the proof to server.receive_vote, which handles
       token validation, ZKP verification, and vote recording
    """
    @staticmethod
    def submit_vote(server, voter_token, candidate_id):
        candidate_id = int(candidate_id)
        voter_token = (voter_token or "").strip()

        if not voter_token:
            return False, "Enter your voter token."

        voter_token_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        print(f"[CLIENT] Voter token hash: {voter_token_hash[:16]}...")

        try:
            print("[CLIENT] Generating zero-knowledge proof...")
            proof_data = VotingCircuit.generate_vote_proof( 
                voter_token,
                candidate_id,
                voter_token_hash
            )
            print("[CLIENT] Proof generated successfully")
            print(f"[CLIENT] Proof size: {len(proof_data)} bytes")
        except Exception as e:
            return False, f"Proof generation failed: {str(e)}"

        try:
            print("\n[CLIENT] Securely transmitting proof to server...")
            success, message = server.receive_vote(voter_token_hash, proof_data, candidate_id)

            if success:
                print(f"[CLIENT] Vote submitted successfully: {message}")
            else:
                print(f"[CLIENT] Vote submission failed: {message}")

            return success, message

        except Exception as e:
            print(f"[CLIENT] Error during vote submission: {str(e)}")
            return False, str(e)