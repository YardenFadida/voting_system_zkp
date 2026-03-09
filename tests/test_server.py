# ===========================================================================
# Tests generated using automation and reviewed manually.
# ===========================================================================

import pytest
from unittest.mock import MagicMock, patch
from server import VotingServer


@pytest.fixture
def server():
    """Create a VotingServer with mocked dependencies."""
    with patch("server.VotingDatabase") as MockDB, \
         patch("server.VotingCircuit") as MockCircuit:
        s = VotingServer()
        s.db = MockDB.return_value
        s.circuit = MockCircuit.return_value
        yield s


# --- setup_election ---

def test_setup_election_adds_three_candidates(server):
    server.setup_election()
    assert server.db.add_candidate.call_count == 3


def test_setup_election_candidate_names(server):
    server.setup_election()
    calls = [call.args[0] for call in server.db.add_candidate.call_args_list]
    assert calls == ["Candidate A", "Candidate B", "Candidate C"]


# --- admin_register_voter ---

def test_admin_register_voter_returns_token(server):
    server.db.add_eligible_voter.return_value = "secure-token-123"
    token = server.admin_register_voter("voter@example.com")
    assert token == "secure-token-123"


def test_admin_register_voter_returns_none_on_failure(server):
    server.db.add_eligible_voter.return_value = None
    token = server.admin_register_voter("voter@example.com")
    assert token is None


# --- receive_vote ---

def test_receive_vote_rejects_invalid_token(server):
    server.db.verify_voter_token.return_value = (False, "Token not found")
    success, msg = server.receive_vote("bad-token", {}, {})
    assert success is False
    assert "Token not found" in msg


def test_receive_vote_rejects_invalid_zkp_proof(server):
    server.db.verify_voter_token.return_value = (True, "voter-1")
    server.circuit.verify_vote_proof.return_value = (False, "Invalid proof")
    success, msg = server.receive_vote("good-token", {}, {})
    assert success is False
    assert "Invalid proof" in msg


def test_receive_vote_records_valid_vote(server):
    server.db.verify_voter_token.return_value = (True, "voter-1")
    server.circuit.verify_vote_proof.return_value = (True, "Proof valid")
    server.db.record_vote.return_value = (True, "Vote recorded")
    success, msg = server.receive_vote("good-token", {"proof": "abc"}, {"candidate": 1})
    assert success is True
    assert "Vote recorded" in msg


def test_receive_vote_calls_record_vote_with_correct_args(server):
    server.db.verify_voter_token.return_value = (True, "voter-1")
    server.circuit.verify_vote_proof.return_value = (True, "OK")
    server.db.record_vote.return_value = (True, "OK")
    proof = {"proof": "xyz"}
    inputs = {"candidate": 2}
    server.receive_vote("my-token", proof, inputs)
    server.db.record_vote.assert_called_once_with("my-token", proof, inputs)


# --- tally_votes_and_display ---

def test_tally_votes_returns_results(server):
    server.db.tally_votes.return_value = [
        (1, "Candidate A", 5),
        (2, "Candidate B", 3),
        (3, "Candidate C", 2),
    ]
    results = server.tally_votes_and_display()
    assert len(results) == 3


def test_tally_votes_handles_zero_votes(server):
    server.db.tally_votes.return_value = [
        (1, "Candidate A", 0),
        (2, "Candidate B", 0),
    ]
    # Should not raise ZeroDivisionError
    results = server.tally_votes_and_display()
    assert results is not None


# --- get_results ---

def test_get_results_delegates_to_db(server):
    server.db.get_election_results.return_value = {"A": 10, "B": 5}
    results = server.get_results()
    server.db.get_election_results.assert_called_once()
    assert results == {"A": 10, "B": 5}
