from flask import Flask, render_template, jsonify, request
from src.block import Blockchain, Block
from src.consensus import ProofOfWork, DifficultyAdjuster
from src.wallet import Wallet, KeyPair
from src.network import P2PNode
from src.transaction import Transaction, TxInput, TxOutput, UTXOSet
from src.database import Database
import threading
import time

app = Flask(__name__)

# 全局状态
db = Database()
blockchain = Blockchain()
pow = ProofOfWork(difficulty=2)
utxo_set = UTXOSet()
p2p_node = None
mining_thread = None
is_mining = False

# 钱包字典
wallets = {}

def load_data_from_db():
    """从数据库加载数据"""
    global blockchain, wallets, utxo_set
    
    # 加载区块
    blocks_data = db.load_blocks()
    if blocks_data:
        blockchain.chain = []
        for block_data in blocks_data:
            block = Block(
                index=block_data['index'],
                timestamp=block_data['timestamp'],
                transactions=block_data['transactions'],
                prev_hash=block_data['prev_hash'],
                nonce=block_data['nonce'],
                merkle_root=block_data['merkle_root']
            )
            block.hash = block_data['hash']
            blockchain.chain.append(block)
        print(f"[DB] 已加载 {len(blocks_data)} 个区块")
    else:
        print("[DB] 数据库为空，创建创世区块")
    
    # 加载钱包
    wallets_data = db.load_wallets()
    if wallets_data:
        for wallet_data in wallets_data:
            wallet = Wallet()
            wallet.address = wallet_data['address']
            wallet.public_key = wallet_data['public_key']
            wallet.private_key = wallet_data['private_key']
            wallets[wallet_data['name']] = wallet
        print(f"[DB] 已加载 {len(wallets_data)} 个钱包")
    
    # 加载 UTXO
    utxos_data = db.load_utxos()
    if utxos_data:
        for utxo in utxos_data:
            output = TxOutput(value=utxo['value'], script_pubkey=utxo['script_pubkey'])
            utxo_set.add_utxo(
                txid=utxo['txid'],
                vout=utxo['vout'],
                output=output
            )
        print(f"[DB] 已加载 {len(utxos_data)} 个 UTXO")
    
    # 加载待处理交易
    pending_txs = db.load_pending_transactions()
    if pending_txs:
        blockchain.pending_transactions = pending_txs
        print(f"[DB] 已加载 {len(pending_txs)} 个待处理交易")

def save_block_to_db(block):
    """保存区块到数据库"""
    block_data = {
        'index': block.index,
        'hash': block.hash,
        'prev_hash': block.prev_hash,
        'timestamp': block.timestamp,
        'nonce': block.nonce,
        'merkle_root': block.merkle_root,
        'transactions': block.transactions
    }
    db.save_block(block_data)

def save_wallet_to_db(name, wallet, balance=0):
    """保存钱包到数据库"""
    db.save_wallet(
        name=name,
        address=wallet.get_address(),
        public_key=wallet.get_public_key_hex(),
        private_key=wallet.get_private_key_hex(),
        balance=balance
    )

def save_utxo_to_db(txid, vout, value, script_pubkey):
    """保存 UTXO 到数据库"""
    db.save_utxo(txid, vout, value, script_pubkey)

def mark_utxo_spent_in_db(txid, vout):
    """标记 UTXO 为已花费"""
    db.mark_utxo_spent(txid, vout)

def save_transaction_to_db(txid, tx_data, status='pending'):
    """保存交易到数据库"""
    db.save_transaction(txid, tx_data, status)

def update_transaction_status_in_db(txid, status):
    """更新交易状态"""
    db.update_transaction_status(txid, status)

def clear_pending_transactions_in_db():
    """清空待处理交易"""
    db.clear_pending_transactions()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/blockchain')
def get_blockchain():
    """获取区块链信息"""
    chain_data = []
    for block in blockchain.chain:
        chain_data.append({
            "index": block.index,
            "hash": block.hash,
            "prev_hash": block.prev_hash,
            "timestamp": block.timestamp,
            "nonce": block.nonce,
            "merkle_root": block.merkle_root,
            "transaction_count": len(block.transactions)
        })
    return jsonify({
        "chain": chain_data,
        "length": len(blockchain.chain)
    })

@app.route('/api/block/<int:index>')
def get_block(index):
    """获取指定区块"""
    if index < 0 or index >= len(blockchain.chain):
        return jsonify({"error": "区块不存在"}), 404
    
    block = blockchain.chain[index]
    return jsonify({
        "index": block.index,
        "hash": block.hash,
        "prev_hash": block.prev_hash,
        "timestamp": block.timestamp,
        "nonce": block.nonce,
        "merkle_root": block.merkle_root,
        "transactions": block.transactions
    })

