import hashlib

from server import VotingServer
from zkp_circuit import VotingCircuit


class VotingClient:
    """
    Client-side helper.
    Responsibilities:
      1. Generate the ZK proof for the voter's choice
      2. Hand the proof to server.receive_vote, which handles
         token validation, ZKP verification, and vote recording
    """

    def __init__(self, server=None):
        self.server = server if server is not None else VotingServer()

    def submit_vote(self, voter_token, candidate_id):
        voter_token = (voter_token or "").strip()
        candidate_id = int(candidate_id)

        if not voter_token:
            return False, "Enter your voter token.", None

        # Generate ZK proof client-side
        try:
            voter_token_hash = hashlib.sha256(voter_token.encode("utf-8")).hexdigest()
            proof_json = VotingCircuit.generate_vote_proof(
                voter_token=voter_token,
                candidate_id=candidate_id,
                voter_token_hash=voter_token_hash,
            )
        except Exception as e:
            return False, f"Proof generation failed: {str(e)}", None

        # Hand everything to the server — it validates the token,
        # verifies the proof, and records the vote
        success, message = self.server.receive_vote(
            voter_token=voter_token,
            proof_data=proof_json,
            public_inputs=str(candidate_id),
        )

        vote_package = {
            "voter_token": voter_token,
            "candidate_id": candidate_id,
            "proof_data": proof_json,
        }

        return success, message, vote_package
