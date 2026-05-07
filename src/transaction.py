import hashlib
import json
from typing import List, Optional
from ecdsa import SigningKey, VerifyingKey, SECP256k1
from .crypto import sha256


class TxInput:
    """
    交易输入类，表示对之前交易输出的引用。
    
    在 UTXO 模型中，交易输入必须引用一个未花费的交易输出（UTXO）。
    输入包含：
    - 引用的交易哈希（txid）
    - 该交易中的输出索引（vout）
    - 解锁脚本（signature）- 用于证明拥有该输出的所有权
    """
    
    def __init__(self, txid: str, vout: int, signature: Optional[str] = None):
        """
        初始化交易输入。
        
        参数:
            txid: 引用的交易哈希
            vout: 该交易中的输出索引（从 0 开始）
            signature: 解锁脚本（签名）
        """
        self.txid = txid
        self.vout = vout
        self.signature = signature
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "txid": self.txid,
            "vout": self.vout,
            "signature": self.signature
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TxInput':
        """从字典创建 TxInput"""
        return cls(
            txid=data["txid"],
            vout=data["vout"],
            signature=data.get("signature")
        )
    
    def __repr__(self) -> str:
        return f"TxInput(txid={self.txid[:8]}..., vout={self.vout})"


class TxOutput:
    """
    交易输出类，表示交易创建的新输出。
    
    输出包含：
    - 金额（value）
    - 锁定脚本（script_pubkey）- 定义谁可以花费这个输出
    """
    
    def __init__(self, value: int, script_pubkey: str):
        """
        初始化交易输出。
        
        参数:
            value: 输出金额（最小单位，类似聪）
            script_pubkey: 锁定脚本，通常是公钥的哈希
        """
        self.value = value
        self.script_pubkey = script_pubkey
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "value": self.value,
            "script_pubkey": self.script_pubkey
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TxOutput':
        """从字典创建 TxOutput"""
        return cls(
            value=data["value"],
            script_pubkey=data["script_pubkey"]
        )
    
    def __repr__(self) -> str:
        return f"TxOutput(value={self.value}, script_pubkey={self.script_pubkey[:8]}...)"


class Transaction:
    """
    交易类，表示区块链中的一笔交易。
    
    交易是区块链的核心，它将未花费的输出（UTXO）转换为新的输出。
    一个交易包含：
    - 输入列表（inputs）：引用之前交易的输出
    - 输出列表（outputs）：创建新的输出
    - 交易哈希（txid）：唯一标识该交易
    """
    
    def __init__(self, inputs: List[TxInput], outputs: List[TxOutput]):
        """
        初始化交易。
        
        参数:
            inputs: 交易输入列表
            outputs: 交易输出列表
        """
        self.inputs = inputs
        self.outputs = outputs
        self.txid = self.calculate_txid()
    
    def calculate_txid(self) -> str:
        """
        计算交易哈希（txid）。
        
        交易哈希是通过对交易的输入和输出数据进行 SHA-256 哈希计算得到的。
        注意：签名前和签名后的 txid 是不同的，这里计算的是签名后的 txid。
        
        返回:
            64 位十六进制字符串表示的交易哈希
        """
        tx_data = {
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs]
        }
        return sha256(tx_data)
    
    def get_transaction_data_for_signing(self) -> str:
        """
        获取用于签名的交易数据。
        
        在签名时，需要排除签名字段本身，只对交易的核心数据进行签名。
        
        返回:
            用于签名的序列化字符串
        """
        tx_data = {
            "inputs": [{"txid": inp.txid, "vout": inp.vout} for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs]
        }
        return json.dumps(tx_data, sort_keys=True, separators=(',', ':'))
    
    def sign(self, private_key: SigningKey, input_index: int) -> None:
        """
        对交易的指定输入进行签名。
        
        参数:
            private_key: 用于签名的私钥
            input_index: 要签名的输入索引
        """
        # 获取用于签名的数据
        data_to_sign = self.get_transaction_data_for_signing()
        data_bytes = data_to_sign.encode('utf-8')
        
        # 使用私钥签名
        signature = private_key.sign(data_bytes)
        
        # 将签名转换为十六进制字符串并保存
        self.inputs[input_index].signature = signature.hex()
    
    def verify_signature(self, input_index: int) -> bool:
        """
        验证交易指定输入的签名是否有效。
        
        参数:
            input_index: 要验证的输入索引
        
        返回:
            如果签名有效返回 True，否则返回 False
        """
        try:
            tx_input = self.inputs[input_index]
            
            if not tx_input.signature:
                return False
            
            # 获取公钥（从输出的 script_pubkey 中提取）
            # 这里简化处理，直接使用 script_pubkey 作为公钥
            public_key_hex = tx_input.script_pubkey if hasattr(tx_input, 'script_pubkey') else None
            
            if not public_key_hex:
                # 从引用的输出中获取公钥（需要 UTXO 集合）
                return False
            
            # 恢复公钥
            public_key = VerifyingKey.from_string(bytes.fromhex(public_key_hex), curve=SECP256k1)
            
            # 获取用于签名的数据
            data_to_sign = self.get_transaction_data_for_signing()
            data_bytes = data_to_sign.encode('utf-8')
            
            # 验证签名
            signature_bytes = bytes.fromhex(tx_input.signature)
            return public_key.verify(signature_bytes, data_bytes)
        
        except Exception as e:
            print(f"[ERROR] 签名验证失败: {e}")
            return False
    
    def is_coinbase(self) -> bool:
        """
        判断是否为 Coinbase 交易（挖矿奖励交易）。
        
        Coinbase 交易是特殊的交易，它没有输入（或者输入的 txid 为空），
        用于奖励矿工。
        
        返回:
            如果是 Coinbase 交易返回 True，否则返回 False
        """
        if len(self.inputs) != 1:
            return False
        
        return self.inputs[0].txid == "" and self.inputs[0].vout == -1
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        return {
            "txid": self.txid,
            "inputs": [inp.to_dict() for inp in self.inputs],
            "outputs": [out.to_dict() for out in self.outputs]
        }
    
    @classmethod
    def from_dict(cls, data: dict) -> 'Transaction':
        """从字典创建 Transaction"""
        inputs = [TxInput.from_dict(inp) for inp in data["inputs"]]
        outputs = [TxOutput.from_dict(out) for out in data["outputs"]]
        tx = cls(inputs, outputs)
        tx.txid = data["txid"]  # 使用已计算的 txid
        return tx
    
    def __repr__(self) -> str:
        return f"Transaction(txid={self.txid[:8]}..., inputs={len(self.inputs)}, outputs={len(self.outputs)})"


