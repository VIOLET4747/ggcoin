from flask import Flask, render_template, jsonify, request
from src.block import Blockchain, Block
from src.consensus import ProofOfWork, DifficultyAdjuster
from src.wallet import Wallet
from src.crypto import sha256
from src.transaction import Transaction, TxInput, TxOutput, UTXOSet
from src.database import Database
import threading
import time
import json
from datetime import datetime

app = Flask(__name__)

# 全局状态
db = Database()
blockchain = Blockchain()
pow = ProofOfWork(difficulty=2)
utxo_set = UTXOSet()
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
    global blockchain, pow, wallets
    
    transactions = blockchain.get_pending_transactions()
    if not transactions:
        # 将挖矿奖励分配给第一个钱包
        miner_address = list(wallets.values())[0].get_address() if wallets else "reward"
        # 创建正确格式的交易（包含 outputs）
        transactions = [{
            "txid": sha256(f"miner_{time.time()}"),
            "inputs": [],
            "outputs": [{"value": 50, "script_pubkey": miner_address}]
        }]
    
    block = pow.mine_block(blockchain, transactions)
    
    if block:
        blockchain.add_block(block)
        
        # 保存区块到数据库
        save_block_to_db(block)
        
        # 处理区块中所有交易的 UTXO
        for tx in block.transactions:
            if isinstance(tx, dict):
                txid = tx.get('txid', '')
                # 移除已花费的 UTXO（非 coinbase 交易）
                if tx.get('inputs'):
                    for inp in tx['inputs']:
                        if isinstance(inp, dict) and inp.get('txid'):
                            utxo_set.remove_utxo(inp['txid'], inp.get('vout', 0))
                # 添加新的 UTXO 并保存到数据库
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
    """创建交易（含 ECDSA 签名）"""
    data = request.json
    from_addr = data.get('from')
    to_addr = data.get('to')
    amount = data.get('amount')
    
    if not from_addr or not to_addr or amount is None:
        return jsonify({"success": False, "error": "参数不全"}), 400
    
    # 找到发送方钱包
    sender_wallet = None
    sender_name = None
    for name, wallet in wallets.items():
        if wallet.get_address() == from_addr:
            sender_wallet = wallet
            sender_name = name
            break
    
    if not sender_wallet:
        return jsonify({"success": False, "error": "找不到发送方钱包"}), 400
    
    inputs = []
    outputs = []
    
    utxos = utxo_set.get_utxos_for_address(from_addr)
    total_available = sum(utxo['value'] for utxo in utxos)
    
    if total_available < amount:
        return jsonify({"success": False, "error": "余额不足"}), 400
    
    for utxo in utxos:
        inputs.append(TxInput(txid=utxo['txid'], vout=utxo['vout']))
        if sum(o.value for o in outputs) + utxo['value'] >= amount:
            break
    
    outputs.append(TxOutput(value=amount, script_pubkey=to_addr))
    
    total_input = sum(utxo['value'] for utxo in utxos[:len(inputs)])
    if total_input > amount:
        outputs.append(TxOutput(value=total_input - amount, script_pubkey=from_addr))
    
    # 创建交易对象（不含签名）
    tx = Transaction(inputs, outputs)
    
    # 对每个输入签名
    signing_data = tx.get_transaction_data_for_signing()
    for i in range(len(inputs)):
        signature = sender_wallet.sign(signing_data)
        tx.inputs[i].signature = signature
    
    # 签名后重新计算 txid（签名也是交易的一部分）
    tx.txid = tx.calculate_txid()
    
    tx_dict = tx.to_dict()
    tx_dict['sender_name'] = sender_name
    tx_dict['sender_pubkey'] = sender_wallet.get_public_key_hex()
    
    # 保存交易到数据库
    save_transaction_to_db(tx.txid, tx_dict)
    
    # 添加到待处理交易池
    blockchain.add_pending_transaction(tx_dict)
    
    return jsonify({
        "success": True,
        "txid": tx.txid,
        "inputs": len(inputs),
        "outputs": len(outputs)
    })

