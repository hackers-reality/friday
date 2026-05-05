"""
Friday Blockchain - Blockchain and cryptocurrency.
Implements blockchain, smart contracts, and crypto operations.
"""
from __future__ import annotations__

import hashlib
import json
import time
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime
from pathlib import Path


# ─── Block ─────────────────────────────────#

class Block:
    """A block in the blockchain."""
    
    def __init__(
        self,
        index: int,
        timestamp: float,
        data: Any,
        previous_hash: str,
        nonce: int = 0,
    ):
        self.index = index
        self.timestamp = timestamp
        self.data = data
        self.previous_hash = previous_hash
        self.nonce = nonce
        self.hash = self.calculate_hash()
        
    def calculate_hash(self) -> str:
        """Calculate SHA-256 hash of block."""
        block_string = json.dumps({
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
        }, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()
    
    def mine(self, difficulty: int = 4):
        """Mine block (proof-of-work)."""
        target = "0" * difficulty
        while self.hash[:difficulty] != target:
            self.nonce += 1
            self.hash = self.calculate_hash()
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "data": self.data,
            "previous_hash": self.previous_hash,
            "nonce": self.nonce,
            "hash": self.hash,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Block':
        block = cls(
            data["index"],
            data["timestamp"],
            data["data"],
            data["previous_hash"],
            data["nonce"],
        )
        block.hash = data["hash"]
        return block


# ─── Blockchain ─────────────────────────────────#

class Blockchain:
    """A simple blockchain implementation."""
    
    def __init__(self, difficulty: int = 4):
        self.chain: List[Block] = []
        self.difficulty = difficulty
        self.pending_transactions: List[Dict] = []
        self._create_genesis_block()
        
    def _create_genesis_block(self):
        """Create the first block."""
        genesis = Block(0, time.time(), "Genesis Block", "0")
        genesis.mine(self.difficulty)
        self.chain.append(genesis)
        
    def get_latest_block(self) -> Block:
        """Get the latest block."""
        return self.chain[-1]
    
    def add_transaction(self, sender: str, recipient: str, amount: float) -> int:
        """Add a transaction to pending pool."""
        transaction = {
            "sender": sender,
            "recipient": recipient,
            "amount": amount,
            "timestamp": time.time(),
        }
        self.pending_transactions.append(transaction)
        return len(self.chain) + 1  # Next block index
    
    def mine_pending_transactions(self, miner_address: str) -> Block:
        """Mine all pending transactions into a new block."""
        # Add mining reward
        self.pending_transactions.append({
            "sender": "network",
            "recipient": miner_address,
            "amount": 1.0,  # Block reward
            "timestamp": time.time(),
        })
        
        # Create new block
        new_block = Block(
            len(self.chain),
            time.time(),
            self.pending_transactions,
            self.get_latest_block().hash,
        )
        new_block.mine(self.difficulty)
        
        self.chain.append(new_block)
        self.pending_transactions = []
        
        return new_block
    
    def is_valid(self) -> bool:
        """Check if blockchain is valid."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            previous = self.chain[i-1]
            
            # Check hash
            if current.hash != current.calculate_hash():
                return False
            
            # Check previous hash link
            if current.previous_hash != previous.hash:
                return False
        
        return True
    
    def get_balance(self, address: str) -> float:
        """Calculate balance for an address."""
        balance = 0.0
        
        for block in self.chain:
            if isinstance(block.data, list):  # Transactions
                for tx in block.data:
                    if tx["sender"] == address:
                        balance -= tx["amount"]
                    if tx["recipient"] == address:
                        balance += tx["amount"]
        
        return balance
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "chain": [b.to_dict() for b in self.chain],
            "pending_transactions": self.pending_transactions,
            "difficulty": self.difficulty,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Blockchain':
        blockchain = cls(difficulty=data.get("difficulty", 4))
        blockchain.chain = []
        for block_data in data.get("chain", []):
            blockchain.chain.append(Block.from_dict(block_data))
        blockchain.pending_transactions = data.get("pending_transactions", [])
        return blockchain
    
    def save(self, path: str):
        """Save blockchain to file."""
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(self.to_dict(), f, indent=2)
    
    @classmethod
    def load(cls, path: str) -> 'Blockchain':
        """Load blockchain from file."""
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return cls.from_dict(data)


# ─── Smart Contract ─────────────────────────────────#

class SmartContract:
    """A simple smart contract."""
    
    def __init__(self, owner: str, code: str):
        self.owner = owner
        self.code = code  # In reality, this would be bytecode
        self.state: Dict[str, Any] = {}
        self.balance: float = 0.0
        
    def execute(self, caller: str, function: str, args: List[Any]) -> Dict[str, Any]:
        """Execute a function on the contract."""
        # Simplified: just check if caller is owner for now
        if caller != self.owner:
            return {"error": "Unauthorized"}
        
        # Simplified execution
        if function == "deposit":
            amount = args[0] if args else 0.0
            self.balance += amount
            return {"success": True, "balance": self.balance}
        
        elif function == "withdraw":
            amount = args[0] if args else 0.0
            if amount > self.balance:
                return {"error": "Insufficient balance"}
            self.balance -= amount
            return {"success": True, "balance": self.balance}
        
        elif function == "get_balance":
            return {"success": True, "balance": self.balance}
        
        return {"error": f"Unknown function: {function}"}
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "owner": self.owner,
            "code": self.code,
            "state": self.state,
            "balance": self.balance,
        }


# ─── Cryptocurrency Wallet ─────────────────────────────────#

class Wallet:
    """A simple cryptocurrency wallet."""
    
    def __init__(self, address: str = None):
        self.address = address or self._generate_address()
        self.private_key = hashlib.sha256(self.address.encode()).hexdigest()
        
    def _generate_address(self) -> str:
        """Generate a random address."""
        import random
        random_part = ''.join(random.choices('0123456789abcdef', k=40))
        return f"1{random_part}"
    
    def sign_transaction(self, transaction: Dict) -> str:
        """Sign a transaction (simplified)."""
        tx_string = json.dumps(transaction, sort_keys=True)
        return hashlib.sha256(
            (tx_string + self.private_key).encode()
        ).hexdigest()
    
    def get_address(self) -> str:
        return self.address


# ─── Singleton Blockchain ─────────────────────────────────#

_blockchain: Optional[Blockchain] = None
_wallets: Dict[str, Wallet] = {}

def get_blockchain() -> Blockchain:
    """Get or create the global blockchain."""
    global _blockchain
    if _blockchain is None:
        _blockchain = Blockchain()
    return _blockchain

def get_wallet(address: str = None) -> Wallet:
    """Get or create a wallet."""
    global _wallets
    if address and address in _wallets:
        return _wallets[address]
    
    wallet = Wallet(address)
    _wallets[wallet.get_address()] = wallet
    return wallet


# ─── Tool Function for Friday ─────────────────────────────────#

def blockchain_tool(
    action: str = "status",
    from_addr: str = None,
    to_addr: str = None,
    amount: float = 0.0,
    miner: str = None,
    address: str = None,
) -> str:
    """
    Friday tool for blockchain operations.
    Actions: status, transaction, mine, balance, wallets, create_wallet
    """
    if action == "status":
        chain = get_blockchain()
        lines = ["### BLOCKCHAIN STATUS", ""]
        lines.append(f"**Blocks**: {len(chain.chain)}")
        lines.append(f"**Difficulty**: {chain.difficulty}")
        lines.append(f"**Valid**: {'✅' if chain.is_valid() else '❌'}")
        lines.append(f"**Pending Transactions**: {len(chain.pending_transactions)}")
        return "\n".join(lines)
    
    if action == "transaction":
        if not from_addr or not to_addr or amount <= 0:
            return "❌ Provide from_addr, to_addr, and amount > 0."
        
        chain = get_blockchain()
        index = chain.add_transaction(from_addr, to_addr, amount)
        return f"✅ Transaction added to block {index} (pending mining)"
    
    if action == "mine":
        if not miner:
            return "❌ Miner address required."
        
        chain = get_blockchain()
        block = chain.mine_pending_transactions(miner)
        return f"✅ Block {block.index} mined! Hash: {block.hash[:16]}..."
    
    if action == "balance":
        if not address:
            return "❌ Address required."
        
        chain = get_blockchain()
        balance = chain.get_balance(address)
        return f"Balance for {address[:16]}...: {balance:.2f}"
    
    if action == "wallets":
        lines = ["### WALLETS", ""]
        for addr, wallet in _wallets.items():
            lines.append(f"- {addr[:20]}...")
        return "\n".join(lines) if _wallets else "No wallets created."
    
    if action == "create_wallet":
        wallet = get_wallet()
        return f"✅ Wallet created: {wallet.get_address()[:20]}..."
    
    return f"Unknown action: {action}"


if __name__ == "__main__":
    print("Testing Blockchain...\n")
    
    # Create blockchain
    chain = get_blockchain()
    print("--- Blockchain Created ---")
    print(blockchain_tool("status"))
    
    # Create wallets
    alice = get_wallet("Alice123")
    bob = get_wallet("Bob456")
    print(f"\n--- Wallets ---")
    print(f"Alice: {alice.get_address()[:20]}...")
    print(f"Bob: {bob.get_address()[:20]}...")
    
    # Add transactions
    print("\n--- Transactions ---")
    print(blockchain_tool("transaction", from_addr="Alice123", to_addr="Bob456", amount=10.0))
    
    # Mine
    print("\n--- Mining ---")
    print(blockchain_tool("mine", miner="Alice123"))
    
    # Check balance
    print("\n--- Balances ---")
    print(blockchain_tool("balance", address="Alice123"))
    print(blockchain_tool("balance", address="Bob456"))
