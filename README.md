# ggcoin - 极简区块链系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/sqlite-3.0%2B-orange.svg)](https://www.sqlite.org/)

ggcoin 是一个用 Python 实现的极简区块链系统，包含完整的核心功能：工作量证明、交易系统、钱包管理和 P2P 网络。支持 SQLite 数据库持久化，数据自动保存，重启不丢失。

---

## 📁 项目结构

```
ggcoin/
├── src/                    # 核心源代码
│   ├── __init__.py         # 模块初始化
│   ├── crypto.py           # 密码学工具（SHA-256）
│   ├── block.py            # 区块和区块链数据结构
│   ├── consensus.py        # 工作量证明（PoW）和难度调整
│   ├── transaction.py      # 交易结构和 UTXO 模型
│   ├── wallet.py           # ECDSA 钱包和数字签名
│   ├── merkle_tree.py      # 默克尔树实现
│   ├── network.py          # P2P 网络协议
│   └── database.py         # SQLite 数据库持久化
├── templates/              # Web 界面模板
│   └── index.html          # 可视化管理界面
├── app.py                  # Flask Web 应用
├── ggcoin.db               # SQLite 数据库文件（自动生成）
└── README.md               # 项目文档
```

---

## ✨ 功能特性

### 🏗️ 核心数据结构
- **区块结构**：包含索引、时间戳、交易、前区块哈希、Nonce、默克尔根
- **区块链**：链式存储、完整性验证、创世区块
- **默克尔树**：交易数据摘要、快速验证

### ⛏️ 共识机制
- **工作量证明（PoW）**：SHA-256 哈希挖矿
- **动态难度调整**：根据网络算力自动调整
- **挖矿奖励**：支持 Coinbase 交易

### 💳 交易系统
- **UTXO 模型**：未花费交易输出管理
- **数字签名**：ECDSA (SECP256k1) 签名验证
- **交易广播**：P2P 网络传播

### 👛 钱包管理
- **密钥生成**：公私钥对生成
- **地址生成**：公钥哈希地址
- **签名/验证**：交易签名和验证

### 🌐 P2P 网络
- **节点发现**：Gossip 协议
- **消息广播**：新区块和交易传播
- **链同步**：最长链共识

### 💾 数据持久化
- **SQLite 数据库**：零配置，自动创建
- **自动保存**：区块、钱包、UTXO、交易自动持久化
- **重启恢复**：启动时自动加载历史数据

### 📊 可视化界面
- **区块链概览**：实时区块展示
- **钱包管理**：余额查看和创建
- **交易管理**：发起交易
- **挖矿控制**：启动/停止挖矿
- **网络监控**：节点状态查看

---

## 🚀 快速开始

### 环境要求
- Python 3.8+
- Flask 3.0+
- ecdsa 0.18+
- SQLite 3.0+（Python 内置）

### 安装依赖

```bash
pip install flask ecdsa
```

### 运行项目

```bash
python app.py
```

首次运行会自动创建 `ggcoin.db` 数据库文件，并初始化 3 个示例钱包。

### 访问界面

打开浏览器访问：http://localhost:5000

---

## 💾 数据持久化说明

### 数据库结构

系统使用 SQLite 数据库存储以下数据：

| 表名 | 说明 |
|------|------|
| `blocks` | 区块数据（索引、哈希、时间戳、交易等） |
| `wallets` | 钱包信息（名称、地址、公私钥、余额） |
| `utxos` | 未花费交易输出（UTXO） |
| `transactions` | 交易记录（含待处理交易） |

### 数据自动保存

- ✅ **挖矿**：新区块自动保存到数据库
- ✅ **创建钱包**：钱包信息自动保存
- ✅ **创建交易**：交易自动保存到待处理队列
- ✅ **UTXO 更新**：UTXO 变化自动同步

### 重启恢复

启动时系统会自动：
1. 从数据库加载所有区块
2. 恢复所有钱包
3. 恢复 UTXO 集合
4. 恢复待处理交易

**无需任何额外配置，数据永久保存！**

---

## 📖 API 接口

### 区块链
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/blockchain` | 获取完整区块链 |
| GET | `/api/block/<index>` | 获取指定区块 |

### 交易
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/transaction` | 创建交易 |
| GET | `/api/pending_transactions` | 获取待处理交易 |

### 挖矿
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/mine` | 挖一个区块 |
| POST | `/api/start_mining` | 启动持续挖矿 |
| POST | `/api/stop_mining` | 停止挖矿 |
| GET | `/api/mining_status` | 获取挖矿状态 |

### 钱包
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/wallets` | 获取所有钱包 |
| POST | `/api/create_wallet` | 创建新钱包 |

