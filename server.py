from database import VotingDatabase
from zkp_circuit import VotingCircuit

class VotingServer:
    def __init__(self):
        self.db = VotingDatabase()
        VotingCircuit._setup_circuit()

    def setup_election(self):
        print("[SERVER] Setting up election with 3 candidates...")
        self.db.add_candidate("Candidate A", "First candidate")
        self.db.add_candidate("Candidate B", "Second candidate")
        self.db.add_candidate("Candidate C", "Third candidate")
        print("[SERVER] Election setup complete!\n")

    def admin_register_voter(self, voter_identifier):
        print(f"[ADMIN] Registering voter: {voter_identifier}")
        token = self.db.add_eligible_voter(voter_identifier)
        if token:
            print(f"[ADMIN] Voter registered. Secure token: {token}")
            print("[ADMIN] Give this token to the voter privately\n")
            return token
        return None

    def receive_vote(self, voter_token_hash, proof_data, public_candidate_input):
        """
        Receive vote from client with ZKP proof
        This function:
        1. Verifies voter token is valid
        2. Checks for double voting
        3. Verifies ZKP proof
        4. Records vote if all checks pass
        """
        print("[SERVER] Receiving vote submission...")
        
        # Verify voter token and check double voting
        is_valid, result = self.db.verify_voter_token(voter_token_hash)
        
        if not is_valid:
            print(f"[SERVER] Vote rejected: {result}")
            return False, result
        
        voter_id = result
        print(f"[SERVER] Voter token validated (Voter ID: {voter_id})")
        
        # Verify ZKP proof
        proof_valid, verification_msg = VotingCircuit.verify_vote_proof(proof_data) 
        
        if not proof_valid:
            print(f"[SERVER] Proof verification failed: {verification_msg}")
            return False, verification_msg
        
        print("[SERVER] ZKP proof verified successfully")
        
        # Record vote
        success, message = self.db.record_vote(voter_token_hash, proof_data, public_candidate_input)
        
        if success:
            print(f"[SERVER] Vote recorded: {message}")
        else:
            print(f"[SERVER] Vote recording failed: {message}")
        
        return success, message

    def tally_votes(self):
        return self.db.tally_votes()