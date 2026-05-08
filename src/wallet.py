from ecdsa import SigningKey, VerifyingKey, SECP256k1
from .crypto import sha256


class Wallet:
    """
    钱包类，用于管理公私钥对和签名交易。
    
    区块链钱包的核心功能：
    1. 生成公私钥对
    2. 从私钥恢复公钥
    3. 生成钱包地址（公钥的哈希）
    4. 签名交易
    5. 验证签名
    """
    
    def __init__(self):
        """初始化钱包，生成新的公私钥对"""
        self.private_key = None
        self.public_key = None
        self.address = None
        self.generate_keys()
    
    def generate_keys(self) -> None:
        """
        生成新的 ECDSA 公私钥对。
        
        使用 SECP256k1 椭圆曲线（比特币使用的曲线）。
        私钥是一个 256 位的随机数，公钥是私钥通过椭圆曲线乘法得到的点。
        """
        # 生成私钥（使用 SECP256k1 曲线）
        self.private_key = SigningKey.generate(curve=SECP256k1)
        
        # 从私钥导出公钥
        self.public_key = self.private_key.get_verifying_key()
        
        # 生成钱包地址（公钥的 SHA-256 哈希）
        self.address = self._generate_address()
    
    def _generate_address(self) -> str:
        """
        生成钱包地址。
        
        地址生成过程：
        1. 获取公钥的字节表示
        2. 对其进行 SHA-256 哈希
        3. 返回哈希值作为地址
        
        返回:
            钱包地址（64 位十六进制字符串）
        """
        public_key_bytes = self.public_key.to_string()
        return sha256(public_key_bytes.hex())
    
    def get_private_key_hex(self) -> str:
        """
        获取私钥的十六进制表示。
        
        返回:
            私钥的十六进制字符串
        """
        if isinstance(self.private_key, str):
            return self.private_key
        return self.private_key.to_string().hex()
    
    def get_public_key_hex(self) -> str:
        """
        获取公钥的十六进制表示。
        
        返回:
            公钥的十六进制字符串
        """
        if isinstance(self.public_key, str):
            return self.public_key
        return self.public_key.to_string().hex()
    
    def get_address(self) -> str:
        """
        获取钱包地址。
        
        返回:
            钱包地址
        """
        return self.address
    
    def sign(self, data: str) -> str:
        """
        使用私钥对数据进行签名。
        
        参数:
            data: 要签名的数据（字符串）
        
        返回:
            签名的十六进制字符串
        """
        data_bytes = data.encode('utf-8')
        
        if isinstance(self.private_key, str):
            private_key = SigningKey.from_string(
                bytes.fromhex(self.private_key),
                curve=SECP256k1
            )
        else:
            private_key = self.private_key
            
        signature = private_key.sign(data_bytes)
        return signature.hex()
    
    @classmethod
    def verify_signature(cls, public_key_hex: str, signature_hex: str, data: str) -> bool:
        """
        使用公钥验证签名是否有效。
        
        参数:
            public_key_hex: 公钥的十六进制字符串
            signature_hex: 签名的十六进制字符串
            data: 原始数据（字符串）
        
        返回:
            如果签名有效返回 True，否则返回 False
        """
        try:
            # 将公钥和签名从十六进制转换为字节
            public_key_bytes = bytes.fromhex(public_key_hex)
            signature_bytes = bytes.fromhex(signature_hex)
            
            # 创建公钥对象
            public_key = VerifyingKey.from_string(public_key_bytes, curve=SECP256k1)
            
            # 验证签名
            data_bytes = data.encode('utf-8')
            return public_key.verify(signature_bytes, data_bytes)
        except Exception as e:
            print(f"[ERROR] 签名验证失败: {e}")
            return False
    
    @classmethod
    def from_private_key(cls, private_key_hex: str) -> 'Wallet':
        """
        从私钥恢复钱包。
        
        参数:
            private_key_hex: 私钥的十六进制字符串
        
        返回:
            Wallet 实例
        """
        wallet = cls.__new__(cls)
        wallet.private_key = SigningKey.from_string(
            bytes.fromhex(private_key_hex),
            curve=SECP256k1
        )
        wallet.public_key = wallet.private_key.get_verifying_key()
        wallet.address = wallet._generate_address()
        return wallet
    
    def __repr__(self) -> str:
        return f"Wallet(address={self.address[:8]}...)"


class KeyPair:
    """
    密钥对工具类，提供静态方法处理密钥。
    """
    
    @staticmethod
    def generate() -> tuple:
        """
        生成新的密钥对。
        
        返回:
            (private_key_hex, public_key_hex, address)
        """
        wallet = Wallet()
        return (
            wallet.get_private_key_hex(),
            wallet.get_public_key_hex(),
            wallet.get_address()
        )
    
    @staticmethod
    def sign(private_key_hex: str, data: str) -> str:
        """
        使用私钥签名数据。
        
        参数:
            private_key_hex: 私钥的十六进制字符串
            data: 要签名的数据
        
        返回:
            签名的十六进制字符串
        """
        private_key = SigningKey.from_string(
            bytes.fromhex(private_key_hex),
            curve=SECP256k1
        )
        data_bytes = data.encode('utf-8')
        signature = private_key.sign(data_bytes)
        return signature.hex()
    
    @staticmethod
    def verify(public_key_hex: str, signature_hex: str, data: str) -> bool:
        """
        验证签名。
        
        参数:
            public_key_hex: 公钥的十六进制字符串
            signature_hex: 签名的十六进制字符串
            data: 原始数据
        
        返回:
            如果签名有效返回 True，否则返回 False
        """
        return Wallet.verify_signature(public_key_hex, signature_hex, data)
