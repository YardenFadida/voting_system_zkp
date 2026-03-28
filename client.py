import hashlib

class VotingClient:
    """
    Client-side helper.
    Responsibilities:
      1. Generate the ZK proof for the voter's choice
      2. Hand the proof to server.receive_vote, which handles
         token validation, ZKP verification, and vote recording
    """
    @staticmethod
    def submit_vote(circuit, server, voter_token, candidate_id):

        candidate_id = int(candidate_id)
        voter_token = (voter_token or "").strip()

        if not voter_token:
            return False, "Enter your voter token."

        # Generate hash of voter token (public parameter)
        voter_token_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        print(f"[CLIENT] Voter token hash: {voter_token_hash[:16]}...")
        
        # Generate ZKP proof
        try:
            print("[CLIENT] Generating zero-knowledge proof...")
            proof_data = circuit.generate_vote_proof(
                voter_token, 
                candidate_id, 
                voter_token_hash
            )
            print("[CLIENT] Proof generated successfully")
            print(f"[CLIENT] Proof size: {len(proof_data)} bytes")
        except Exception as e:
            return False, f"Proof generation failed: {str(e)}"
        try:
            # Securely transmit to server (in production, use HTTPS/TLS)
            print("\n[CLIENT] Securely transmitting proof to server...")
            success, message = server.receive_vote(voter_token_hash, proof_data, candidate_id)
            
            if success:
                print(f"[CLIENT] ✓ Vote submitted successfully: {message}")
            else:
                print(f"[CLIENT] ✗ Vote submission failed: {message}")
            
            return success, message
            
        except Exception as e:
            print(f"[CLIENT] Error during vote submission: {str(e)}")
            return False, str(e)