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

MockPointG1 = MagicMock(side_effect=lambda x, y: (x, y))
MockPointG2 = MagicMock(side_effect=lambda x0, x1, y0, y1: ((x0, x1), (y0, y1)))

mock_ecc = MagicMock()
mock_ecc.ec_bn254.PointG1 = MockPointG1
mock_ecc.ec_bn254.PointG2 = MockPointG2

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
    "zksnake.ecc":             mock_ecc,
    "zksnake.ecc.ec_bn254":    mock_ecc.ec_bn254,
})


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
VALID_TOKEN = "secret_voter_token"
VALID_TOKEN_HASH = hashlib.sha256(VALID_TOKEN.encode()).hexdigest()


def _restore_mock_defaults():
    mock_groth16_instance.side_effect = None
    mock_groth16_instance.prove.side_effect = None
    mock_r1cs_instance.solve.side_effect = None
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

    MockGroth16.return_value = mock_groth16_instance
    MockR1CS.return_value = mock_r1cs_instance

    mock_groth16_instance.reset_mock(return_value=False, side_effect=False)
    mock_r1cs_instance.reset_mock(return_value=False, side_effect=False)
    MockPointG1.reset_mock(return_value=False, side_effect=False)
    MockPointG2.reset_mock(return_value=False, side_effect=False)

    _restore_mock_defaults()

    MockPointG1.side_effect = lambda x, y: (x, y)
    MockPointG2.side_effect = lambda x0, x1, y0, y1: ((x0, x1), (y0, y1))

    with patch("zkp_circuit.Groth16",            MockGroth16), \
         patch("zkp_circuit.Proof",              MockProof), \
         patch("zkp_circuit.R1CS",               MockR1CS), \
         patch("zkp_circuit.ConstraintSystem",   MockConstraintSystem), \
         patch("zkp_circuit.BN254_SCALAR_FIELD", FAKE_FIELD), \
         patch("zkp_circuit.PointG1",            MockPointG1), \
         patch("zkp_circuit.PointG2",            MockPointG2):
        VotingCircuit._setup_circuit()  # ← pre-warm while patches are active
        yield


# ===========================================================================
# Tests
# ===========================================================================

def test_setup_circuit():
    """Circuit initializes r1cs and proof system correctly"""
    VotingCircuit._setup_circuit()
    assert VotingCircuit._r1cs is mock_r1cs_instance
    assert VotingCircuit._proof_system is mock_groth16_instance

def test_generate_proof_valid():
    """Valid token and candidate produce a well-formed proof JSON"""
    data = json.loads(
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
    )
    assert data["proof_type"] == "zksnake_groth16"
    assert set(data["proof"].keys()) == {"A", "B", "C"}
    assert all(isinstance(p, str) for p in data["public_inputs"])


def test_generate_proof_invalid_token():
    with pytest.raises(ValueError, match="Invalid voter token"):
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, "bad_hash")


def test_generate_proof_invalid_candidate():
    with pytest.raises(ValueError, match="Invalid candidate ID"):
        VotingCircuit.generate_vote_proof(VALID_TOKEN, 0, VALID_TOKEN_HASH)


def test_verify_valid_proof():
    """Full roundtrip: generate then verify succeeds"""
    proof_json = VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
    ok, msg = VotingCircuit.verify_vote_proof(proof_json)
    assert ok is True
    assert msg == "Proof verified"

def test_verify_wrong_proof_type():
    bad = json.dumps({
        "proof_type": "other_system",
        "proof": {"A": [1, 2], "B": [[1, 2], [3, 4]], "C": [5, 6]},
        "public_inputs": ["0"],
    })
    ok, msg = VotingCircuit.verify_vote_proof(bad)
    assert ok is False
    assert "Wrong proof format" in msg


def test_verify_invalid_json():
    ok, msg = VotingCircuit.verify_vote_proof("not-json{{{")
    assert ok is False
    assert "Verification error" in msg

def test_debug_setup():
    print("MockR1CS:", MockR1CS)
    print("MockR1CS.return_value:", MockR1CS.return_value)
    VotingCircuit._setup_circuit()
    print("_r1cs after setup:", VotingCircuit._r1cs)
    print("_proof_system after setup:", VotingCircuit._proof_system)
    assert VotingCircuit._r1cs is not None

def test_verify_failed_proof():
    proof_json = VotingCircuit.generate_vote_proof(VALID_TOKEN, 1, VALID_TOKEN_HASH)
    mock_groth16_instance.verify.return_value = False 
    ok, msg = VotingCircuit.verify_vote_proof(proof_json)
    assert ok is False
    assert "failed" in msg

def test_debug_setup():
    print("MockR1CS:", MockR1CS)
    print("MockR1CS.return_value:", MockR1CS.return_value)
    VotingCircuit._setup_circuit()
    print("_r1cs after setup:", VotingCircuit._r1cs)
    print("_proof_system after setup:", VotingCircuit._proof_system)
    assert VotingCircuit._r1cs is not None
