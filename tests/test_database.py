# ===========================================================================
# Tests generated using automation and reviewed manually.
# ===========================================================================

import pytest
import os
import hashlib
from database import VotingDatabase


@pytest.fixture
def db(tmp_path):
    """Create a fresh in-memory DB for each test."""
    db_file = str(tmp_path / "test_voting.db")
    instance = VotingDatabase(db_name=db_file)
    return instance


# --- Voter Registration ---

def test_add_voter_returns_token(db):
    token = db.add_eligible_voter("voter_001")
    assert token is not None
    assert len(token) > 0


def test_duplicate_voter_returns_none(db):
    db.add_eligible_voter("voter_001")
    duplicate = db.add_eligible_voter("voter_001")
    assert duplicate is None


# --- Token Verification ---

def test_valid_token_is_verified(db):
    token = db.add_eligible_voter("voter_002")
    voter_token_hash = hashlib.sha256(token.encode()).hexdigest()
    valid, result = db.verify_voter_token(voter_token_hash)
    assert valid is True
    assert isinstance(result, int)  # returns voter_id


def test_invalid_token_rejected(db):
    valid, msg = db.verify_voter_token("totally_fake_token")
    assert valid is False
    assert "Invalid" in msg


# --- Double Voting Prevention ---

def test_double_vote_prevented(db):
    token = db.add_eligible_voter("voter_003")
    voter_token_hash = hashlib.sha256(token.encode()).hexdigest()
    db.add_candidate("Alice")

    db.record_vote(voter_token_hash, proof_data="proof_xyz", public_candidate_input="1")
    success, msg = db.record_vote(voter_token_hash, proof_data="proof_xyz", public_candidate_input="1")
    assert success is False
    assert "double" in msg.lower() or "Double" in msg


def test_voter_marked_as_voted(db):
    token = db.add_eligible_voter("voter_004")
    voter_token_hash = hashlib.sha256(token.encode()).hexdigest()
    db.add_candidate("Bob")
    db.record_vote(voter_token_hash, proof_data="proof_abc", public_candidate_input="1")

    valid, msg = db.verify_voter_token(voter_token_hash)
    assert valid is False
    assert "already voted" in msg.lower()


# --- Candidate Management ---

def test_add_candidate_returns_id(db):
    candidate_id = db.add_candidate("Alice", "Party A")
    assert candidate_id is not None
    assert candidate_id > 0


def test_duplicate_candidate_returns_none(db):
    db.add_candidate("Alice")
    duplicate_id = db.add_candidate("Alice")
    assert duplicate_id is None


# --- Vote Tally ---

def test_tally_counts_votes_correctly(db):
    token1 = db.add_eligible_voter("voter_005")
    token2 = db.add_eligible_voter("voter_006")
    candidate_id = db.add_candidate("Charlie")

    db.record_vote(token1, "proof1", str(candidate_id))
    db.record_vote(token2, "proof2", str(candidate_id))

    results = db.tally_votes()
    vote_counts = {name: count for _, name, count in results}
    assert vote_counts["Charlie"] == 2
