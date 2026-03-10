# app.py
import json
import hashlib
import streamlit as st
from zkp_circuit import VotingCircuit

# ----------------------------
# Voter ballot UI
# ----------------------------
def ballot_ui():
    st.header("Secure Voting Portal")

    if "step" not in st.session_state:
        st.session_state.step = 1
    if "last_proof" not in st.session_state:
        st.session_state.last_proof = ""
    if "last_hash" not in st.session_state:
        st.session_state.last_hash = ""
    if "last_candidate" not in st.session_state:
        st.session_state.last_candidate = None

    if st.session_state.step == 1:
        st.subheader("Step 1: Enter your voter token")
        voter_token = st.text_input("Voter token", type="password")

        if st.button("Continue", use_container_width=True):
            if not voter_token.strip():
                st.error("Enter your voter token.")
                return

            token_hash = hashlib.sha256(voter_token.encode("utf-8")).hexdigest()
            st.session_state.voter_token = voter_token
            st.session_state.last_hash = token_hash
            st.session_state.step = 2
            st.rerun()

    elif st.session_state.step == 2:
        st.subheader("Step 2: Select ONE candidate")
        choice = st.radio(
            "Candidates",
            options=[
                ("Candidate 1", 1),
                ("Candidate 2", 2),
                ("Candidate 3", 3),
            ],
            format_func=lambda x: x[0],
        )
        candidate_id = choice[1]

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.step = 1
                st.rerun()
        with col2:
            if st.button("Review", use_container_width=True):
                st.session_state.last_candidate = candidate_id
                st.session_state.step = 3
                st.rerun()

    elif st.session_state.step == 3:
        st.subheader("Step 3: Confirm your vote")
        st.write(f"You selected: **Candidate {st.session_state.last_candidate}**")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Go Back", use_container_width=True):
                st.session_state.step = 2
                st.rerun()

        with col2:
            if st.button("Confirm Vote", use_container_width=True):
                try:
                    proof_json = VotingCircuit.generate_vote_proof(
                        voter_token=st.session_state.voter_token,
                        candidate_id=int(st.session_state.last_candidate),
                        voter_token_hash=st.session_state.last_hash,
                    )
                    st.session_state.last_proof = proof_json
                    st.session_state.step = 4
                    st.rerun()
                except Exception as e:
                    st.error(str(e))

    else:  # step 4
        st.success("Vote submitted successfully.")
        st.caption("Your vote has been recorded anonymously.")
        if st.session_state.get("last_proof"):
            st.subheader("Proof (for demo only)")
            st.code(st.session_state.last_proof, language="json")

        if st.button("Start Over", use_container_width=True):
            for k in ["step", "voter_token", "last_proof", "last_hash", "last_candidate"]:
                if k in st.session_state:
                    del st.session_state[k]
            st.rerun()


# ----------------------------
# Developer / demo panel
# ----------------------------
def developer_panel():
    st.header("Developer Panel (for demo / debugging)")

    voter_token = st.text_input("Voter token", type="password", key="dev_token")
    candidate_id = st.selectbox("Candidate", [1, 2, 3], key="dev_candidate")

    auto_hash = ""
    if voter_token.strip():
        auto_hash = hashlib.sha256(voter_token.encode("utf-8")).hexdigest()

    voter_token_hash = st.text_input(
        "Voter token hash (sha256 hex)",
        value=auto_hash,
        key="dev_hash",
        help="Auto-filled from the token above. You can also paste your own.",
    )

    if st.button("Generate proof", key="dev_gen"):
        try:
            proof_json = VotingCircuit.generate_vote_proof(
                voter_token=voter_token,
                candidate_id=int(candidate_id),
                voter_token_hash=voter_token_hash,
            )
            st.success("Proof generated")
            st.code(proof_json, language="json")
            st.session_state.dev_last_proof = proof_json
        except Exception as e:
            st.error(str(e))


# ----------------------------
# App shell
# ----------------------------
st.set_page_config(page_title="ZK Voting Demo", layout="centered")
st.title("ZK Vote Demo")


mode = st.sidebar.radio("View", ["Developer Panel", "Voter Ballot"], index=0)

if mode == "Developer Panel":
    developer_panel()
else:
    ballot_ui()
