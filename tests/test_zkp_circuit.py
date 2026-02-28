# ===========================================================================
# Tests generated using automation and reviewed manually.
# ===========================================================================

import hashlib
import json
import sys
import pytest
from zkp_circuit import VotingCircuit
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Force-remove real zksnake from sys.modules for testing
# ---------------------------------------------------------------------------
for mod in list(sys.modules):
    if mod.startswith("zksnake"):
        del sys.modules[mod]

# ---------------------------------------------------------------------------
# Build mock zksnake tree
# ---------------------------------------------------------------------------
FAKE_FIELD = 2**254 + 4825374

mock_proof = MagicMock()
mock_proof.A = (111, 222)
mock_proof.B = ((333, 444), (555, 666))
mock_proof.C = (777, 888)

mock_groth16_instance = MagicMock()
mock_groth16_instance.prove.return_value = mock_proof
mock_groth16_instance.verify.return_value = True
mock_groth16_instance.setup.return_value = None

MockGroth16 = MagicMock(return_value=mock_groth16_instance)
MockProof = MagicMock(side_effect=lambda A, B, C: MagicMock(A=A, B=B, C=C))

mock_r1cs_instance = MagicMock()
mock_r1cs_instance.solve.return_value = {"candidate": 1}
mock_r1cs_instance.generate_witness.return_value = (["0"], ["1", "0", "0"])
mock_r1cs_instance.compile.return_value = None

MockR1CS = MagicMock(return_value=mock_r1cs_instance)
MockConstraintSystem = MagicMock()
MockVar = MagicMock(side_effect=lambda name: MagicMock(name=name))

mock_zksnake = MagicMock()
mock_zksnake.groth16.Groth16 = MockGroth16
mock_zksnake.groth16.Proof = MockProof
mock_zksnake.arithmetization.ConstraintSystem = MockConstraintSystem
mock_zksnake.arithmetization.R1CS = MockR1CS
mock_zksnake.arithmetization.Var = MockVar
mock_zksnake.constant.BN254_SCALAR_FIELD = FAKE_FIELD

sys.modules.update({
    "zksnake":                 mock_zksnake,
    "zksnake.groth16":         mock_zksnake.groth16,
    "zksnake.arithmetization": mock_zksnake.arithmetization,
    "zksnake.constant":        mock_zksnake.constant,
})


# ---------------------------------------------------------------------------
# CRITICAL: patch the names as they were imported INTO zkp_circuit's namespace
# ---------------------------------------------------------------------------
patch("zkp_circuit.Groth16", MockGroth16).start()
patch("zkp_circuit.Proof",   MockProof).start()
patch("zkp_circuit.R1CS",    MockR1CS).start()
patch("zkp_circuit.ConstraintSystem", MockConstraintSystem).start()
patch("zkp_circuit.BN254_SCALAR_FIELD", FAKE_FIELD).start()

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_TOKEN = "secret_voter_token"
VALID_TOKEN_HASH = hashlib.sha256(VALID_TOKEN.encode()).hexdigest()


def _restore_mock_defaults():
    # Clear side effects first — critical after exception propagation tests
    mock_groth16_instance.side_effect = None
    mock_groth16_instance.prove.side_effect = None
    mock_r1cs_instance.solve.side_effect = None
    mock_r1cs_instance.compile.side_effect = None

    # Restore return values
    mock_r1cs_instance.solve.return_value = {"candidate": 1}
    mock_r1cs_instance.generate_witness.return_value = (["0"], ["1", "0", "0"])
    mock_r1cs_instance.compile.return_value = None
    mock_groth16_instance.prove.return_value = mock_proof
    mock_groth16_instance.verify.return_value = True
    mock_groth16_instance.setup.return_value = None
    MockGroth16.return_value = mock_groth16_instance
    MockR1CS.return_value = mock_r1cs_instance



@pytest.fixture(autouse=True)
def reset_circuit_state():
    VotingCircuit._proof_system = None
    VotingCircuit._r1cs = None

    MockGroth16.reset_mock(return_value=False, side_effect=False)
    MockR1CS.reset_mock(return_value=False, side_effect=False)
    mock_groth16_instance.reset_mock(return_value=False, side_effect=False)
    mock_r1cs_instance.reset_mock(return_value=False, side_effect=False)

    _restore_mock_defaults()
    yield


def _make_valid_proof_json(candidate_id=1):
    return VotingCircuit.generate_vote_proof(
        VALID_TOKEN, candidate_id, VALID_TOKEN_HASH
    )


# ===========================================================================
# Tests: _setup_circuit
# ===========================================================================

class TestSetupCircuit:
    def test_setup_called_once(self):
        VotingCircuit._setup_circuit()
        assert VotingCircuit._proof_system is mock_groth16_instance
        assert VotingCircuit._r1cs is mock_r1cs_instance

    def test_r1cs_compile_called(self):
        VotingCircuit._setup_circuit()
        mock_r1cs_instance.compile.assert_called_once()

    def test_proof_system_setup_called(self):
        VotingCircuit._setup_circuit()
        mock_groth16_instance.setup.assert_called_once()


# ===========================================================================
# Tests: _serialize_point / _deserialize_point
# ===========================================================================

class TestSerializePoint:
    @pytest.mark.parametrize("point, expected", [
        ((1, 2),           ["1", "2"]),
        ([1, 2],           ["1", "2"]),
        (((1, 2), (3, 4)), [["1", "2"], ["3", "4"]]),
        (42,               "42"),
    ])
    def test_serialize_various_types(self, point, expected):
        assert VotingCircuit._serialize_point(point) == expected

    def test_serialize_object_with_xy(self):
        point_obj = MagicMock()
        point_obj.x = 10
        point_obj.y = 20
        assert VotingCircuit._serialize_point(point_obj) == ["10", "20"]


