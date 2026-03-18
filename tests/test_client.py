# ===========================================================================
# Tests generated using automation and reviewed manually.
# ===========================================================================

import hashlib
import pytest
from unittest.mock import MagicMock
from client import VotingClient


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def circuit():
    mock = MagicMock()
    mock.generate_vote_proof.return_value = '{"proof": "mock_proof"}'
    return mock


@pytest.fixture
def server():
    mock = MagicMock()
    mock.receive_vote.return_value = (True, "Vote recorded successfully")
    return mock


VALID_TOKEN = "secret_voter_token"
VALID_TOKEN_HASH = hashlib.sha256(VALID_TOKEN.encode()).hexdigest()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

def test_submit_vote_success(circuit, server):
    ok, msg = VotingClient.submit_vote(circuit, server, VALID_TOKEN, 1)
    assert ok is True
    assert msg == "Vote recorded successfully"


def test_submit_vote_empty_token(circuit, server):
    ok, msg = VotingClient.submit_vote(circuit, server, "", 1)
    assert ok is False
    assert "Enter your voter token" in msg


def test_submit_vote_whitespace_token(circuit, server):
    ok, msg = VotingClient.submit_vote(circuit, server, "   ", 1)
    assert ok is False
    assert "Enter your voter token" in msg


def test_submit_vote_proof_generation_fails(circuit, server):
    circuit.generate_vote_proof.side_effect = ValueError("Invalid candidate ID")
    ok, msg = VotingClient.submit_vote(circuit, server, VALID_TOKEN, 1)
    assert ok is False
    assert "Proof generation failed" in msg


def test_submit_vote_server_rejects(circuit, server):
    server.receive_vote.return_value = (False, "Double voting detected")
    ok, msg = VotingClient.submit_vote(circuit, server, VALID_TOKEN, 1)
    assert ok is False
    assert "Double voting" in msg


def test_submit_vote_passes_correct_hash(circuit, server):
    VotingClient.submit_vote(circuit, server, VALID_TOKEN, 1)
    called_hash = server.receive_vote.call_args[0][0]
    assert called_hash == VALID_TOKEN_HASH


def test_submit_vote_server_raises(circuit, server):
    server.receive_vote.side_effect = Exception("Connection error")
    ok, msg = VotingClient.submit_vote(circuit, server, VALID_TOKEN, 1)
    assert ok is False
    assert "Connection error" in msg