class UTXOSet:
    """
    UTXO（未花费交易输出）集合管理类。
    
    UTXO 是区块链的核心数据结构，它追踪所有未被花费的交易输出。
    当一笔交易被处理时：
    - 它消耗的输入会从 UTXO 集合中移除
    - 它创建的输出会添加到 UTXO 集合中
    """
    
    def __init__(self):
        """初始化 UTXO 集合"""
        # 存储格式: {txid: {vout: TxOutput}}
        self.utxos = {}
    
    def add_utxo(self, txid: str, vout: int, output: TxOutput) -> None:
        """
        添加一个新的 UTXO。
        
        参数:
            txid: 交易哈希
            vout: 输出索引
            output: 交易输出对象
        """
        if txid not in self.utxos:
            self.utxos[txid] = {}
        self.utxos[txid][vout] = output
    
    def remove_utxo(self, txid: str, vout: int) -> bool:
        """
        移除一个已花费的 UTXO。
        
        参数:
            txid: 交易哈希
            vout: 输出索引
        
        返回:
            如果成功移除返回 True，否则返回 False
        """
        if txid in self.utxos and vout in self.utxos[txid]:
            del self.utxos[txid][vout]
            # 如果该交易的所有输出都已花费，删除该交易记录
            if not self.utxos[txid]:
                del self.utxos[txid]
            return True
        return False
    
    def get_utxo(self, txid: str, vout: int) -> Optional[TxOutput]:
        """
        获取指定的 UTXO。
        
        参数:
            txid: 交易哈希
            vout: 输出索引
        
        返回:
            如果找到返回 TxOutput，否则返回 None
        """
        return self.utxos.get(txid, {}).get(vout)
    
    def get_balance(self, address: str) -> int:
        """
        获取指定地址的余额。
        
        参数:
            address: 钱包地址（公钥哈希）
        
        返回:
            该地址的总余额
        """
        balance = 0
        for txid, outputs in self.utxos.items():
            for vout, output in outputs.items():
                if output.script_pubkey == address:
                    balance += output.value
        return balance
    
    def get_utxos_for_address(self, address: str) -> List[dict]:
        """
        获取指定地址的所有 UTXO。
        
        参数:
            address: 钱包地址（公钥哈希）
        
        返回:
            UTXO 列表，每个元素包含 txid、vout 和 value
        """
        utxos = []
        for txid, outputs in self.utxos.items():
            for vout, output in outputs.items():
                if output.script_pubkey == address:
                    utxos.append({
                        "txid": txid,
                        "vout": vout,
                        "value": output.value
                    })
        return utxos
    
    def process_transaction(self, tx: Transaction) -> bool:
        """
        处理一笔交易，更新 UTXO 集合。
        
        参数:
            tx: 要处理的交易
        
        返回:
            如果处理成功返回 True，否则返回 False
        """
        # Coinbase 交易不需要验证输入
        if not tx.is_coinbase():
            # 验证并移除所有输入引用的 UTXO
            for tx_input in tx.inputs:
                utxo = self.get_utxo(tx_input.txid, tx_input.vout)
                if not utxo:
                    print(f"[ERROR] UTXO 不存在: {tx_input.txid}:{tx_input.vout}")
                    return False
                
                # 移除已花费的 UTXO
                self.remove_utxo(tx_input.txid, tx_input.vout)
        
        # 添加新创建的输出到 UTXO 集合
        for i, output in enumerate(tx.outputs):
            self.add_utxo(tx.txid, i, output)
        
        return True
    
    def to_dict(self) -> dict:
        """转换为字典格式"""
        result = {}
        for txid, outputs in self.utxos.items():
            result[txid] = {vout: output.to_dict() for vout, output in outputs.items()}
        return result
    
    def from_dict(self, data: dict) -> None:
        """从字典加载 UTXO 集合"""
        self.utxos = {}
        for txid, outputs in data.items():
            self.utxos[txid] = {vout: TxOutput.from_dict(out) for vout, out in outputs.items()}
    
    def __len__(self) -> int:
        """返回 UTXO 的总数"""
        count = 0
        for outputs in self.utxos.values():
            count += len(outputs)
        return count
    
    def __repr__(self) -> str:
        return f"UTXOSet(total_utxos={len(self)})"