class TestDeserializePoint:
    def test_deserialize_g1(self):
        assert VotingCircuit._deserialize_point(["111", "222"]) == (111, 222)

    def test_deserialize_g2(self):
        assert VotingCircuit._deserialize_point([["1", "2"], ["3", "4"]]) == ((1, 2), (3, 4))

    def test_deserialize_scalar(self):
        assert VotingCircuit._deserialize_point("99") == 99

    def test_roundtrip_g1(self):
        original = (123, 456)
        assert VotingCircuit._deserialize_point(
            VotingCircuit._serialize_point(original)
        ) == original

    def test_roundtrip_g2(self):
        original = ((10, 20), (30, 40))
        assert VotingCircuit._deserialize_point(
            VotingCircuit._serialize_point(original)
        ) == original


# ===========================================================================
# Tests: generate_vote_proof
# ===========================================================================

class TestGenerateVoteProof:
    @pytest.mark.parametrize("candidate_id", [1, 2, 3])
    def test_valid_candidates_return_json(self, candidate_id):
        data = json.loads(
            VotingCircuit.generate_vote_proof(VALID_TOKEN, candidate_id, VALID_TOKEN_HASH)
        )
        assert data["proof_type"] == "zksnake_groth16"
        assert "proof" in data
        assert "public_inputs" in data

    def test_proof_contains_abc_keys(self):
        data = json.loads(
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
        )
        assert set(data["proof"].keys()) == {"A", "B", "C"}

    def test_public_inputs_are_strings(self):
        data = json.loads(
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
        )
        assert all(isinstance(p, str) for p in data["public_inputs"])

    def test_invalid_token_raises(self):
        with pytest.raises(ValueError, match="Invalid voter token"):
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, "bad_hash")

    def test_invalid_candidate_zero_raises(self):
        with pytest.raises(ValueError, match="Invalid candidate ID"):
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 0, VALID_TOKEN_HASH)

    def test_invalid_candidate_out_of_range_raises(self):
        with pytest.raises(ValueError, match="Invalid candidate ID"):
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 4, VALID_TOKEN_HASH)

    def test_r1cs_solve_called_with_candidate(self):
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 2, VALID_TOKEN_HASH)
        mock_r1cs_instance.solve.assert_called_once_with({"candidate": 2})

    def test_prove_called(self):
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
        mock_groth16_instance.prove.assert_called_once()

    def test_setup_triggered_on_first_call(self):
        assert VotingCircuit._proof_system is None
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
        assert VotingCircuit._proof_system is not None

    def test_proof_generation_propagates_exception(self):
        mock_groth16_instance.prove.side_effect = RuntimeError("prove failed")
        with pytest.raises(RuntimeError, match="prove failed"):
            VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)



# ===========================================================================
# Tests: verify_vote_proof
# ===========================================================================

class TestVerifyVoteProof:
    def test_valid_proof_returns_true(self):
        ok, msg = VotingCircuit.verify_vote_proof(_make_valid_proof_json())
        print(ok)
        print(msg)
        assert ok is True
        assert msg == "Proof verified"

    def test_wrong_proof_type_returns_false(self):
        bad = json.dumps({
            "proof_type": "other_system",
            "proof": {"A": ["1", "2"], "B": [["1", "2"], ["3", "4"]], "C": ["5", "6"]},
            "public_inputs": ["0"],
        })
        ok, msg = VotingCircuit.verify_vote_proof(bad)
        assert ok is False
        assert "Wrong proof format" in msg

    def test_missing_proof_key_returns_false(self):
        bad = json.dumps({"proof_type": "zksnake_groth16", "public_inputs": ["0"]})
        ok, msg = VotingCircuit.verify_vote_proof(bad)
        assert ok is False
        assert "Invalid proof structure" in msg

    def test_missing_public_inputs_returns_false(self):
        bad = json.dumps({
            "proof_type": "zksnake_groth16",
            "proof": {"A": ["1", "2"], "B": [["1", "2"], ["3", "4"]], "C": ["5", "6"]},
        })
        ok, msg = VotingCircuit.verify_vote_proof(bad)
        assert ok is False

    def test_invalid_json_returns_false(self):
        ok, msg = VotingCircuit.verify_vote_proof("not-json{{{")
        assert ok is False
        assert "Verification error" in msg

    def test_failed_verification_returns_false(self):
        proof_json = _make_valid_proof_json()
        mock_groth16_instance.verify.return_value = False
        VotingCircuit._proof_system = None
        VotingCircuit._r1cs = None
        ok, msg = VotingCircuit.verify_vote_proof(proof_json)
        assert ok is False
        assert "failed" in msg

    def test_verify_called_with_reconstructed_proof(self):
        proof_json = _make_valid_proof_json()
        VotingCircuit.verify_vote_proof(proof_json)
        mock_groth16_instance.verify.assert_called_once()

    def test_full_roundtrip_all_candidates(self):
        for candidate_id in [1, 2, 3]:
            VotingCircuit._proof_system = None
            VotingCircuit._r1cs = None
            proof_json = _make_valid_proof_json(candidate_id)
            ok, msg = VotingCircuit.verify_vote_proof(proof_json)
            assert ok is True, f"Failed for candidate {candidate_id}: {msg}"