### 网络
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/start_network` | 启动 P2P 网络 |
| POST | `/api/stop_network` | 停止 P2P 网络 |
| POST | `/api/connect_peer` | 连接到对等节点 |
| GET | `/api/network` | 获取网络状态 |

---

## 🛠️ 核心模块说明

### 1. 密码学模块 (`src/crypto.py`)
- `sha256(data)` - SHA-256 哈希计算
- `double_sha256(data)` - 双重 SHA-256

### 2. 区块模块 (`src/block.py`)
- `Block` - 区块类
- `Blockchain` - 区块链类

### 3. 共识模块 (`src/consensus.py`)
- `ProofOfWork` - 工作量证明
- `DifficultyAdjuster` - 难度调整器

### 4. 交易模块 (`src/transaction.py`)
- `Transaction` - 交易类
- `TxInput` - 交易输入
- `TxOutput` - 交易输出
- `UTXOSet` - UTXO 集合

### 5. 钱包模块 (`src/wallet.py`)
- `Wallet` - 钱包类
- `KeyPair` - 密钥对工具

### 6. 网络模块 (`src/network.py`)
- `P2PNode` - P2P 节点
- `Message` - 网络消息
- `Peer` - 对等节点

### 7. 数据库模块 (`src/database.py`)
- `Database` - SQLite 数据库管理
- 自动初始化表结构
- 线程安全的数据操作

---

## 🎯 使用示例

### 创建钱包

```python
from src.wallet import Wallet

# 创建钱包
wallet = Wallet()
print(f"地址: {wallet.get_address()}")
print(f"公钥: {wallet.get_public_key_hex()}")
print(f"私钥: {wallet.get_private_key_hex()}")
```

### 创建交易

```python
from src.transaction import Transaction, TxInput, TxOutput

# 创建交易
tx = Transaction(
    inputs=[TxInput(txid="prev_tx_hash", vout=0)],
    outputs=[TxOutput(value=100, script_pubkey="recipient_address")]
)
print(f"交易ID: {tx.txid}")
```

### 挖矿

```python
from src.block import Blockchain
from src.consensus import ProofOfWork

# 创建区块链
blockchain = Blockchain()

# 创建 PoW 实例
pow = ProofOfWork(difficulty=4)

# 挖矿
block = pow.mine_block(blockchain, [{"from": "A", "to": "B", "amount": 10}])
blockchain.add_block(block)
```

### 数据库操作

```python
from src.database import Database

# 创建数据库实例（自动创建 ggcoin.db）
db = Database()

# 保存区块
db.save_block({
    'index': 1,
    'hash': '0x123...',
    'prev_hash': '0x000...',
    'timestamp': 1234567890,
    'nonce': 12345,
    'merkle_root': '0xabc...',
    'transactions': []
})

# 加载区块
blocks = db.load_blocks()
print(f"已加载 {len(blocks)} 个区块")
```

---

## 🔒 安全性说明

1. **密钥安全**：私钥应妥善保管，切勿泄露
2. **签名验证**：所有交易必须经过签名验证
3. **网络安全**：建议在安全网络环境下运行
4. **数据备份**：定期备份 `ggcoin.db` 数据库文件
5. **数据库安全**：SQLite 文件应设置适当的文件权限

---

## 📝 开发说明

### 代码规范
- 使用 Python 类型提示
- 遵循 PEP 8 代码规范
- 使用 docstring 文档化函数

### 测试建议
- 使用 `unittest` 进行单元测试
- 建议覆盖核心功能模块
- 测试挖矿功能时注意难度设置
- 验证数据库持久化功能

### 数据库管理

#### 查看数据库内容

```bash
# 使用 SQLite 命令行工具
sqlite3 ggcoin.db

# 查看所有表
.tables

# 查看区块数据
SELECT * FROM blocks;

# 查看钱包数据
SELECT * FROM wallets;

# 查看UTXO数据
SELECT * FROM utxos;

# 查看交易数据
SELECT * FROM transactions;
```

#### 清空数据库

```bash
# 删除数据库文件（下次启动会重新创建）
rm ggcoin.db
```

---

## 🐛 常见问题

### Q: 数据库文件在哪里？
A: 数据库文件 `ggcoin.db` 会自动创建在项目根目录下。

### Q: 如何重置所有数据？
A: 删除 `ggcoin.db` 文件，重启程序即可。

### Q: 数据会丢失吗？
A: 不会。所有数据都保存在 `ggcoin.db` 中，重启程序会自动加载。

### Q: 可以在其他机器上使用吗？
A: 可以。复制 `ggcoin.db` 文件到其他机器即可。

### Q: SQLite 够用吗？
A: 对于教学演示和小规模应用，SQLite 完全够用。如需生产环境，可迁移到 MySQL 或 PostgreSQL。

---

## 📄 许可证

MIT License

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

---

*Made with 🪙 by ggcoin Team*
