import sqlite3
import pandas as pd
import streamlit as st

from client import VotingClient
from server import VotingServer


DB_NAME = "zkp_voting_system.db"

@st.cache_resource
def get_server():
    return VotingServer()

@st.cache_resource
def get_client():
    return VotingClient(server=get_server())

server = get_server()
client = get_client()


# ----------------------------
# Helpers
# ----------------------------
def fetch_df(query, params=None):
    conn = sqlite3.connect(DB_NAME)
    try:
        df = pd.read_sql_query(query, conn, params=params or ())
    finally:
        conn.close()
    return df


def safe_refresh_tally():
    try:
        server.db.tally_votes()
    except Exception:
        pass


def init_session_state():
    defaults = {
        "step": 1,
        "voter_token": "",
        "last_candidate_id": None,
        "last_candidate_name": "",
        "last_proof": "",
        "server_message": "",
        "admin_last_token": "",
        "admin_last_message": "",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


def candidate_options():
    df = fetch_df("""
        SELECT candidate_id, candidate_name
        FROM candidates
        ORDER BY candidate_id
    """)
    if df.empty:
        return []
    return [(int(row["candidate_id"]), str(row["candidate_name"])) for _, row in df.iterrows()]


def reset_voter_flow():
    for key in [
        "step",
        "voter_token",
        "last_candidate_id",
        "last_candidate_name",
        "last_proof",
        "server_message",
    ]:
        if key in st.session_state:
            del st.session_state[key]
    init_session_state()


# ----------------------------
# Admin side
# ----------------------------
def admin_side():
    st.header("Admin Side")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Election Setup")
        if st.button("Load / Initialize Election", use_container_width=True):
            try:
                server.setup_election()
                safe_refresh_tally()
                st.session_state.admin_last_message = "Election initialized."
                st.success("Election initialized.")
            except Exception as e:
                st.session_state.admin_last_message = str(e)
                st.error(str(e))

    with col2:
        st.subheader("Voter Registration")
        voter_identifier = st.text_input(
            "Register voter by name, email, or ID",
            key="admin_voter_identifier",
        )

        if st.button("Register Voter", use_container_width=True):
            if not voter_identifier.strip():
                st.error("Enter a voter identifier.")
            else:
                try:
                    token = server.admin_register_voter(voter_identifier.strip())
                    if token:
                        st.session_state.admin_last_token = token
                        st.success("Voter registered successfully.")
                    else:
                        st.error("Voter already exists or registration failed.")
                except Exception as e:
                    st.error(str(e))

    if st.session_state.get("admin_last_token"):
        st.info(f"Latest voter token: {st.session_state.admin_last_token}")

    st.divider()

    col3, col4 = st.columns([1, 1])
    with col3:
        if st.button("Refresh Database View", use_container_width=True):
            safe_refresh_tally()
            st.rerun()
    with col4:
        if st.button("Refresh Results Only", use_container_width=True):
            safe_refresh_tally()
            st.rerun()

    safe_refresh_tally()

    st.subheader("Election Results")
    results_df = fetch_df("""
        SELECT c.candidate_id, c.candidate_name, vt.vote_count
        FROM candidates c
        LEFT JOIN vote_tally vt ON c.candidate_id = vt.candidate_id
        ORDER BY c.candidate_id
    """)
    st.dataframe(results_df, use_container_width=True, hide_index=True)

    st.subheader("Candidates Table")
    candidates_df = fetch_df("""
        SELECT candidate_id, candidate_name, description
        FROM candidates
        ORDER BY candidate_id
    """)
    st.dataframe(candidates_df, use_container_width=True, hide_index=True)

    st.subheader("Eligible Voters Table")
    voters_df = fetch_df("""
        SELECT voter_id, voter_hash, voter_token, registration_date, has_voted, is_active
        FROM eligible_voters
        ORDER BY voter_id
    """)
    st.dataframe(voters_df, use_container_width=True, hide_index=True)

    st.subheader("Votes Table")
    votes_df = fetch_df("""
        SELECT vote_id, voter_token_hash, public_inputs, vote_timestamp, is_verified
        FROM votes
        ORDER BY vote_id
    """)
    st.dataframe(votes_df, use_container_width=True, hide_index=True)

    st.subheader("Vote Tally Table")
    tally_df = fetch_df("""
        SELECT vt.candidate_id, c.candidate_name, vt.vote_count
        FROM vote_tally vt
        JOIN candidates c ON c.candidate_id = vt.candidate_id
        ORDER BY vt.candidate_id
    """)
    st.dataframe(tally_df, use_container_width=True, hide_index=True)

    st.subheader("Quick Status Checks")

    if not voters_df.empty:
        voted_count = int((voters_df["has_voted"] == 1).sum())
        active_count = int((voters_df["is_active"] == 1).sum())
        total_voters = len(voters_df)

        c1, c2, c3 = st.columns(3)
        c1.metric("Registered Voters", total_voters)
        c2.metric("Already Voted", voted_count)
        c3.metric("Active Voters", active_count)

    if not votes_df.empty and not voters_df.empty:
        st.caption(
            "If a voter has has_voted = 1 and only one row appears for that token hash in votes, "
            "the double-voting protection is working."
        )


# ----------------------------
# Voter ballot
# ----------------------------
def voter_ballot():
    st.header("Voter Ballot")

    options = candidate_options()

    if not options:
        st.warning("No candidates found. Go to the Admin Side and load the election first.")
        return

    label_map = {cid: name for cid, name in options}

    if st.session_state.step == 1:
        st.subheader("Step 1: Enter your voter token")
        token_input = st.text_input("Voter token", type="password", value=st.session_state.voter_token)

        if st.button("Continue", use_container_width=True):
            if not token_input.strip():
                st.error("Enter your voter token.")
                return

            st.session_state.voter_token = token_input.strip()
            st.session_state.step = 2
            st.rerun()

    elif st.session_state.step == 2:
        st.subheader("Step 2: Select one candidate")

        candidate_ids = [cid for cid, _ in options]
        selected_id = st.radio(
            "Candidates",
            options=candidate_ids,
            format_func=lambda cid: label_map[cid],
        )

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Back", use_container_width=True):
                st.session_state.step = 1
                st.rerun()

        with col2:
            if st.button("Review", use_container_width=True):
                st.session_state.last_candidate_id = int(selected_id)
                st.session_state.last_candidate_name = label_map[int(selected_id)]
                st.session_state.step = 3
                st.rerun()

    elif st.session_state.step == 3:
        st.subheader("Step 3: Confirm your vote")
        st.write(f"You selected: **{st.session_state.last_candidate_name}**")

        col1, col2 = st.columns(2)

        with col1:
            if st.button("Go Back", use_container_width=True):
                st.session_state.step = 2
                st.rerun()

        with col2:
            if st.button("Confirm Vote", use_container_width=True):
                success, message, vote_package = client.submit_vote(
                    voter_token=st.session_state.voter_token,
                    candidate_id=st.session_state.last_candidate_id,
                )

                st.session_state.server_message = message
                st.session_state.last_proof = (
                    vote_package["proof_data"] if vote_package else ""
                )

                if success:
                    safe_refresh_tally()
                    st.session_state.step = 4
                    st.rerun()
                else:
                    st.error(message)

    else:
        st.success(st.session_state.server_message or "Vote submitted successfully.")
        st.caption("Your vote has been recorded anonymously.")

        if st.session_state.get("last_proof"):
            st.subheader("Proof")
            st.code(st.session_state.last_proof, language="json")

        if st.button("Start Over", use_container_width=True):
            reset_voter_flow()
            st.rerun()


# ----------------------------
# App shell
# ----------------------------
st.set_page_config(page_title="ZK Voting Demo", layout="wide")
init_session_state()

st.title("ZK Vote Demo")

mode = st.sidebar.radio("View", ["Admin Side", "Voter Ballot"], index=0)

if mode == "Admin Side":
    admin_side()
else:
    voter_ballot()
