from database import VotingDatabase
from zkp_circuit import VotingCircuit
import hashlib
import json

"""
Server-side:
1. Manages voter registration (admin only)
2. Receives and verifies proofs from clients
3. Records votes
4. Tallies results
"""

class VotingServer:
    def __init__(self):
        self.db = VotingDatabase()
        self.circuit = VotingCircuit()
    
    def setup_election(self):
        """Initialize election with 3 candidates"""
        print("[SERVER] Setting up election with 3 candidates...")
        
        self.db.add_candidate("Candidate A", "First candidate")
        self.db.add_candidate("Candidate B", "Second candidate")
        self.db.add_candidate("Candidate C", "Third candidate")
        
        print("[SERVER] Election setup complete!")
    
    def admin_register_voter(self, voter_identifier):
        """
        Admin function to register eligible voter
        Returns secure token that voter uses to vote
        """
        print(f"\n[ADMIN] Registering voter: {voter_identifier}")
        token = self.db.add_eligible_voter(voter_identifier)
        
        if token:
            print(f"[ADMIN] Voter registered. Secure token: {token}")
            print("[ADMIN] Give this token to the voter privately")
            return token
        return None
    
    def receive_vote(self, voter_token, proof_data, public_inputs):
        """
        Receive vote from client with ZKP proof
        This function:
        1. Verifies voter token is valid
        2. Checks for double voting
        3. Verifies ZKP proof
        4. Records vote if all checks pass
        """
        print("[SERVER] Receiving vote submission...")
        
        # Step 1: Verify voter token and check double voting
        is_valid, result = self.db.verify_voter_token(voter_token)
        
        if not is_valid:
            print(f"[SERVER] Vote rejected: {result}")
            return False, result
        
        voter_id = result
        print(f"[SERVER] Voter token validated (Voter ID: {voter_id})")
        
        # Step 2: Verify ZKP proof
        voter_token_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        proof_valid, verification_msg = self.circuit.verify_vote_proof(proof_data)  # original call passed 3 args (proof_data, public_inputs, voter_token_hash) but verify_vote_proof in zkp_circuit.py only accepts proof_data
        
        if not proof_valid:
            print(f"[SERVER] Proof verification failed: {verification_msg}")
            return False, verification_msg
        
        print("[SERVER] ZKP proof verified successfully")
        
        # Step 3: Record vote
        success, message = self.db.record_vote(voter_token, proof_data, public_inputs)
        
        if success:
            print(f"[SERVER] Vote recorded: {message}")
        else:
            print(f"[SERVER] Vote recording failed: {message}")
        
        return success, message
    
    def tally_votes_and_display(self):
        """
        Tally all verified votes and display results
        """
        print("\n" + "="*50)
        print("TALLYING VOTES")
        print("="*50)
        
        results = self.db.tally_votes()
        
        print("\nFinal Election Results:")
        print("-" * 50)
        
        total_votes = sum(count for _, _, count in results)
        
        for candidate_id, candidate_name, vote_count in results:
            percentage = (vote_count / total_votes * 100) if total_votes > 0 else 0
            print(f"{candidate_name}: {vote_count} votes ({percentage:.1f}%)")
        
        print("-" * 50)
        print(f"Total votes cast: {total_votes}")
        
        return results

    def get_results(self):
        """Get current election results"""
        return self.db.get_election_results()
