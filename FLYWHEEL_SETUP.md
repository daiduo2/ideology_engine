# Flywheel 自动化配置指南

本仓库已集成 **Flywheel** 自动化系统，用于 AI 驱动的代码自修复。

## 功能特性

- **代码扫描**: 自动扫描代码库，识别 Bug、安全问题和优化机会
- **并行修复候选**: 每个 Issue 生成 3 路并行修复候选
- **AI 仲裁合并**: 自动选择最优候选并合并
- **监控看板**: 每日自动化健康报告

## 触发方式

### 自动触发

| Workflow | 触发时间 | 说明 |
|---------|---------|------|
| `flywheel-orchestrator.yml` | 每 6 小时 (2:00, 8:00, 14:00, 20:00 UTC) | 主飞轮工作流 |
| `automation-metrics.yml` | 每日 3:00 UTC | 健康指标报告 |

### 手动触发

```bash
# 触发完整飞轮
gh workflow run flywheel-orchestrator.yml

# 触发带参数的飞轮
gh workflow run flywheel-orchestrator.yml \
  -f max_issues=3 \
  -f candidate_quality_min_score=75

# 查看指标报告
gh workflow run automation-metrics.yml
```

## 必要配置

### 1. 设置 Secrets

在 GitHub 仓库 Settings → Secrets and variables → Actions 中添加：

| Secret | 说明 | 获取方式 |
|--------|------|---------|
| `ANTHROPIC_AUTH_TOKEN` | Claude API 密钥 | [Anthropic Console](https://console.anthropic.com/) |
| `ANTHROPIC_BASE_URL` | API 基础 URL (可选) | 默认: https://api.anthropic.com |
| `ANTHROPIC_MODEL` | 使用的模型 (可选) | 如: claude-opus-4-6 |

### 2. 配置仓库保护规则

Settings → Branches → Add rule:
- Branch name pattern: `master`
- ✅ Require a pull request before merging
- ✅ Require status checks to pass before merging
- Status checks: `quality`, `test`

### 3. 启用 Discussions (可选)

Settings → Discussions → Enable
用于接收每日自动化健康报告

## 成本优化

当前配置已优化以降低成本：

| 配置项 | 原设置 | 当前设置 | 节省 |
|--------|--------|---------|------|
| 触发频率 | 每小时 | 每 6 小时 | 83% |
| 候选并行度 | 3 路 | 3 路 | - |
| 质量门阈值 | 70 | 70 | - |

如需进一步降低成本，可修改 `.github/workflows/flywheel-orchestrator.yml`：

```yaml
# 改为每日两次
cron: "0 2,14 * * *"

# 或减少候选数量 (需同步修改 matrix.candidate_id)
candidate_id: [1, 2]  # 从 [1, 2, 3] 改为 [1, 2]
```

## 工作流程

```
┌─────────────────┐
│ Circuit Breaker │ 熔断保护（连续失败 3 次后冷却 120 分钟）
└────────┬────────┘
         ▼
┌─────────────────┐
│      Scan       │ 代码扫描，创建 Issue
└────────┬────────┘
         ▼
┌─────────────────┐
│    Evaluate     │ 评估 Issue 优先级
└────────┬────────┘
         ▼
┌─────────────────┐
│  Select Issue   │ 选择待修复 Issue
└────────┬────────┘
         ▼
┌─────────────────┐
│Generate Candidate│ 并行生成 3 路修复候选 PR
└────────┬────────┘
         ▼
┌─────────────────┐
│      Merge      │ AI 仲裁，选择最优合并
└────────┬────────┘
         ▼
┌─────────────────┐
│    Curation     │ Issue 整理与归档
└─────────────────┘
```

## 监控与故障排查

### 查看运行状态

```bash
# 查看最新运行
gh run list --workflow=flywheel-orchestrator.yml

# 查看特定运行日志
gh run view <run-id> --log

# 查看候选 PR 数量
gh pr list --search "[AUTOFIX]" --state open | wc -l
```

### 常见问题

| 问题 | 解决方案 |
|------|---------|
| Workflow 不触发 | 检查 Secrets 是否配置正确 |
| 候选 PR 质量低 | 提高 `candidate_quality_min_score` |
| API 费用过高 | 降低触发频率或减少候选并行度 |
| 合并失败 | 检查分支保护规则是否冲突 |

## 文档

- `.github/FLYWHEEL.md` - 完整飞轮策略文档
- `docs/runbook.md` - 运行与故障处置手册
- `AGENTS_FLYWHEEL.md` - AI Agent 配置指南

## 许可证

与原仓库保持一致
