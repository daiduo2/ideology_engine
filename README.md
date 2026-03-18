# Ideology Engine | 意识形态引擎

自然语言驱动的智能测评引擎，支持 MBTI、DISC 等人格与能力评估协议。

> 基于大语言模型的对话式测评，告别固定问卷，实现真正的个性化评估。

## 特性

- 🧠 **智能对话**: 根据用户回答动态生成问题，而非固定问卷
- ⚡ **并行优化**: 证据提取与问题生成并行执行，响应速度提升 50%+
- 🎯 **多协议支持**: 内置 MBTI、DISC、沟通风格、领导力等测评协议
- 🔌 **多模型兼容**: 支持 Anthropic、OpenAI、Kimi 等兼容 OpenAI 协议的 API
- 💾 **状态持久化**: 会话状态自动保存，支持断点续评
- 🌐 **REST API**: 完整的 HTTP API，易于集成到现有系统

## 快速开始

### 1. 环境要求

- Python 3.9+
- 支持 UTF-8 的终端（推荐使用 iTerm2、Tabby 等现代终端）

### 2. 安装

```bash
# 克隆仓库
git clone https://github.com/daiduo2/ideology_engine.git
cd ideology_engine

# 安装依赖
pip install -e .

# 安装输入增强（可选，提供更好输入体验）
pip install prompt_toolkit
```

### 3. 配置 API Key

**方式一：环境变量（推荐）**

```bash
export ANTHROPIC_API_KEY="your-api-key"
export ANTHROPIC_BASE_URL="https://api.anthropic.com"  # 可选，使用第三方API时修改
```

**方式二：直接修改代码**

编辑 `demo_mbti_optimized.py` 或 `demo_mbti_fast.py`：

```python
# 文件开头修改以下配置
API_KEY = "your-api-key"
BASE_URL = "https://api.kimi.com/coding/"  # 使用 Kimi 时
```

### 4. 运行测评

**优化版（推荐）**
```bash
python demo_mbti_optimized.py
```
- 合并解析+提取：单次 LLM 调用
- 预生成问题：零等待获取下一题
- 智能缓存：相似回答复用结果

**并行版**
```bash
python demo_mbti_fast.py
```
- 证据提取与问题生成并行执行

**基础版**
```bash
python demo_mbti.py
```
- 串行处理，适合理解原理

## 支持的 LLM 提供商

| 提供商 | BASE_URL | 说明 |
|--------|----------|------|
| Anthropic | `https://api.anthropic.com` | 官方 API |
| Kimi | `https://api.kimi.com/coding/` | 国内可用 |
| 其他 OpenAI 兼容 | 自定义 | 如 OpenRouter、LocalAI 等 |

## 项目结构

```
ideology_engine/
├── demo_mbti_optimized.py      # 优化版 Demo（推荐）
├── demo_mbti_fast.py           # 并行处理版
├── demo_mbti.py                # 基础版
├── run_api.py                  # REST API 服务端
├── protocols/                  # 测评协议定义
│   └── mbti-assessment.json
├── src/assessment_engine/
│   ├── core/                   # 核心模型
│   │   ├── protocol.py         # 协议定义
│   │   ├── session.py          # 会话管理
│   │   └── state.py            # 状态管理
│   ├── engine/                 # 测评引擎
│   │   ├── optimized_parallel_engine.py  # 优化引擎
│   │   ├── parallel_engine.py            # 并行引擎
│   │   ├── state_updater.py              # 状态更新
│   │   └── probe_planner.py              # 问题规划
│   ├── llm/                    # LLM 集成
│   │   ├── config.py           # 配置
│   │   ├── factory.py          # 客户端工厂
│   │   └── providers/          # 各厂商实现
│   └── api/                    # REST API
├── tests/                      # 测试用例
└── sessions/                   # 会话存储（自动生成）
```

## 内置测评协议

### MBTI 人格测评
```bash
python demo_mbti_optimized.py
```
- 评估四个维度：E/I、S/N、T/F、J/P
- 8 轮对话，动态问题生成
- 输出 16 型人格结果及置信度

### 其他协议（通过 REST API）

启动 API 服务：
```bash
python run_api.py
# 或
uvicorn run_api:app --reload
```

创建 MBTI 测评会话：
```bash
curl -X POST http://localhost:8000/sessions \
  -H "Content-Type: application/json" \
  -d '{"protocol_id": "mbti-assessment"}'
```

获取下一题：
```bash
curl http://localhost:8000/sessions/{session_id}/next-question
```

提交回答：
```bash
curl -X POST http://localhost:8000/sessions/{session_id}/answers \
  -H "Content-Type: application/json" \
  -d '{"answer": "我喜欢和朋友们一起度过周末"}'
```

生成报告：
```bash
curl http://localhost:8000/sessions/{session_id}/report
```

## 常见问题

### 1. 响应速度慢

**现象**: 每轮需要 10-30 秒

**原因**: LLM API 响应慢（特别是复杂解析任务）

**优化**:
- 使用 `demo_mbti_optimized.py`（已合并调用）
- 考虑使用更快的模型（如 claude-3-5-sonnet 代替 opus）
- 启用缓存（相同回答自动复用）

### 2. 输入中文乱码

**现象**: 输入中文显示为乱码或报错

**解决**:
- 确保终端编码为 UTF-8
- macOS/Linux: `export LANG=en_US.UTF-8`
- 安装 `prompt_toolkit` 获得最佳体验

### 3. API 连接失败

**现象**: "连接失败" 或超时

**检查**:
- API Key 是否正确设置
- BASE_URL 是否正确（注意末尾斜杠）
- 网络是否能访问该 API

### 4. 并发限制

**现象**: 后台证据处理等待很久

**说明**: 这是预期行为。引擎在等待你的输入期间并行处理证据，
如果你输入很快，就会看到"等待后台证据处理"的提示。

## 开发

### 运行测试
```bash
python -m pytest tests/ -v
```

### 添加新测评协议

1. 在 `protocols/` 目录创建 JSON 文件
2. 参考 `protocols/mbti-assessment.json` 格式
3. 定义维度、量表、覆盖目标、停止规则

## 技术架构

```
┌─────────────────────────────────────────┐
│              用户界面层                  │
│    (demo / REST API / Web Frontend)     │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              引擎层                      │
│  ┌──────────────┐    ┌──────────────┐  │
│  │ 问题规划器    │    │ 状态更新器    │  │
│  │ProbePlanner  │    │StateUpdater  │  │
│  └──────────────┘    └──────────────┘  │
│  ┌──────────────────────────────────┐  │
│  │    并行执行器 (Parallel Engine)   │  │
│  │  ┌──────────┐    ┌──────────┐   │  │
│  │  │证据提取  │◄──►│问题生成  │   │  │
│  │  │(后台)    │    │(即时)    │   │  │
│  │  └──────────┘    └──────────┘   │  │
│  └──────────────────────────────────┘  │
└──────────────────┬──────────────────────┘
                   │
┌──────────────────▼──────────────────────┐
│              LLM 适配层                  │
│    (Anthropic / OpenAI / Kimi ...)      │
└─────────────────────────────────────────┘
```

## 贡献

欢迎提交 Issue 和 PR！

## 许可

MIT License

---

> 本项目仅供学习和研究使用。测评结果仅供参考，不构成专业心理诊断。
