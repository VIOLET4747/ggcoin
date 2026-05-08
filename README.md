# ggcoin - 极简区块链系统

[![Python Version](https://img.shields.io/badge/python-3.8%2B-blue.svg)](https://www.python.org/)
[![Flask Version](https://img.shields.io/badge/flask-3.0%2B-green.svg)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/sqlite-3.0%2B-orange.svg)](https://www.sqlite.org/)

ggcoin 是一个用 Python 实现的极简区块链系统，包含完整的核心功能：工作量证明（PoW）、UTXO 交易模型、ECDSA 数字签名钱包。支持 SQLite 数据库持久化，数据自动保存，重启不丢失。提供 Web 可视化界面，便于教学演示和快速体验。

---

## 项目结构

```
ggcoin/
├── src/                       # 核心源代码
│   ├── __init__.py            # 模块初始化
│   ├── crypto.py              # SHA-256 哈希函数
│   ├── block.py               # 区块和区块链数据结构
│   ├── consensus.py           # PoW 共识机制和难度调整
│   ├── transaction.py         # 交易结构和 UTXO 模型
│   ├── wallet.py              # ECDSA 钱包和数字签名
│   ├── merkle_tree.py         # 默克尔树实现
│   └── database.py            # SQLite 数据库持久化
├── templates/
│   └── index.html             # Web 可视化管理界面
├── app.py                     # Flask Web 应用入口
├── ggcoin.db                  # SQLite 数据库文件（自动生成）
├── .gitignore                 # Git 忽略文件
└── README.md                  # 项目文档
```

---

## 功能特性

### 核心数据结构
- **区块结构**：包含索引、时间戳、交易列表、前区块哈希、Nonce、默克尔根
- **区块链**：链式存储、完整性验证、创世区块自动创建
- **默克尔树**：交易数据摘要、快速验证交易完整性

### 共识机制
- **工作量证明（PoW）**：SHA-256 哈希挖矿，动态调整 nonce 值
- **动态难度调整**：根据网络算力自动调整挖矿难度
- **挖矿奖励**：每个区块固定奖励 50 GGC

### 交易系统
- **UTXO 模型**：未花费交易输出管理
- **交易验证**：输入输出平衡检查

### 钱包管理
- **密钥生成**：SECP256k1 椭圆曲线密钥对
- **地址生成**：公钥哈希地址
- **签名/验证**：ECDSA 数字签名

### 数据持久化
- **SQLite 数据库**：零配置，自动创建，无需额外服务
- **自动保存**：区块、钱包、UTXO、交易自动持久化
- **重启恢复**：启动时自动加载历史数据

### 可视化界面
- **区块链概览**：实时区块展示和统计数据
- **钱包管理**：余额查看和钱包创建
- **交易管理**：发起交易
- **挖矿控制**：单步挖矿、持续挖矿、快速批量挖矿
- **系统管理**：重置数据库、导出数据、查看系统信息

---

## 快速开始

### 环境要求
- Python 3.8+
- Flask 3.0+
- ecdsa 0.18+

### 安装依赖

```bash
pip install flask ecdsa
```

### 运行项目

```bash
python app.py
```

首次运行会自动创建 `ggcoin.db` 数据库文件，并初始化 3 个示例钱包（余额分别为 100、150、200 GGC）。

### 访问界面

打开浏览器访问：http://localhost:5000

---

## Web 界面使用说明

### 1. 区块链概览
- 查看区块高度、待处理交易数、钱包数量、总供应量等统计数据
- 浏览所有区块的详细信息（哈希、交易数、Nonce、时间戳）

### 2. 钱包管理
- 查看所有钱包的名称、地址和余额
- 创建新钱包

### 3. 交易管理
- 选择发送方钱包，输入接收方地址和金额
- 创建交易（交易会进入待处理队列，等待挖矿确认）

### 4. 挖矿控制
- **挖一个区块**：手动挖一个区块，打包待处理交易
- **开始挖矿**：启动持续自动挖矿
- **快速挖矿**：一次性批量挖掘指定数量的区块，快速推进区块链

### 5. 系统管理
- **重置数据库**：清空所有数据，恢复到初始状态
- **导出数据**：将区块链和钱包数据导出为 JSON 文件
- **查看日志**：查看系统运行日志
- **系统信息**：版本、数据库类型、共识机制等

---

## 数据库持久化

### 数据库结构

| 表名 | 说明 |
|------|------|
| `blocks` | 区块数据（索引、哈希、时间戳、Nonce、交易列表） |
| `wallets` | 钱包信息（名称、地址、公私钥） |
| `utxos` | 未花费交易输出（交易ID、输出索引、金额、地址） |
| `transactions` | 交易记录（交易ID、发送方、接收方、金额、状态） |

### 数据自动保存

- 挖矿产生的新区块自动保存
- 创建的钱包信息自动保存
- 交易自动保存到待处理队列
- UTXO 变化自动同步

### 重启恢复

启动时系统会自动从数据库加载所有数据，无需任何额外配置。

---

## API 接口

### 区块链
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/blockchain` | 获取完整区块链 |
| GET | `/api/block/<index>` | 获取指定区块 |

### 交易
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/transaction` | 创建交易 |
| GET | `/api/pending_transactions` | 获取待处理交易列表 |
| GET | `/api/utxo` | 获取 UTXO 集合 |

### 挖矿
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/mine` | 挖一个区块 |
| POST | `/api/start_mining` | 启动持续挖矿 |
| POST | `/api/stop_mining` | 停止挖矿 |
| GET | `/api/mining_status` | 获取挖矿状态 |
| POST | `/api/quick_mine` | 快速批量挖矿 |
| GET | `/api/mining_rewards` | 获取挖矿收益记录 |

### 钱包
| 方法 | 路径 | 描述 |
|------|------|------|
| GET | `/api/wallets` | 获取所有钱包 |
| POST | `/api/create_wallet` | 创建新钱包 |

### 系统管理
| 方法 | 路径 | 描述 |
|------|------|------|
| POST | `/api/reset_database` | 重置数据库 |
| GET | `/api/export_data` | 导出数据为 JSON |

---

## 核心模块说明

### 1. 密码学模块 (`src/crypto.py`)
- `sha256(data)` - SHA-256 哈希计算，支持字符串、字典、字节数据
- `double_sha256(data)` - 双重 SHA-256 哈希

### 2. 区块模块 (`src/block.py`)
- `Block` - 区块类，包含计算哈希、计算默克尔根方法
- `Blockchain` - 区块链类，支持添加区块、链验证

### 3. 共识模块 (`src/consensus.py`)
- `ProofOfWork` - 工作量证明，通过调整 nonce 寻找有效哈希
- `DifficultyAdjuster` - 难度调整器，根据出块时间动态调整

### 4. 交易模块 (`src/transaction.py`)
- `Transaction` - 交易类，自动计算 txid
- `TxInput` - 交易输入，引用前一笔交易的输出
- `TxOutput` - 交易输出，包含金额和接收地址
- `UTXOSet` - UTXO 集合管理，支持添加、移除、查询

### 5. 钱包模块 (`src/wallet.py`)
- `Wallet` - 钱包类，支持密钥生成、地址生成、签名验证
- `KeyPair` - 密钥对工具类，提供静态方法

### 6. 数据库模块 (`src/database.py`)
- `Database` - SQLite 数据库管理，自动初始化表结构
- 线程安全的数据读写操作

---

## 使用示例

### 创建钱包

```python
from src.wallet import Wallet

wallet = Wallet()
print(f"地址: {wallet.get_address()}")
print(f"公钥: {wallet.get_public_key_hex()}")
print(f"私钥: {wallet.get_private_key_hex()}")
```

### 创建交易

```python
from src.transaction import Transaction, TxInput, TxOutput

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

blockchain = Blockchain()
pow = ProofOfWork(difficulty=4)

block = pow.mine_block(blockchain, [{"from": "A", "to": "B", "amount": 10}])
blockchain.add_block(block)
```

---

## 数据库管理

### 查看数据库内容

```bash
sqlite3 ggcoin.db

.tables                     # 查看所有表
SELECT * FROM blocks;       # 查看区块数据
SELECT * FROM wallets;      # 查看钱包数据
SELECT * FROM utxos;        # 查看 UTXO 数据
SELECT * FROM transactions; # 查看交易数据

.quit                       # 退出
```

### 重置数据

通过 Web 界面的「系统管理 -> 重置数据库」功能，或直接删除 `ggcoin.db` 文件后重启程序。

---

## 常见问题

### Q: 数据库文件在哪里？
A: 数据库文件 `ggcoin.db` 会自动创建在项目根目录下。

### Q: 如何重置所有数据？
A: 通过 Web 界面的「系统管理 -> 重置数据库」功能，或删除 `ggcoin.db` 文件后重启。

### Q: 数据会丢失吗？
A: 不会。所有数据保存在 `ggcoin.db` 中，重启程序会自动加载。

### Q: 如何备份数据？
A: 复制 `ggcoin.db` 文件即可，也可以通过「系统管理 -> 导出数据」导出为 JSON。

### Q: 可以在其他机器上使用吗？
A: 可以。复制 `ggcoin.db` 文件到其他机器即可恢复数据。

### Q: 挖矿太慢怎么办？
A: 使用「快速挖矿」功能可以一次性批量挖掘多个区块。

---

## 安全提示

1. **私钥安全**：私钥应妥善保管，切勿泄露
2. **数据备份**：定期备份 `ggcoin.db` 数据库文件
3. **权限设置**：`ggcoin.db` 文件应设置适当的文件权限
4. **网络端口**：默认监听 5000 端口，生产环境建议使用反向代理

---

## 许可证

MIT License

---

## 贡献

欢迎提交 Issue 和 Pull Request！