@app.route('/api/wallets')
def get_wallets():
    """获取所有钱包信息"""
    wallets_data = []
    for name, wallet in wallets.items():
        balance = utxo_set.get_balance(wallet.get_address())
        # 更新数据库中的余额
        db.update_wallet_balance(wallet.get_address(), balance)
        
        wallets_data.append({
            "name": name,
            "address": wallet.get_address(),
            "public_key": wallet.get_public_key_hex(),
            "private_key": wallet.get_private_key_hex(),
            "balance": balance
        })
    return jsonify(wallets_data)

@app.route('/api/mine', methods=['POST'])
def mine_block():
    """挖矿"""
    global blockchain, pow
    
    transactions = blockchain.get_pending_transactions()
    if not transactions:
        transactions = [{"from": "miner", "to": "reward", "amount": 50}]
    
    block = pow.mine_block(blockchain, transactions)
    
    if block:
        blockchain.add_block(block)
        
        # 保存区块到数据库
        save_block_to_db(block)
        
        # 更新 UTXO
        utxo_set.process_transaction(block)
        
        # 保存 UTXO 到数据库
        for tx in block.transactions:
            if isinstance(tx, dict):
                txid = tx.get('txid', '')
                for i, output in enumerate(tx.get('outputs', [])):
                    if isinstance(output, dict):
                        output_obj = TxOutput(value=output.get('value', 0), script_pubkey=output.get('script_pubkey', ''))
                        utxo_set.add_utxo(txid, i, output_obj)
                        save_utxo_to_db(
                            txid=txid,
                            vout=i,
                            value=output.get('value', 0),
                            script_pubkey=output.get('script_pubkey', '')
                        )
        
        # 清空待处理交易
        clear_pending_transactions_in_db()
        
        return jsonify({
            "success": True,
            "block": {
                "index": block.index,
                "hash": block.hash,
                "nonce": block.nonce,
                "transaction_count": len(block.transactions)
            }
        })
    else:
        return jsonify({"success": False, "error": "挖矿失败"})

@app.route('/api/transaction', methods=['POST'])
def create_transaction():
    """创建交易"""
    data = request.json
    from_addr = data.get('from')
    to_addr = data.get('to')
    amount = data.get('amount')
    
    if not from_addr or not to_addr or amount is None:
        return jsonify({"success": False, "error": "参数不全"}), 400
    
    # 创建交易
    inputs = []
    outputs = []
    
    # 找到足够的 UTXO
    utxos = utxo_set.get_utxos_for_address(from_addr)
    total_available = sum(utxo['value'] for utxo in utxos)
    
    if total_available < amount:
        return jsonify({"success": False, "error": "余额不足"}), 400
    
    # 创建输入
    for utxo in utxos:
        inputs.append(TxInput(txid=utxo['txid'], vout=utxo['vout']))
        if sum(o.value for o in outputs) + utxo['value'] >= amount:
            break
    
    # 创建输出
    outputs.append(TxOutput(value=amount, script_pubkey=to_addr))
    
    # 找零
    total_input = sum(utxo['value'] for utxo in utxos[:len(inputs)])
    if total_input > amount:
        outputs.append(TxOutput(value=total_input - amount, script_pubkey=from_addr))
    
    # 创建交易
    tx = Transaction(inputs, outputs)
    
    # 保存交易到数据库
    save_transaction_to_db(tx.txid, tx.to_dict())
    
    # 添加到待处理交易池
    blockchain.add_pending_transaction(tx.to_dict())
    
    return jsonify({
        "success": True,
        "txid": tx.txid,
        "inputs": len(inputs),
        "outputs": len(outputs)
    })

@app.route('/api/pending_transactions')
def get_pending_transactions():
    """获取待处理交易"""
    return jsonify(blockchain.pending_transactions)

@app.route('/api/utxo')
def get_utxo():
    """获取 UTXO 集合"""
    return jsonify(utxo_set.to_dict())

@app.route('/api/network')
def get_network_status():
    """获取网络状态"""
    if p2p_node:
        return jsonify({
            "running": p2p_node.running,
            "host": p2p_node.host,
            "port": p2p_node.port,
            "peer_count": p2p_node.get_peer_count(),
            "peers": [{"host": p.address[0], "port": p.address[1]} for p in p2p_node.get_peers()]
        })
    else:
        return jsonify({"running": False})

