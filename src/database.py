import sqlite3
import json
import threading
from typing import List, Dict, Optional
from pathlib import Path

class Database:
    def __init__(self, db_path: str = "ggcoin.db"):
        self.db_path = db_path
        self.lock = threading.Lock()
        self._init_db()
    
    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn
    
    def _init_db(self):
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS blocks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    index_num INTEGER NOT NULL UNIQUE,
                    hash TEXT NOT NULL UNIQUE,
                    prev_hash TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    nonce INTEGER NOT NULL,
                    merkle_root TEXT NOT NULL,
                    transactions TEXT NOT NULL
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS wallets (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    address TEXT NOT NULL UNIQUE,
                    public_key TEXT NOT NULL,
                    private_key TEXT NOT NULL,
                    balance REAL DEFAULT 0
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS utxos (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txid TEXT NOT NULL,
                    vout INTEGER NOT NULL,
                    value REAL NOT NULL,
                    script_pubkey TEXT NOT NULL,
                    spent INTEGER DEFAULT 0,
                    UNIQUE(txid, vout)
                )
            """)
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    txid TEXT NOT NULL UNIQUE,
                    tx_data TEXT NOT NULL,
                    status TEXT DEFAULT 'pending'
                )
            """)
            
            conn.commit()
            conn.close()
    
    def save_block(self, block_data: Dict) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT INTO blocks 
                    (index_num, hash, prev_hash, timestamp, nonce, merkle_root, transactions)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    block_data['index'],
                    block_data['hash'],
                    block_data['prev_hash'],
                    block_data['timestamp'],
                    block_data['nonce'],
                    block_data['merkle_root'],
                    json.dumps(block_data['transactions'])
                ))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error saving block: {e}")
                return False
    
    def load_blocks(self) -> List[Dict]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM blocks ORDER BY index_num")
            rows = cursor.fetchall()
            
            blocks = []
            for row in rows:
                blocks.append({
                    'index': row['index_num'],
                    'hash': row['hash'],
                    'prev_hash': row['prev_hash'],
                    'timestamp': row['timestamp'],
                    'nonce': row['nonce'],
                    'merkle_root': row['merkle_root'],
                    'transactions': json.loads(row['transactions'])
                })
            
            conn.close()
            return blocks
    
    def save_wallet(self, name: str, address: str, public_key: str, private_key: str, balance: float = 0) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO wallets 
                    (name, address, public_key, private_key, balance)
                    VALUES (?, ?, ?, ?, ?)
                """, (name, address, public_key, private_key, balance))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error saving wallet: {e}")
                return False
    
    def load_wallets(self) -> List[Dict]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM wallets")
            rows = cursor.fetchall()
            
            wallets = []
            for row in rows:
                wallets.append({
                    'name': row['name'],
                    'address': row['address'],
                    'public_key': row['public_key'],
                    'private_key': row['private_key'],
                    'balance': row['balance']
                })
            
            conn.close()
            return wallets
    
    def update_wallet_balance(self, address: str, balance: float) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE wallets SET balance = ? WHERE address = ?
                """, (balance, address))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error updating wallet balance: {e}")
                return False
    
    def save_utxo(self, txid: str, vout: int, value: float, script_pubkey: str) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO utxos 
                    (txid, vout, value, script_pubkey, spent)
                    VALUES (?, ?, ?, ?, 0)
                """, (txid, vout, value, script_pubkey))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error saving UTXO: {e}")
                return False
    
    def mark_utxo_spent(self, txid: str, vout: int) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE utxos SET spent = 1 WHERE txid = ? AND vout = ?
                """, (txid, vout))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error marking UTXO spent: {e}")
                return False
    
    def load_utxos(self) -> List[Dict]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM utxos WHERE spent = 0")
            rows = cursor.fetchall()
            
            utxos = []
            for row in rows:
                utxos.append({
                    'txid': row['txid'],
                    'vout': row['vout'],
                    'value': row['value'],
                    'script_pubkey': row['script_pubkey']
                })
            
            conn.close()
            return utxos
    
    def get_utxos_for_address(self, address: str) -> List[Dict]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM utxos 
                WHERE script_pubkey = ? AND spent = 0
            """, (address,))
            
            rows = cursor.fetchall()
            
            utxos = []
            for row in rows:
                utxos.append({
                    'txid': row['txid'],
                    'vout': row['vout'],
                    'value': row['value'],
                    'script_pubkey': row['script_pubkey']
                })
            
            conn.close()
            return utxos
    
    def save_transaction(self, txid: str, tx_data: Dict, status: str = 'pending') -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    INSERT OR REPLACE INTO transactions 
                    (txid, tx_data, status)
                    VALUES (?, ?, ?)
                """, (txid, json.dumps(tx_data), status))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error saving transaction: {e}")
                return False
    
    def load_pending_transactions(self) -> List[Dict]:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT * FROM transactions WHERE status = 'pending'")
            rows = cursor.fetchall()
            
            transactions = []
            for row in rows:
                tx_data = json.loads(row['tx_data'])
                transactions.append(tx_data)
            
            conn.close()
            return transactions
    
    def update_transaction_status(self, txid: str, status: str) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("""
                    UPDATE transactions SET status = ? WHERE txid = ?
                """, (status, txid))
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error updating transaction status: {e}")
                return False
    
    def clear_pending_transactions(self) -> bool:
        with self.lock:
            try:
                conn = self._get_connection()
                cursor = conn.cursor()
                
                cursor.execute("DELETE FROM transactions WHERE status = 'pending'")
                
                conn.commit()
                conn.close()
                return True
            except Exception as e:
                print(f"Error clearing pending transactions: {e}")
                return False
    
    def get_block_count(self) -> int:
        with self.lock:
            conn = self._get_connection()
            cursor = conn.cursor()
            
            cursor.execute("SELECT COUNT(*) as count FROM blocks")
            result = cursor.fetchone()
            
            conn.close()
            return result['count'] if result else 0
