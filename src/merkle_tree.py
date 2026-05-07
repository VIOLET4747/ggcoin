from typing import List, Optional
from .crypto import sha256


class MerkleTree:
    """
    默克尔树（Merkle Tree）实现。
    
    默克尔树是一种二叉树结构，用于高效验证数据完整性：
    1. 叶子节点是数据块的哈希值
    2. 非叶子节点是其子节点哈希的组合哈希
    3. 根节点称为默克尔根，代表整个数据集的哈希
    
    主要用途：
    - 区块链中验证区块内交易的完整性
    - 快速验证某笔交易是否存在于区块中
    """
    
    def __init__(self, data: List[str] = None):
        """
        初始化默克尔树。
        
        参数:
            data: 数据列表，每个元素是一个字符串（将被哈希）
        """
        self.leaves: List[str] = []  # 叶子节点（数据的哈希）
        self.tree: List[List[str]] = []  # 完整的树结构（每层的节点）
        self.root: str = ""  # 默克尔根
        
        if data:
            self.build(data)
    
    def build(self, data: List[str]) -> None:
        """
        构建默克尔树。
        
        参数:
            data: 数据列表
        """
        if not data:
            self.root = sha256("")
            return
        
        # 计算所有叶子节点的哈希
        self.leaves = [sha256(item) for item in data]
        
        # 构建树的每一层
        self.tree = [self.leaves[:]]
        
        current_level = self.leaves[:]
        
        # 从叶子向上构建树
        while len(current_level) > 1:
            next_level = []
            
            # 如果当前层节点数为奇数，复制最后一个节点
            if len(current_level) % 2 != 0:
                current_level.append(current_level[-1])
            
            # 两两组合计算哈希
            for i in range(0, len(current_level), 2):
                combined = current_level[i] + current_level[i + 1]
                next_level.append(sha256(combined))
            
            self.tree.append(next_level)
            current_level = next_level
        
        # 树根是最后一层的唯一节点
        self.root = current_level[0] if current_level else sha256("")
    
    def get_root(self) -> str:
        """
        获取默克尔根。
        
        返回:
            默克尔根哈希值
        """
        return self.root
    
    def get_proof(self, index: int) -> List[dict]:
        """
        获取指定索引数据的默克尔证明。
        
        默克尔证明用于验证某条数据是否存在于默克尔树中，
        它包含从叶子节点到根节点路径上所有兄弟节点的哈希值。
        
        参数:
            index: 数据在原始列表中的索引
        
        返回:
            默克尔证明列表，每个元素包含兄弟节点哈希和位置（左或右）
        """
        if index < 0 or index >= len(self.leaves):
            return []
        
        proof = []
        current_index = index
        
        # 从叶子层向上遍历到根
        for level in range(len(self.tree) - 1):
            level_nodes = self.tree[level]
            
            # 如果当前节点数为奇数且是最后一个节点，使用自身作为兄弟
            if len(level_nodes) % 2 != 0 and current_index == len(level_nodes) - 1:
                sibling_index = current_index
            elif current_index % 2 == 0:
                sibling_index = current_index + 1
                position = "right"
            else:
                sibling_index = current_index - 1
                position = "left"
            
            # 如果兄弟节点存在，添加到证明中
            if sibling_index < len(level_nodes):
                proof.append({
                    "hash": level_nodes[sibling_index],
                    "position": position
                })
            
            # 计算上一层的索引
            current_index = current_index // 2
        
        return proof
    
    def verify_proof(self, data: str, proof: List[dict], root: str) -> bool:
        """
        验证默克尔证明。
        
        参数:
            data: 原始数据
            proof: 默克尔证明
            root: 默克尔根
        
        返回:
            如果证明有效返回 True，否则返回 False
        """
        # 计算数据的哈希
        current_hash = sha256(data)
        
        # 沿着证明路径向上计算
        for step in proof:
            if step["position"] == "left":
                current_hash = sha256(step["hash"] + current_hash)
            else:
                current_hash = sha256(current_hash + step["hash"])
        
        # 验证最终计算结果是否等于根哈希
        return current_hash == root
    
    def get_tree_structure(self) -> List[List[str]]:
        """
        获取完整的树结构。
        
        返回:
            每层节点的列表
        """
        return self.tree
    
    def __len__(self) -> int:
        """返回叶子节点数量"""
        return len(self.leaves)
    
    def __repr__(self) -> str:
        return f"MerkleTree(leaves={len(self.leaves)}, root={self.root[:8]}...)"


def calculate_merkle_root(data: List[str]) -> str:
    """
    计算数据列表的默克尔根（便捷函数）。
    
    参数:
        data: 数据列表
    
    返回:
        默克尔根哈希值
    """
    tree = MerkleTree(data)
    return tree.get_root()
