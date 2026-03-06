import sqlite3
import hashlib
import secrets
from datetime import datetime

class VotingDatabase:
    def __init__(self, db_name='zkp_voting_system.db'):
        self.db_name = db_name
        self.init_database()
    
    def init_database(self):
        """Initialize database with required tables"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Table 1: Eligible Voters
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS eligible_voters (
                voter_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_hash TEXT UNIQUE NOT NULL,
                voter_token TEXT UNIQUE NOT NULL,
                registration_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                has_voted BOOLEAN DEFAULT 0,
                is_active BOOLEAN DEFAULT 1
            )
        ''')
        
        # Table 2: Candidates
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS candidates (
                candidate_id INTEGER PRIMARY KEY AUTOINCREMENT,
                candidate_name TEXT UNIQUE NOT NULL,
                description TEXT
            )
        ''')
        
        # Table 3: Votes (stores only zkp data and public knowledge)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS votes (
                vote_id INTEGER PRIMARY KEY AUTOINCREMENT,
                voter_token_hash TEXT UNIQUE NOT NULL,
                proof_data TEXT NOT NULL,
                public_inputs TEXT NOT NULL,
                vote_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0
            )
        ''')
        
        # Table 4: Vote Tally (Reference the candidates table)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS vote_tally (
                candidate_id INTEGER PRIMARY KEY,
                vote_count INTEGER DEFAULT 0,
                FOREIGN KEY (candidate_id) REFERENCES candidates(candidate_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_eligible_voter(self, voter_identifier):
        """A function to add eligible voter, preserved for admin use ONLY!"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create a unique hash and token for the voter that contain they personal information provided by the admin
        # This essentially hides the personal information in a non reversible value (HASH)
        voter_hash = hashlib.sha256(voter_identifier.encode()).hexdigest()
        # This part is the secret token provided to the voter in order to cast their votes
        voter_token = secrets.token_urlsafe(32)
        
        try:
            cursor.execute('''
                INSERT INTO eligible_voters (voter_hash, voter_token)
                VALUES (?, ?)
            ''', (voter_hash, voter_token))
            
            conn.commit()
            print(f"[DB] Voter added successfully. Token: {voter_token}")
            return voter_token
        except sqlite3.IntegrityError:
            print("Voter already exists")
            return None
        finally:
            conn.close()
    
    def add_candidate(self, name, description=""):
        """Add candidate to election"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        try:
            cursor.execute('''
                INSERT INTO candidates (candidate_name, description)
                VALUES (?, ?)
            ''', (name, description))
            
            candidate_id = cursor.lastrowid
            
            cursor.execute('''
                INSERT INTO vote_tally (candidate_id, vote_count)
                VALUES (?, 0)
            ''', (candidate_id,))
            
            conn.commit()
            return candidate_id
        except sqlite3.IntegrityError:
            print(f"Candidate {name} already exists")
            return None
        finally:
            conn.close()
    
    def verify_voter_token(self, voter_token):
        """Verify if voter token is valid and the voter did not vote before in this election"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT voter_id, has_voted, is_active 
            FROM eligible_voters 
            WHERE voter_token = ?
        ''', (voter_token,))
        
        result = cursor.fetchone()
        conn.close()
        
        if not result:
            return False, "Invalid voter token"
        
        voter_id, has_voted, is_active = result
        
        if not is_active:
            return False, "Voter account is inactive"
        
        if has_voted:
            return False, "Voter has already voted (double voting prevented)"
        
        return True, voter_id
    
    def record_vote(self, voter_token, proof_data, public_inputs):
        """Record a vote with the voter proof and token"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Hash the voter token for privacy
        token_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        
        try:
            # Check double voting attempt
            cursor.execute('''
                SELECT vote_id FROM votes WHERE voter_token_hash = ?
            ''', (token_hash,))
            
            # If row exists, prevent double voting.
            if cursor.fetchone():
                conn.close()
                return False, "Double voting detected"
            
            # Record vote
            cursor.execute('''
                INSERT INTO votes (voter_token_hash, proof_data, public_inputs, is_verified)
                VALUES (?, ?, ?, ?)
            ''', (token_hash, proof_data, public_inputs, 1))
            
            # Mark voter as voted
            cursor.execute('''
                UPDATE eligible_voters 
                SET has_voted = 1 
                WHERE voter_token = ?
            ''', (voter_token,))
            
            conn.commit()
            conn.close()
            return True, "Vote recorded successfully"
        except Exception as e:
            conn.close()
            return False, str(e)
    
    def tally_votes(self):
        """Tally all verified votes"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.candidate_id, c.candidate_name, COUNT(v.vote_id) as votes
            FROM candidates c
            LEFT JOIN votes v ON c.candidate_id = CAST(v.public_inputs AS INTEGER)
            WHERE v.is_verified = 1 OR v.is_verified IS NULL
            GROUP BY c.candidate_id, c.candidate_name
        ''')
        
        results = cursor.fetchall()
        
        # Update tally table
        for candidate_id, _, vote_count in results:
            cursor.execute('''
                UPDATE vote_tally 
                SET vote_count = ? 
                WHERE candidate_id = ?
            ''', (vote_count, candidate_id))
        
        conn.commit()
        conn.close()
        
        return results
    
    def get_election_results(self):
        """Get final election results"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT c.candidate_name, vt.vote_count
            FROM candidates c
            JOIN vote_tally vt ON c.candidate_id = vt.candidate_id
            ORDER BY vt.vote_count DESC
        ''')
        
        results = cursor.fetchall()
        conn.close()
        return results
