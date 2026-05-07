import hashlib
import json
from typing import Any


def sha256(data: Any) -> str:
    """
    计算数据的 SHA-256 哈希值。
    
    SHA-256 是一种密码学哈希函数，具有以下特性：
    1. 确定性：相同输入始终产生相同输出
    2. 单向性：无法从哈希值逆向推导出原始数据
    3. 抗碰撞性：很难找到两个不同输入产生相同哈希值
    4. 雪崩效应：输入微小变化会导致输出完全不同
    
    参数:
        data: 任意类型的数据（将被序列化为 JSON 字符串）
    
    返回:
        64 位十六进制字符串表示的哈希值
    """
    # 将数据序列化为 JSON 字符串，确保可哈希化
    if isinstance(data, str):
        data_bytes = data.encode('utf-8')
    else:
        # 使用 JSON 序列化，sort_keys=True 确保字典顺序一致
        data_str = json.dumps(data, sort_keys=True, separators=(',', ':'))
        data_bytes = data_str.encode('utf-8')
    
    # 计算 SHA-256 哈希
    hash_result = hashlib.sha256(data_bytes).hexdigest()
    return hash_result


def double_sha256(data: Any) -> str:
    """
    计算数据的双重 SHA-256 哈希值（比特币使用的方式）。
    
    双重哈希提供更高的安全性，防止长度扩展攻击。
    
    参数:
        data: 任意类型的数据
    
    返回:
        64 位十六进制字符串表示的双重哈希值
    """
    return sha256(sha256(data))