@app.route('/api/verify_transaction', methods=['POST'])
def verify_transaction():
    """验证交易签名和完整性"""
    data = request.json
    txid = data.get('txid', '')
    
    if not txid:
        return jsonify({"success": False, "error": "请输入交易 ID"}), 400
    
    # 在区块链中查找交易
    found_tx = None
    found_block = None
    for block in blockchain.chain:
        for tx in block.transactions:
            if isinstance(tx, dict) and tx.get('txid') == txid:
                found_tx = tx
                found_block = block
                break
            elif hasattr(tx, 'txid') and tx.txid == txid:
                found_tx = tx.to_dict() if hasattr(tx, 'to_dict') else tx
                found_block = block
                break
        if found_tx:
            break
    
    # 不在区块链中，检查待处理交易
    is_pending = False
    if not found_tx:
        for tx in blockchain.pending_transactions:
            if isinstance(tx, dict) and tx.get('txid') == txid:
                found_tx = tx
                is_pending = True
                break
    
    if not found_tx:
        return jsonify({"success": False, "error": "未找到该交易"}), 404
    
    # 重建签名数据
    inputs_no_sig = []
    for inp in found_tx.get('inputs', []):
        inputs_no_sig.append({"txid": inp.get('txid', ''), "vout": inp.get('vout', 0)})
    
    signing_data = json.dumps({
        "inputs": inputs_no_sig,
        "outputs": found_tx.get('outputs', [])
    }, sort_keys=True, separators=(',', ':'))
    
    # 获取签名和公钥
    signatures = []
    sender_pubkey = found_tx.get('sender_pubkey', '')
    
    for inp in found_tx.get('inputs', []):
        sig = inp.get('signature', '')
        if sig:
            signatures.append(sig)
    
    # 验证签名
    sig_valid = False
    if signatures and sender_pubkey:
        sig_valid = Wallet.verify_signature(sender_pubkey, signatures[0], signing_data)
    
    receiver = ''
    total_out = 0
    for out in found_tx.get('outputs', []):
        total_out += out.get('value', 0)
        if not receiver:
            receiver = out.get('script_pubkey', '')
    
    result = {
        "success": True,
        "txid": txid,
        "status": "已确认" if found_block else ("待处理" if is_pending else "未找到"),
        "block_index": found_block.index if found_block else None,
        "signature_valid": sig_valid,
        "inputs_count": len(found_tx.get('inputs', [])),
        "outputs_count": len(found_tx.get('outputs', [])),
        "total_output": total_out,
        "receiver": receiver[:16] + '...' if len(receiver) > 16 else receiver,
        "is_coinbase": len(found_tx.get('inputs', [])) == 0
    }
    
    return jsonify(result)

@app.route('/api/verify_blockchain', methods=['POST'])
def verify_blockchain():
    """验证区块链完整性"""
    results = []
    
    for i, block in enumerate(blockchain.chain):
        block_result = {"index": block.index, "valid": True, "checks": {}}
        
        # 1. 验证区块哈希
        expected_hash = block.calculate_hash()
        hash_valid = (expected_hash == block.hash)
        block_result["checks"]["hash_match"] = hash_valid
        if not hash_valid:
            block_result["valid"] = False
            block_result["hash_error"] = f"期望 {expected_hash[:16]}..., 实际 {block.hash[:16]}..."
        
        # 2. 验证与上一块的链接
        if i > 0:
            prev_hash_valid = (block.prev_hash == blockchain.chain[i-1].hash)
            block_result["checks"]["prev_hash_match"] = prev_hash_valid
            if not prev_hash_valid:
                block_result["valid"] = False
                block_result["prev_hash_error"] = f"不匹配上一区块哈希"
        else:
            block_result["checks"]["prev_hash_match"] = True
            block_result["is_genesis"] = True
        
        # 3. 验证 Merkle 根
        expected_merkle = block.calculate_merkle_root()
        merkle_valid = (expected_merkle == block.merkle_root)
        block_result["checks"]["merkle_root_match"] = merkle_valid
        if not merkle_valid:
            block_result["valid"] = False
            block_result["merkle_error"] = f"期望 {expected_merkle[:16]}..., 实际 {block.merkle_root[:16]}..."
        
        # 4. 验证交易签名
        tx_sigs_valid = True
        for tx in block.transactions:
            if isinstance(tx, dict):
                if tx.get('inputs') and tx.get('sender_pubkey'):
                    inputs_no_sig = [{"txid": inp.get('txid', ''), "vout": inp.get('vout', 0)} for inp in tx['inputs']]
                    sig_data = json.dumps({"inputs": inputs_no_sig, "outputs": tx.get('outputs', [])}, sort_keys=True, separators=(',', ':'))
                    sig = tx['inputs'][0].get('signature', '') if tx['inputs'] else ''
                    pubkey = tx.get('sender_pubkey', '')
                    if sig and pubkey:
                        if not Wallet.verify_signature(pubkey, sig, sig_data):
                            tx_sigs_valid = False
                            break
        
        block_result["checks"]["tx_signatures_valid"] = tx_sigs_valid
        if not tx_sigs_valid:
            block_result["valid"] = False
        
        results.append(block_result)
    
    total_blocks = len(results)
    valid_blocks = sum(1 for r in results if r["valid"])
    
    return jsonify({
        "success": True,
        "total_blocks": total_blocks,
        "valid_blocks": valid_blocks,
        "chain_intact": (total_blocks == valid_blocks),
        "details": results
    })

@app.route('/api/pending_transactions')
def get_pending_transactions():
    """获取待处理交易"""
    return jsonify(blockchain.pending_transactions)