@app.route('/api/start_mining', methods=['POST'])
def start_mining():
    """开始挖矿"""
    global is_mining, mining_thread
    
    if is_mining:
        return jsonify({"success": False, "error": "已经在挖矿中"})
    
    is_mining = True
    
    def mine_loop():
        global is_mining
        while is_mining:
            try:
                transactions = blockchain.get_pending_transactions()
                if not transactions:
                    transactions = [{"from": "miner", "to": "reward", "amount": 50}]
                
                block = pow.mine_block(blockchain, transactions)
                if block:
                    blockchain.add_block(block)
                    
                    # 保存区块到数据库
                    save_block_to_db(block)
                    
                    # 更新 UTXO
                    utxo_set.process_transaction(block)
                    
                    # 保存 UTXO 到数据库
                    for tx in block.transactions:
                        if isinstance(tx, dict):
                            txid = tx.get('txid', '')
                            for i, output in enumerate(tx.get('outputs', [])):
                                if isinstance(output, dict):
                                    output_obj = TxOutput(value=output.get('value', 0), script_pubkey=output.get('script_pubkey', ''))
                                    utxo_set.add_utxo(txid, i, output_obj)
                                    save_utxo_to_db(
                                        txid=txid,
                                        vout=i,
                                        value=output.get('value', 0),
                                        script_pubkey=output.get('script_pubkey', '')
                                    )
                    
                    # 清空待处理交易
                    clear_pending_transactions_in_db()
                    
                    print(f"[MINING] 挖到区块 #{block.index}: {block.hash[:8]}...")
            except Exception as e:
                print(f"[MINING ERROR] {e}")
                break
            time.sleep(0.1)
    
    mining_thread = threading.Thread(target=mine_loop)
    mining_thread.daemon = True
    mining_thread.start()
    
    return jsonify({"success": True, "message": "挖矿已启动"})

@app.route('/api/stop_mining', methods=['POST'])
def stop_mining():
    """停止挖矿"""
    global is_mining
    is_mining = False
    return jsonify({"success": True, "message": "挖矿已停止"})

@app.route('/api/mining_status')
def get_mining_status():
    """获取挖矿状态"""
    return jsonify({"is_mining": is_mining})

@app.route('/api/start_network', methods=['POST'])
def start_network():
    """启动 P2P 网络"""
    global p2p_node
    
    if p2p_node and p2p_node.running:
        return jsonify({"success": False, "error": "网络已启动"})
    
    data = request.json
    port = data.get('port', 8888)
    
    p2p_node = P2PNode('127.0.0.1', port)
    p2p_node.set_blockchain(blockchain)
    p2p_node.start()
    
    return jsonify({"success": True, "message": f"P2P 网络已启动，监听端口 {port}"})

@app.route('/api/stop_network', methods=['POST'])
def stop_network():
    """停止 P2P 网络"""
    global p2p_node
    
    if p2p_node:
        p2p_node.stop()
        p2p_node = None
    
    return jsonify({"success": True, "message": "P2P 网络已停止"})

@app.route('/api/connect_peer', methods=['POST'])
def connect_peer():
    """连接到对等节点"""
    global p2p_node
    
    if not p2p_node or not p2p_node.running:
        return jsonify({"success": False, "error": "网络未启动"})
    
    data = request.json
    host = data.get('host')
    port = data.get('port')
    
    if not host or not port:
        return jsonify({"success": False, "error": "参数不全"}), 400
    
    success = p2p_node.connect_to_peer(host, port)
    
    return jsonify({
        "success": success,
        "message": "连接成功" if success else "连接失败"
    })

@app.route('/api/create_wallet', methods=['POST'])
def create_wallet():
    """创建新钱包"""
    data = request.json
    name = data.get('name', f"钱包{len(wallets)+1}")
    
    wallet = Wallet()
    wallets[name] = wallet
    
    # 保存到数据库
    save_wallet_to_db(name, wallet)
    
    return jsonify({
        "success": True,
        "name": name,
        "address": wallet.get_address(),
        "public_key": wallet.get_public_key_hex()
    })

if __name__ == '__main__':
    # 从数据库加载数据
    load_data_from_db()
    
    # 如果数据库为空，初始化一些示例数据
    if not wallets:
        print("[INIT] 初始化示例钱包...")
        for i in range(3):
            wallet = Wallet()
            name = f"钱包{i+1}"
            wallets[name] = wallet
            
            # 创建初始余额（模拟挖矿奖励）
            tx = Transaction(
                inputs=[TxInput(txid="", vout=-1)],
                outputs=[TxOutput(value=100 + i * 50, script_pubkey=wallet.get_address())]
            )
            utxo_set.process_transaction(tx)
            
            # 保存到数据库
            save_wallet_to_db(name, wallet)
            output_obj = TxOutput(value=100 + i * 50, script_pubkey=wallet.get_address())
            utxo_set.add_utxo(tx.txid, 0, output_obj)
            save_utxo_to_db(tx.txid, 0, 100 + i * 50, wallet.get_address())
            save_transaction_to_db(tx.txid, tx.to_dict(), 'confirmed')
        
        print(f"[INIT] 已创建 {len(wallets)} 个示例钱包")
    
    print(f"[START] 区块链高度: {len(blockchain.chain)}")
    print(f"[START] 钱包数量: {len(wallets)}")
    print(f"[START] UTXO 数量: {len(utxo_set.utxos)}")
    
    app.run(host='0.0.0.0', port=5000, debug=True)
