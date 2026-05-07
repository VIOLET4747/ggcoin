import socket
import threading
import json
import struct
import time
from typing import List, Dict, Optional, Callable
from .block import Blockchain, Block
from .transaction import Transaction


class MessageType:
    """
    消息类型枚举，定义 P2P 网络中传输的消息类型。
    """
    # 节点发现消息
    HELLO = 0x01           # 初始握手
    GET_PEERS = 0x02       # 请求节点列表
    PEERS = 0x03           # 节点列表响应
    
    # 区块链同步消息
    GET_BLOCKS = 0x04      # 请求区块
    BLOCKS = 0x05          # 区块响应
    NEW_BLOCK = 0x06       # 新区块广播
    
    # 交易消息
    NEW_TRANSACTION = 0x07 # 新交易广播
    
    # 状态消息
    GET_CHAIN_HEIGHT = 0x08 # 请求链高度
    CHAIN_HEIGHT = 0x09     # 链高度响应


class Message:
    """
    P2P 网络消息类，封装自定义报文协议。
    
    报文格式：
    +----------+--------+---------+----------+
    | Magic    | Type   | Length  | Payload  |
    | (4 bytes)|(1 byte)|(4 bytes)|(N bytes) |
    +----------+--------+---------+----------+
    
    Magic: 魔数，用于识别协议（固定为 0x4D494E49，"MINI"）
    Type: 消息类型（参考 MessageType）
    Length: 负载长度（大端序）
    Payload: 消息负载（JSON 格式）
    """
    
    # 协议魔数
    MAGIC = 0x4D494E49  # "MINI"
    
    def __init__(self, msg_type: int, payload: dict = None):
        """
        初始化消息。
        
        参数:
            msg_type: 消息类型（MessageType 枚举值）
            payload: 消息负载（字典格式，将被序列化为 JSON）
        """
        self.msg_type = msg_type
        self.payload = payload if payload else {}
    
    def serialize(self) -> bytes:
        """
        将消息序列化为字节流。
        
        返回:
            序列化后的字节数组
        """
        # 将负载序列化为 JSON 字符串
        payload_json = json.dumps(self.payload, separators=(',', ':'))
        payload_bytes = payload_json.encode('utf-8')
        
        # 构建消息头
        # Magic: 4 bytes (大端序)
        # Type: 1 byte
        # Length: 4 bytes (大端序)
        header = struct.pack('!IBI', self.MAGIC, self.msg_type, len(payload_bytes))
        
        # 组合完整消息
        return header + payload_bytes
    
    @classmethod
    def deserialize(cls, data: bytes) -> Optional['Message']:
        """
        从字节流反序列化消息。
        
        参数:
            data: 包含消息的字节数组
        
        返回:
            Message 对象，如果解析失败返回 None
        """
        try:
            # 检查最小长度（Magic 4 + Type 1 + Length 4 = 9 bytes）
            if len(data) < 9:
                return None
            
            # 解析消息头
            magic, msg_type, length = struct.unpack('!IBI', data[:9])
            
            # 验证魔数
            if magic != cls.MAGIC:
                print(f"[ERROR] 无效的魔数: {hex(magic)}")
                return None
            
            # 检查负载长度
            if len(data) < 9 + length:
                return None  # 数据不完整
            
            # 解析负载
            payload_bytes = data[9:9+length]
            payload = json.loads(payload_bytes.decode('utf-8'))
            
            return cls(msg_type, payload)
        
        except Exception as e:
            print(f"[ERROR] 消息解析失败: {e}")
            return None
    
    def __repr__(self) -> str:
        return f"Message(type={hex(self.msg_type)}, payload={self.payload})"