@app.route('/api/utxo')
def get_utxo():
    """获取 UTXO 集合"""
    return jsonify(utxo_set.to_dict())



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
                    # 将挖矿奖励分配给第一个钱包
                    miner_address = list(wallets.values())[0].get_address() if wallets else "reward"
                    # 创建正确格式的交易（包含 outputs）
                    transactions = [{
                        "txid": sha256(f"miner_{time.time()}"),
                        "inputs": [],
                        "outputs": [{"value": 50, "script_pubkey": miner_address}]
                    }]
                
                block = pow.mine_block(blockchain, transactions)
                if block:
                    blockchain.add_block(block)
                    
                    # 保存区块到数据库
                    save_block_to_db(block)
                    
                    # 处理区块中所有交易的 UTXO
                    for tx in block.transactions:
                        if isinstance(tx, dict):
                            txid = tx.get('txid', '')
                            for i, output in enumerate(tx.get('outputs', [])):
                                if isinstance(output, dict):
                                    utxo_set.add_utxo(txid, i, TxOutput(value=output.get('value', 0), script_pubkey=output.get('script_pubkey', '')))
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

@app.route('/api/mining_rewards')
def get_mining_rewards():
    """获取挖矿收益记录"""
    rewards = []
    print(f"[DEBUG] 区块链高度: {len(blockchain.chain)}")
    
    for block in blockchain.chain[1:]:  # 跳过创世区块
        print(f"[DEBUG] 区块 #{block.index}, 交易数: {len(block.transactions)}")
        
        for tx in block.transactions:
            # 处理 Transaction 对象
            if hasattr(tx, 'outputs'):
                outputs = tx.outputs
                for i, output in enumerate(outputs):
                    if hasattr(output, 'value') and output.value == 50:
                        address = output.script_pubkey[:8] + '...' if output.script_pubkey else 'unknown'
                        rewards.append({
                            'block_height': block.index,
                            'timestamp': block.timestamp,
                            'reward': 50,
                            'address': address
                        })
            # 处理字典类型的交易
            elif isinstance(tx, dict):
                outputs = tx.get('outputs', [])
                for output in outputs:
                    if isinstance(output, dict) and output.get('value') == 50:
                        address = output.get('script_pubkey', '')[:8] + '...'
                        rewards.append({
                            'block_height': block.index,
                            'timestamp': block.timestamp,
                            'reward': 50,
                            'address': address
                        })
    
    print(f"[DEBUG] 找到 {len(rewards)} 条挖矿收益记录")
    return jsonify({"success": True, "rewards": rewards})

@app.route('/api/export_data')
def export_data():
    """导出数据库数据为 JSON"""
    data = {
        'blocks': blockchain.chain,
        'wallets': {name: {
            'address': wallet.address,
            'public_key': wallet.get_public_key_hex(),
            'balance': wallet.get_balance()
        } for name, wallet in wallets.items()},
        'utxos': list(utxo_set.utxos.keys()),
        'pending_transactions': blockchain.get_pending_transactions(),
        'export_time': datetime.now().isoformat()
    }
    return jsonify({"success": True, "data": data})

def create_initial_wallets():
    """创建初始示例钱包"""
    global wallets, utxo_set
    
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

@app.route('/api/reset_database', methods=['POST'])
def reset_database():
    """重置数据库 - 清空所有数据并重新初始化"""
    global blockchain, utxo_set, wallets, is_mining
    
    # 停止挖矿
    is_mining = False
    
    # 删除数据库文件
    import os
    db_path = 'ggcoin.db'
    if os.path.exists(db_path):
        os.remove(db_path)
    
    # 重新初始化
    blockchain = Blockchain()
    utxo_set = UTXOSet()
    wallets = {}
    
    # 重新创建数据库
    db = Database()
    
    # 创建初始钱包
    create_initial_wallets()
    
    return jsonify({"success": True, "message": "数据库已重置"})

@app.route('/api/quick_mine', methods=['POST'])
def quick_mine():
    """快速挖矿 - 一次性挖掘多个区块"""
    data = request.json
    count = data.get('count', 10)  # 默认挖10个区块
    
    if is_mining:
        return jsonify({"success": False, "error": "请先停止挖矿"})
    
    blocks_mined = []
    
    for i in range(count):
        transactions = blockchain.get_pending_transactions()
        if not transactions:
            # 将挖矿奖励分配给第一个钱包
            miner_address = list(wallets.values())[0].get_address() if wallets else "reward"
            # 创建正确格式的交易（包含 outputs）
            transactions = [{
                "txid": sha256(f"miner_{time.time()}_{i}"),
                "inputs": [],
                "outputs": [{"value": 50, "script_pubkey": miner_address}]
            }]
        
        block = pow.mine_block(blockchain, transactions)
        if block:
            blockchain.add_block(block)
            save_block_to_db(block)
            
            for tx in block.transactions:
                if isinstance(tx, dict):
                    txid = tx.get('txid', '')
                    for j, output in enumerate(tx.get('outputs', [])):
                        if isinstance(output, dict):
                            utxo_set.add_utxo(txid, j, TxOutput(value=output.get('value', 0), script_pubkey=output.get('script_pubkey', '')))
                            save_utxo_to_db(
                                txid=txid,
                                vout=j,
                                value=output.get('value', 0),
                                script_pubkey=output.get('script_pubkey', '')
                            )
            
            blocks_mined.append(block.index)
    
    return jsonify({
        "success": True,
        "message": f"成功挖掘 {len(blocks_mined)} 个区块",
        "blocks": blocks_mined
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
