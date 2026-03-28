# 🗳️ Overview : voting_system_zkp

A privacy-preserving voting system built on the **zk-SNARK** (Zero-Knowledge Succinct Non-Interactive Argument of Knowledge) protocol, demonstrating Zero-Knowledge Proofs (ZKP) using a real-world use case.

---

## 📐 Design Overview

This system enables verifiable, anonymous voting through the following guarantees:
- **Privacy**: A voter's choice is never revealed to the server — only a
  cryptographic proof of a valid vote is transmitted.
- **Integrity**: Double voting is prevented at the database level via hashed
  token tracking.
- **Verifiability**: Every recorded vote carries a zk-SNARK proof that can be
  independently verified.

> **⚠️ Disclaimer:** This implementation runs all components in-process with no
> network communication. For any real-world deployment, **all channels must be
> encrypted** — client↔server via HTTPS/TLS, and server↔database via encrypted
> connections or a secured local socket. Admin token distribution must also
> occur over a private, out-of-band channel.

---

## Architecture

The system is composed of five modules:

| Module             | File               | Responsibility                                              |
|--------------------|--------------------|-------------------------------------------------------------|
| Frontend / App     | `app.py`           | Streamlit UI for voters and admins                          |
| Server             | `server.py`        | Voter registration, proof verification, vote recording      |
| Client             | `client.py`        | ZKP proof generation and secure transmission                |
| Database           | `database.py`      | SQLite persistence for voters, candidates, and votes        |
| ZKP Circuit        | `zkp_circuit.py`   | Groth16 zk-SNARK circuit setup, proving, and verification   |

---

## 🚀 Getting Started

# How to Run Our Code

## 1. Create a virtual environment (recommended)

```bash
python -m venv venv
```
## 2. Activate it
#### For Windows:
```bash
venv\Scripts\activate
```
#### For Mac/Linux:
```bash
venv\bin\activate
```
## 3. Intsall virtual env requirements
```bash
pip intsall -r requirements.txt
```
## 4. Run (streamlit)
```bash
python -m streamlit run app.py
```


