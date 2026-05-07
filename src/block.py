import time
from typing import List, Optional
from .crypto import sha256


class Block:
    """
    区块类，代表区块链中的一个区块。
    
    区块是区块链的基本单元，包含区块头和交易数据。
    区块头包含用于验证区块完整性和链接到前一个区块的关键信息。
    """
    
    def __init__(
        self,
        index: int,
        timestamp: float,
        transactions: List[dict],
        prev_hash: str = "",
        nonce: int = 0,
        merkle_root: str = ""
    ):
        """
        初始化区块对象。
        
        参数:
            index: 区块在链中的位置（高度）
            timestamp: 区块创建的时间戳（Unix 时间）
            transactions: 区块中包含的交易列表
            prev_hash: 前一个区块的哈希值
            nonce: 工作量证明的随机数
            merkle_root: 交易的默克尔树根哈希
        """
        self.index = index
        self.timestamp = timestamp
        self.transactions = transactions
        self.prev_hash = prev_hash
        self.nonce = nonce
        self.merkle_root = merkle_root if merkle_root else self.calculate_merkle_root()
        self.hash = self.calculate_hash()
    
    def calculate_hash(self) -> str:
        """
        计算区块的哈希值。
        
        区块哈希是通过对区块头（index, timestamp, prev_hash, nonce, merkle_root）
        进行 SHA-256 哈希计算得到的。这个哈希值唯一标识一个区块。
        
        返回:
            64 位十六进制字符串表示的区块哈希
        """
        # 构建区块头数据
        block_header = {
            "index": self.index,
            "timestamp": self.timestamp,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root
        }
        return sha256(block_header)
    
    def calculate_merkle_root(self) -> str:
        """
        计算交易的默克尔树根哈希。
        
        默克尔树是一种二叉树结构，用于高效验证交易完整性。
        叶子节点是交易哈希，非叶子节点是其子节点哈希的组合哈希。
        
        返回:
            默克尔树根哈希值
        """
        if not self.transactions:
            return sha256("")
        
        # 获取所有交易的哈希值作为叶子节点
        transaction_hashes = [sha256(tx) for tx in self.transactions]
        
        # 如果交易数量为奇数，复制最后一个交易哈希
        if len(transaction_hashes) % 2 != 0:
            transaction_hashes.append(transaction_hashes[-1])
        
        # 递归构建默克尔树
        while len(transaction_hashes) > 1:
            new_level = []
            for i in range(0, len(transaction_hashes), 2):
                combined = transaction_hashes[i] + transaction_hashes[i + 1]
                new_level.append(sha256(combined))
            transaction_hashes = new_level
        
        return transaction_hashes[0]
    
    def to_dict(self) -> dict:
        """
        将区块转换为字典格式，便于序列化和网络传输。
        
        返回:
            包含区块所有字段的字典
        """
        return {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": self.transactions,
            "prev_hash": self.prev_hash,
            "nonce": self.nonce,
            "merkle_root": self.merkle_root,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Block':
        """
        从字典创建区块对象。
        
        参数:
            data: 包含区块字段的字典
        
        返回:
            Block 实例
        """
        block = cls(
            index=data["index"],
            timestamp=data["timestamp"],
            transactions=data["transactions"],
            prev_hash=data["prev_hash"],
            nonce=data["nonce"],
            merkle_root=data["merkle_root"]
        )
        # 直接设置哈希值，避免重新计算
        block.hash = data["hash"]
        return block
    
    def __repr__(self) -> str:
        """
        返回区块的字符串表示，便于调试和日志输出。
        """
        return f"Block(index={self.index}, hash={self.hash[:16]}..., prev_hash={self.prev_hash[:16]}..., nonce={self.nonce})"


class Blockchain:
    """
    区块链类，管理整个区块链的数据结构。
    
    区块链是一个由区块组成的链表，每个区块通过 prev_hash 字段链接到前一个区块。
    整个链从创世区块开始。
    """
    
    def __init__(self):
        """
        初始化区块链，创建创世区块。
        """
        self.chain: List[Block] = []
        self.pending_transactions: List[dict] = []
        self.create_genesis_block()
    
    def create_genesis_block(self) -> None:
        """
        创建创世区块（Genesis Block）。
        
        创世区块是区块链的第一个区块，没有前一个区块（prev_hash 为空）。
        它是整个区块链的起点，通常包含一些初始交易或元数据。
        """
        # 创世区块的特殊标识
        genesis_transaction = {
            "type": "genesis",
            "message": "Welcome to Mini-Blockchain - Genesis Block"
        }
        
        genesis_block = Block(
            index=0,
            timestamp=time.time(),
            transactions=[genesis_transaction],
            prev_hash="",
            nonce=0
        )
        
        self.chain.append(genesis_block)
        print(f"[INFO] 创世区块已创建: {genesis_block.hash}")
    
    def get_latest_block(self) -> Block:
        """
        获取区块链中的最后一个区块。
        
        返回:
            最新的区块对象
        """
        return self.chain[-1]
    
    def add_block(self, block: Block) -> bool:
        """
        添加一个新区块到区块链。
        
        在添加前会验证区块的有效性：
        1. 区块索引是否正确（比最新区块索引大 1）
        2. 前一个区块哈希是否匹配
        3. 区块自身哈希是否有效
        
        参数:
            block: 要添加的区块对象
        
        返回:
            如果添加成功返回 True，否则返回 False
        """
        latest_block = self.get_latest_block()
        
        # 验证区块索引
        if block.index != latest_block.index + 1:
            print(f"[ERROR] 区块索引无效: 期望 {latest_block.index + 1}, 实际 {block.index}")
            return False
        
        # 验证前一个区块哈希
        if block.prev_hash != latest_block.hash:
            print(f"[ERROR] 前一个区块哈希不匹配: 期望 {latest_block.hash}, 实际 {block.prev_hash}")
            return False
        
        # 验证区块哈希
        if block.hash != block.calculate_hash():
            print(f"[ERROR] 区块哈希无效")
            return False
        
        self.chain.append(block)
        print(f"[INFO] 区块 #{block.index} 已添加到链: {block.hash}")
        return True
    
    def is_chain_valid(self) -> bool:
        """
        验证整个区块链的完整性和正确性。
        
        检查每个区块：
        1. 区块自身哈希是否正确
        2. 前一个区块哈希链接是否正确
        3. 默克尔根是否与交易列表匹配
        
        返回:
            如果链有效返回 True，否则返回 False
        """
        for i in range(len(self.chain)):
            current_block = self.chain[i]
            
            # 验证默克尔根是否与当前交易匹配
            recalculated_merkle_root = current_block.calculate_merkle_root()
            if current_block.merkle_root != recalculated_merkle_root:
                print(f"[ERROR] 区块 #{i} 默克尔根无效")
                return False
            
            # 验证当前区块哈希
            if current_block.hash != current_block.calculate_hash():
                print(f"[ERROR] 区块 #{i} 哈希无效")
                return False
            
            # 验证前一个区块哈希链接（跳过创世区块）
            if i > 0:
                previous_block = self.chain[i - 1]
                if current_block.prev_hash != previous_block.hash:
                    print(f"[ERROR] 区块 #{i} 前哈希链接无效")
                    return False
        
        print("[INFO] 区块链验证通过，所有区块有效")
        return True
    
    def add_pending_transaction(self, transaction: dict) -> None:
        """
        添加待处理交易到交易池。
        
        参数:
            transaction: 交易字典
        """
        self.pending_transactions.append(transaction)
        print(f"[INFO] 交易已添加到待处理池")
    
    def get_pending_transactions(self) -> List[dict]:
        """
        获取所有待处理交易。
        
        返回:
            待处理交易列表
        """
        return self.pending_transactions
    
    def clear_pending_transactions(self) -> None:
        """
        清空待处理交易池（通常在区块打包后调用）。
        """
        self.pending_transactions = []
    
    def to_dict(self) -> List[dict]:
        """
        将整个区块链转换为字典列表，便于序列化和网络传输。
        
        返回:
            包含所有区块字典的列表
        """
        return [block.to_dict() for block in self.chain]
    
    def __len__(self) -> int:
        """
        返回区块链的长度（区块数量）。
        """
        return len(self.chain)
    
    def __repr__(self) -> str:
        """
        返回区块链的字符串表示。
        """
        return f"Blockchain(length={len(self.chain)}, latest_block={self.get_latest_block().hash[:16]}...)"