class Peer:
    """
    对等节点类，代表网络中的一个连接节点。
    """
    
    def __init__(self, socket: socket.socket, address: tuple):
        """
        初始化对等节点。
        
        参数:
            socket: 与该节点的连接套接字
            address: 节点地址（IP, 端口）
        """
        self.socket = socket
        self.address = address
        self.last_seen = time.time()
        self.chain_height = 0
    
    def send_message(self, message: Message) -> bool:
        """
        向该节点发送消息。
        
        参数:
            message: 要发送的消息
        
        返回:
            如果发送成功返回 True，否则返回 False
        """
        try:
            data = message.serialize()
            self.socket.sendall(data)
            self.last_seen = time.time()
            return True
        except Exception as e:
            print(f"[ERROR] 发送消息到 {self.address} 失败: {e}")
            return False
    
    def close(self):
        """关闭与该节点的连接"""
        try:
            self.socket.close()
        except Exception as e:
            print(f"[ERROR] 关闭连接失败: {e}")
    
    def __repr__(self) -> str:
        return f"Peer({self.address[0]}:{self.address[1]}, height={self.chain_height})"


class P2PNode:
    """
    P2P 节点类，实现完整的 P2P 网络功能。
    
    功能包括：
    1. TCP 服务器，接受 incoming 连接
    2. TCP 客户端，连接到其他节点
    3. 节点发现机制
    4. 消息广播（Gossip Protocol）
    5. 区块链同步
    6. 最长链共识
    """
    
    def __init__(self, host: str = '127.0.0.1', port: int = 8888):
        """
        初始化 P2P 节点。
        
        参数:
            host: 绑定的 IP 地址
            port: 绑定的端口
        """
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
        # 对等节点列表
        self.peers: Dict[tuple, Peer] = {}
        self.peers_lock = threading.Lock()
        
        # 区块链引用
        self.blockchain = None
        
        # 消息处理器注册
        self.message_handlers: Dict[int, Callable] = {
            MessageType.HELLO: self._handle_hello,
            MessageType.GET_PEERS: self._handle_get_peers,
            MessageType.PEERS: self._handle_peers,
            MessageType.GET_BLOCKS: self._handle_get_blocks,
            MessageType.BLOCKS: self._handle_blocks,
            MessageType.NEW_BLOCK: self._handle_new_block,
            MessageType.NEW_TRANSACTION: self._handle_new_transaction,
            MessageType.GET_CHAIN_HEIGHT: self._handle_get_chain_height,
            MessageType.CHAIN_HEIGHT: self._handle_chain_height,
        }
        
        # 最近看到的区块哈希（用于防止重复处理）
        self.seen_blocks = set()
        
        # 最近看到的交易哈希（用于防止重复处理）
        self.seen_transactions = set()
    
    def set_blockchain(self, blockchain: Blockchain):
        """
        设置区块链引用。
        
        参数:
            blockchain: 区块链实例
        """
        self.blockchain = blockchain
    
    def start(self):
        """启动 P2P 节点"""
        # 创建 TCP 套接字
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        
        try:
            self.socket.bind((self.host, self.port))
            self.socket.listen(10)
            self.running = True
            print(f"[INFO] P2P 节点已启动，监听 {self.host}:{self.port}")
            
            # 启动接受连接的线程
            accept_thread = threading.Thread(target=self._accept_connections)
            accept_thread.daemon = True
            accept_thread.start()
            
        except Exception as e:
            print(f"[ERROR] 启动 P2P 节点失败: {e}")
            self.running = False
    
    def stop(self):
        """停止 P2P 节点"""
        self.running = False
        
        # 关闭所有对等节点连接
        with self.peers_lock:
            for peer in self.peers.values():
                peer.close()
            self.peers.clear()
        
        # 关闭主套接字
        if self.socket:
            try:
                self.socket.close()
            except Exception as e:
                print(f"[ERROR] 关闭套接字失败: {e}")
        
        print("[INFO] P2P 节点已停止")
    
    def connect_to_peer(self, peer_host: str, peer_port: int) -> bool:
        """
        连接到一个对等节点。
        
        参数:
            peer_host: 目标节点 IP 地址
            peer_port: 目标节点端口
        
        返回:
            如果连接成功返回 True，否则返回 False
        """
        try:
            # 检查是否已连接
            if (peer_host, peer_port) in self.peers:
                print(f"[INFO] 已连接到 {peer_host}:{peer_port}")
                return True
            
            # 创建连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((peer_host, peer_port))
            
            # 创建 Peer 对象
            peer = Peer(sock, (peer_host, peer_port))
            with self.peers_lock:
                self.peers[(peer_host, peer_port)] = peer
            
            print(f"[INFO] 成功连接到节点 {peer_host}:{peer_port}")
            
            # 发送 HELLO 消息进行握手
            self._send_hello(peer)
            
            # 启动接收消息线程
            recv_thread = threading.Thread(
                target=self._receive_messages,
                args=(peer,)
            )
            recv_thread.daemon = True
            recv_thread.start()
            
            return True
        
        except Exception as e:
            print(f"[ERROR] 连接到 {peer_host}:{peer_port} 失败: {e}")
            return False
    
    def _accept_connections(self):
        """接受 incoming 连接"""
        while self.running:
            try:
                self.socket.settimeout(1.0)
                conn, addr = self.socket.accept()
                
                print(f"[INFO] 接收到来自 {addr} 的连接")
                
                # 创建 Peer 对象
                peer = Peer(conn, addr)
                with self.peers_lock:
                    self.peers[addr] = peer
                
                # 启动接收消息线程
                recv_thread = threading.Thread(
                    target=self._receive_messages,
                    args=(peer,)
                )
                recv_thread.daemon = True
                recv_thread.start()
                
                # 发送 HELLO 消息进行握手
                self._send_hello(peer)
                
            except socket.timeout:
                continue
            except Exception as e:
                if self.running:
                    print(f"[ERROR] 接受连接失败: {e}")
    
    def _receive_messages(self, peer: Peer):
        """接收来自对等节点的消息"""
        buffer = b''
        
        while self.running:
            try:
                peer.socket.settimeout(1.0)
                data = peer.socket.recv(4096)
                
                if not data:
                    # 连接已关闭
                    print(f"[INFO] 节点 {peer.address} 断开连接")
                    with self.peers_lock:
                        del self.peers[peer.address]
                    peer.close()
                    break
                
                buffer += data
                
                # 尝试解析消息
                while True:
                    message = Message.deserialize(buffer)
                    if message:
                        # 处理消息
                        self._handle_message(peer, message)
                        # 移除已处理的消息
                        msg_length = 9 + len(json.dumps(message.payload, separators=(',', ':')))
                        buffer = buffer[msg_length:]
                    else:
                        break  # 数据不完整，等待更多数据
            
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[ERROR] 接收消息失败: {e}")
                with self.peers_lock:
                    if peer.address in self.peers:
                        del self.peers[peer.address]
                peer.close()
                break
    
    def _handle_message(self, peer: Peer, message: Message):
        """处理接收到的消息"""
        handler = self.message_handlers.get(message.msg_type)
        if handler:
            try:
                handler(peer, message)
            except Exception as e:
                print(f"[ERROR] 处理消息类型 {hex(message.msg_type)} 失败: {e}")
        else:
            print(f"[WARNING] 未知消息类型: {hex(message.msg_type)}")
    
    def _send_hello(self, peer: Peer):
        """发送 HELLO 消息"""
        payload = {
            "version": "1.0",
            "height": len(self.blockchain.chain) if self.blockchain else 0,
            "peer_port": self.port
        }
        message = Message(MessageType.HELLO, payload)
        peer.send_message(message)
    
    def _handle_hello(self, peer: Peer, message: Message):
        """处理 HELLO 消息"""
        payload = message.payload
        peer.chain_height = payload.get("height", 0)
        print(f"[INFO] 接收到 HELLO 消息 from {peer.address}, 链高度: {peer.chain_height}")
        
        # 如果对方链更长，请求同步
        if self.blockchain and peer.chain_height > len(self.blockchain.chain):
            self._request_blocks(peer)
    
    def _handle_get_peers(self, peer: Peer, message: Message):
        """处理 GET_PEERS 消息"""
        with self.peers_lock:
            peer_list = [{"host": addr[0], "port": addr[1]} for addr in self.peers.keys()]
        
        response = Message(MessageType.PEERS, {"peers": peer_list})
        peer.send_message(response)
    
    def _handle_peers(self, peer: Peer, message: Message):
        """处理 PEERS 消息"""
        peer_list = message.payload.get("peers", [])
        print(f"[INFO] 收到 {len(peer_list)} 个节点地址")
        
        for p in peer_list:
            host = p.get("host")
            port = p.get("port")
            if host and port:
                # 避免连接自己
                if not (host == self.host and port == self.port):
                    self.connect_to_peer(host, port)
    
    def _handle_get_blocks(self, peer: Peer, message: Message):
        """处理 GET_BLOCKS 消息"""
        payload = message.payload
        start_index = payload.get("start", 0)
        end_index = payload.get("end", -1)
        
        if not self.blockchain:
            response = Message(MessageType.BLOCKS, {"blocks": []})
            peer.send_message(response)
            return
        
        # 获取区块范围
        if end_index < 0 or end_index >= len(self.blockchain.chain):
            end_index = len(self.blockchain.chain) - 1
        
        blocks_data = []
        for i in range(start_index, end_index + 1):
            block = self.blockchain.chain[i]
            blocks_data.append(block.to_dict())
        
        response = Message(MessageType.BLOCKS, {
            "blocks": blocks_data,
            "start": start_index,
            "end": end_index
        })
        peer.send_message(response)
    
    def _handle_blocks(self, peer: Peer, message: Message):
        """处理 BLOCKS 消息"""
        payload = message.payload
        blocks_data = payload.get("blocks", [])
        
        if not self.blockchain or not blocks_data:
            return
        
        print(f"[INFO] 收到 {len(blocks_data)} 个区块")
        
        # 添加区块到区块链
        for block_data in blocks_data:
            block = Block.from_dict(block_data)
            
            # 检查是否已存在
            if any(b.hash == block.hash for b in self.blockchain.chain):
                continue
            
            # 添加区块
            success = self.blockchain.add_block(block)
            if success:
                print(f"[INFO] 同步区块 #{block.index}: {block.hash[:8]}...")
                # 广播新区块
                self.broadcast_new_block(block)
    
    def _handle_new_block(self, peer: Peer, message: Message):
        """处理 NEW_BLOCK 消息"""
        payload = message.payload
        block_data = payload.get("block")
        
        if not block_data or not self.blockchain:
            return
        
        block = Block.from_dict(block_data)
        
        # 检查是否已处理过
        if block.hash in self.seen_blocks:
            return
        
        self.seen_blocks.add(block.hash)
        
        print(f"[INFO] 收到新区块 #{block.index}: {block.hash[:8]}...")
        
        # 添加区块
        success = self.blockchain.add_block(block)
        if success:
            # 广播给其他节点（Gossip）
            self.broadcast_new_block(block, exclude_peer=peer.address)
    
    def _handle_new_transaction(self, peer: Peer, message: Message):
        """处理 NEW_TRANSACTION 消息"""
        payload = message.payload
        tx_data = payload.get("transaction")
        
        if not tx_data or not self.blockchain:
            return
        
        tx = Transaction.from_dict(tx_data)
        
        # 检查是否已处理过
        if tx.txid in self.seen_transactions:
            return
        
        self.seen_transactions.add(tx.txid)
        
        print(f"[INFO] 收到新交易: {tx.txid[:8]}...")
        
        # 添加到待处理交易池
        self.blockchain.add_pending_transaction(tx_data)
        
        # 广播给其他节点（Gossip）
        self.broadcast_new_transaction(tx, exclude_peer=peer.address)
    
    def _handle_get_chain_height(self, peer: Peer, message: Message):
        """处理 GET_CHAIN_HEIGHT 消息"""
        height = len(self.blockchain.chain) if self.blockchain else 0
        response = Message(MessageType.CHAIN_HEIGHT, {"height": height})
        peer.send_message(response)
    
    def _handle_chain_height(self, peer: Peer, message: Message):
        """处理 CHAIN_HEIGHT 消息"""
        height = message.payload.get("height", 0)
        peer.chain_height = height
        
        # 如果对方链更长，请求同步
        if self.blockchain and height > len(self.blockchain.chain):
            self._request_blocks(peer)
    
    def _request_blocks(self, peer: Peer):
        """请求对方的区块"""
        if not self.blockchain:
            return
        
        current_height = len(self.blockchain.chain)
        payload = {
            "start": current_height,
            "end": -1  # -1 表示请求所有剩余区块
        }
        message = Message(MessageType.GET_BLOCKS, payload)
        peer.send_message(message)
    
    def broadcast_new_block(self, block: Block, exclude_peer: tuple = None):
        """
        广播新区块到所有连接的节点。
        
        参数:
            block: 要广播的区块
            exclude_peer: 排除的节点地址（避免回传给发送者）
        """
        payload = {"block": block.to_dict()}
        message = Message(MessageType.NEW_BLOCK, payload)
        self._broadcast(message, exclude_peer)
    
    def broadcast_new_transaction(self, tx: Transaction, exclude_peer: tuple = None):
        """
        广播新交易到所有连接的节点。
        
        参数:
            tx: 要广播的交易
            exclude_peer: 排除的节点地址（避免回传给发送者）
        """
        payload = {"transaction": tx.to_dict()}
        message = Message(MessageType.NEW_TRANSACTION, payload)
        self._broadcast(message, exclude_peer)
    
    def request_peers(self):
        """向所有节点请求节点列表"""
        message = Message(MessageType.GET_PEERS)
        self._broadcast(message)
    
    def sync_chain(self):
        """同步区块链"""
        # 找到链最长的节点
        max_height = 0
        target_peer = None
        
        with self.peers_lock:
            for peer in self.peers.values():
                if peer.chain_height > max_height:
                    max_height = peer.chain_height
                    target_peer = peer
        
        if target_peer and self.blockchain:
            if max_height > len(self.blockchain.chain):
                print(f"[INFO] 正在从 {target_peer.address} 同步区块链")
                self._request_blocks(target_peer)
    
    def _broadcast(self, message: Message, exclude_peer: tuple = None):
        """
        广播消息到所有连接的节点。
        
        参数:
            message: 要广播的消息
            exclude_peer: 排除的节点地址
        """
        with self.peers_lock:
            peers = list(self.peers.items())
        
        for addr, peer in peers:
            if addr == exclude_peer:
                continue
            
            peer.send_message(message)
    
    def get_peer_count(self) -> int:
        """获取连接的节点数量"""
        with self.peers_lock:
            return len(self.peers)
    
    def get_peers(self) -> List[Peer]:
        """获取所有连接的节点列表"""
        with self.peers_lock:
            return list(self.peers.values())
    
    def resolve_conflicts(self) -> bool:
        """
        解决区块链冲突，实现最长链共识。
        
        返回:
            如果链被替换返回 True，否则返回 False
        """
        if not self.blockchain:
            return False
        
        max_height = len(self.blockchain.chain)
        longest_chain = None
        
        # 检查所有节点的链高度
        with self.peers_lock:
            for peer in self.peers.values():
                if peer.chain_height > max_height:
                    # 请求完整的链
                    self._request_full_chain(peer)
        
        # 检查是否收到了更长的链
        # （实际实现中需要缓存收到的链并比较）
        
        return False  # 简化实现
    
    def _request_full_chain(self, peer: Peer):
        """请求完整的区块链"""
        payload = {"start": 0, "end": -1}
        message = Message(MessageType.GET_BLOCKS, payload)
        peer.send_message(message)
    
    def __repr__(self) -> str:
        return f"P2PNode({self.host}:{self.port}, peers={self.get_peer_count()})"
