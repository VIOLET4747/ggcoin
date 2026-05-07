import time
from typing import Optional, Tuple
from .block import Block, Blockchain
from .crypto import sha256


class ProofOfWork:
    """
    工作量证明（Proof of Work, PoW）算法实现。
    
    PoW 是区块链的核心共识机制，通过算力竞争来维护网络安全：
    1. 矿工通过不断尝试不同的 nonce 值来找到满足难度目标的哈希
    2. 找到有效哈希的过程称为"挖矿"
    3. 难度目标通过哈希值的前导零数量来定义
    """
    
    def __init__(self, difficulty: int = 4):
        """
        初始化 PoW 算法。
        
        参数:
            difficulty: 难度目标，表示哈希值需要的前导零数量（默认 4）
        """
        self.difficulty = difficulty
        # 目标前缀：难度为 N 时，目标哈希必须以 N 个 '0' 开头
        self.target_prefix = '0' * difficulty
    
    def set_difficulty(self, difficulty: int) -> None:
        """
        设置新的难度目标。
        
        参数:
            difficulty: 新的难度值（前导零数量）
        """
        self.difficulty = difficulty
        self.target_prefix = '0' * difficulty
    
    def get_difficulty(self) -> int:
        """
        获取当前难度目标。
        
        返回:
            当前难度值
        """
        return self.difficulty
    
    def is_valid_hash(self, block_hash: str) -> bool:
        """
        验证哈希是否满足当前难度目标。
        
        参数:
            block_hash: 待验证的区块哈希值
        
        返回:
            如果哈希满足难度目标返回 True，否则返回 False
        """
        return block_hash.startswith(self.target_prefix)
    
    def mine_block(self, blockchain: Blockchain, transactions: list = None) -> Optional[Block]:
        """
        挖矿函数：找到满足难度目标的区块。
        
        挖矿过程：
        1. 获取区块链最新区块
        2. 创建新的候选区块
        3. 不断调整 nonce 值，直到找到满足难度目标的哈希
        
        参数:
            blockchain: 区块链实例
            transactions: 待打包的交易列表（可选，默认为区块链的待处理交易）
        
        返回:
            成功挖到的区块，如果失败返回 None
        """
        if transactions is None:
            transactions = blockchain.get_pending_transactions()
        
        if not transactions:
            print("[WARNING] 没有待处理交易，无法挖矿")
            return None
        
        latest_block = blockchain.get_latest_block()
        new_index = latest_block.index + 1
        
        # 初始化 nonce 为 0
        nonce = 0
        start_time = time.time()
        attempts = 0
        
        print(f"[INFO] 开始挖矿 - 区块 #{new_index}, 难度: {self.difficulty}, 交易数: {len(transactions)}")
        
        while True:
            # 创建候选区块
            candidate_block = Block(
                index=new_index,
                timestamp=time.time(),
                transactions=transactions,
                prev_hash=latest_block.hash,
                nonce=nonce
            )
            
            # 计算区块哈希
            block_hash = candidate_block.calculate_hash()
            attempts += 1
            
            # 检查是否满足难度目标
            if self.is_valid_hash(block_hash):
                elapsed_time = time.time() - start_time
                print(f"[SUCCESS] 挖矿成功! 区块 #{new_index}")
                print(f"          哈希: {block_hash}")
                print(f"          Nonce: {nonce}")
                print(f"          尝试次数: {attempts}")
                print(f"          耗时: {elapsed_time:.2f}秒")
                
                # 更新区块的哈希值（因为创建时计算的哈希可能不同）
                candidate_block.hash = block_hash
                return candidate_block
            
            # 增加 nonce 继续尝试
            nonce += 1
            
            # 每 100000 次尝试输出进度信息
            if attempts % 100000 == 0:
                print(f"[PROGRESS] 尝试次数: {attempts:,}, 当前 nonce: {nonce:,}, 当前哈希: {block_hash}")
    
    def validate_proof(self, block: Block) -> bool:
        """
        验证区块的工作量证明是否有效。
        
        参数:
            block: 待验证的区块
            
        返回:
            如果 PoW 有效返回 True，否则返回 False
        """
        # 验证区块哈希是否满足难度目标
        if not self.is_valid_hash(block.hash):
            return False
        
        # 验证区块哈希是否正确计算
        calculated_hash = block.calculate_hash()
        if calculated_hash != block.hash:
            return False
        
        return True


class DifficultyAdjuster:
    """
    难度调整器：根据网络算力动态调整挖矿难度。
    
    参考比特币的难度调整机制：
    - 目标区块生成时间：10 分钟
    - 每 2016 个区块调整一次难度
    - 如果区块生成太快，增加难度；如果太慢，降低难度
    """
    
    def __init__(
        self,
        target_block_time: int = 600,  # 目标区块生成时间（秒），默认 10 分钟
        adjustment_interval: int = 2016  # 调整间隔（区块数），默认 2016 个区块
    ):
        """
        初始化难度调整器。
        
        参数:
            target_block_time: 目标区块生成时间（秒）
            adjustment_interval: 难度调整间隔（区块数）
        """
        self.target_block_time = target_block_time
        self.adjustment_interval = adjustment_interval
    
    def calculate_new_difficulty(
        self,
        blockchain: Blockchain,
        current_difficulty: int
    ) -> Tuple[int, bool]:
        """
        计算新的难度值。
        
        参数:
            blockchain: 区块链实例
            current_difficulty: 当前难度值
        
        返回:
            (新难度值, 是否需要调整)
        """
        chain_length = len(blockchain.chain)
        
        # 只有在达到调整间隔时才进行调整
        if chain_length % self.adjustment_interval != 0:
            return current_difficulty, False
        
        # 获取最近调整间隔内的区块
        start_block_index = chain_length - self.adjustment_interval
        if start_block_index < 0:
            return current_difficulty, False
        
        # 计算实际区块生成时间
        start_block = blockchain.chain[start_block_index]
        end_block = blockchain.chain[-1]
        actual_time = end_block.timestamp - start_block.timestamp
        
        # 计算目标时间
        target_time = self.target_block_time * self.adjustment_interval
        
        print(f"[INFO] 难度调整: 实际时间 {actual_time:.2f}秒, 目标时间 {target_time}秒")
        
        # 根据实际时间与目标时间的比例调整难度
        # 如果实际时间 < 目标时间的一半，增加难度
        # 如果实际时间 > 目标时间的两倍，降低难度
        if actual_time < target_time / 2:
            new_difficulty = current_difficulty + 1
            print(f"[INFO] 区块生成太快，难度增加: {current_difficulty} -> {new_difficulty}")
            return new_difficulty, True
        
        elif actual_time > target_time * 2:
            new_difficulty = max(1, current_difficulty - 1)
            print(f"[INFO] 区块生成太慢，难度降低: {current_difficulty} -> {new_difficulty}")
            return new_difficulty, True
        
        else:
            return current_difficulty, False
