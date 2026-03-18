import sqlite3
import hashlib
import secrets
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
                voter_token_hash TEXT UNIQUE NOT NULL,
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
                candidate TEXT NOT NULL,
                vote_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_verified BOOLEAN DEFAULT 0
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_eligible_voter(self, voter_identifier):
        """A function to add eligible voter, preserved for admin use ONLY!"""
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        
        # Create a unique hash and token for the voter that contain they personal information provided by the admin
        # Hash value used to prevent double registration of the same voter with the same ID
        voter_hash = hashlib.sha256(voter_identifier.encode()).hexdigest()
        # This part is the secret token provided to the voter in order to cast their votes
        voter_token = secrets.token_urlsafe(32)
        # This is the part we store in order to verify the validity of the token
        voter_token_hash = hashlib.sha256(voter_token.encode()).hexdigest()
        
        try:
            cursor.execute('''
                INSERT INTO eligible_voters (voter_hash, voter_token_hash)
                VALUES (?, ?)
            ''', (voter_hash, voter_token_hash))
            
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
            
            conn.commit()
            return candidate_id
        except sqlite3.IntegrityError:
            print(f"Candidate {name} already exists")
            return None
        finally:
            conn.close()
    
    def verify_voter_token(self, voter_token_hash):
        """Verify if voter token is valid and the voter did not vote before in this election"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT voter_id, has_voted, is_active 
                FROM eligible_voters 
                WHERE voter_token_hash = ?
            ''', (voter_token_hash,))
            
            result = cursor.fetchone()
        except Exception as e:
            return False, str(e)
        finally:
            conn.close()
        
        if not result:
            return False, "Invalid voter token"
        
        voter_id, has_voted, is_active = result
        
        if not is_active:
            return False, "Voter account is inactive"
        
        if has_voted:
            return False, "Voter has already voted (double voting prevented)"
        
        return True, voter_id
    
    def record_vote(self, voter_token_hash, proof_data, public_candidate_input):
        conn = sqlite3.connect(self.db_name)
        cursor = conn.cursor()
        try:
            cursor.execute('''
                INSERT INTO votes (voter_token_hash, proof_data, candidate, is_verified)
                VALUES (?, ?, ?, 1)
            ''', (voter_token_hash, proof_data, public_candidate_input))

            cursor.execute('''
                UPDATE eligible_voters SET has_voted = 1 WHERE voter_token_hash = ?
            ''', (voter_token_hash,))

            conn.commit()
            return True, "Vote recorded successfully"
        except sqlite3.IntegrityError:
            conn.rollback()
            return False, "Double voting detected"
        except Exception as e:
            conn.rollback()
            return False, str(e)
        finally:
            conn.close()

    def tally_votes(self):
        """Tally all verified votes"""
        try:
            conn = sqlite3.connect(self.db_name)
            cursor = conn.cursor()
            
            cursor.execute('''
                SELECT c.candidate_id, c.candidate_name, COUNT(v.vote_id) as votes
                FROM candidates c
                LEFT JOIN votes v ON c.candidate_id = CAST(v.candidate AS INTEGER)
                    AND v.is_verified = 1 
                GROUP BY c.candidate_id, c.candidate_name 
            ''')
            
            results = cursor.fetchall()
            return results
        except Exception as e:
            print(f"[DB] Tally error: {e}")
            return []
        finally:
            conn.close()
        
        
