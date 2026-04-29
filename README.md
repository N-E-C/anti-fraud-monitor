# 客户自媒体反诈微舆情监测工具

> **Anti-Fraud Public Opinion Monitoring System**  
> 面向电信运营商反诈业务的客户自媒体舆情自动监测平台

[![Python](https://img.shields.io/badge/Python-3.9%2B-blue)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-微博%20%7C%20知乎%20%7C%20贴吧-orange)]()

---

## 📌 项目背景

电信运营商依托反诈模型对高风险号码实施关停管控。在此过程中，少量正常用户可能因模型误判被关停，进而在微博、知乎、贴吧、抖音、小红书等自媒体平台发表投诉言论，形成负面舆情。

同时，部分真实诈骗用户也可能通过舆论手段向运营商施压，试图借助舆情迫使恢复号码。

本工具旨在：

1. **自动监测**各主流自媒体平台的相关舆情内容
2. **智能分级**识别舆情风险等级与用户类型（正常误伤 vs 疑似施压）
3. **生成报表**辅助内部决策、关停时间核查、用户定位
4. **持续跟踪**形成长期舆情风险档案

---

## 🏗️ 项目结构

```
anti-fraud-monitor/
├── main.py                    # 程序入口（CLI）
├── requirements.txt           # 依赖包
├── .env.example               # 配置模板
├── config/
│   └── keywords.yaml          # 监测关键词配置（分级）
├── src/
│   ├── models.py              # 数据库模型
│   ├── scheduler.py           # 定时调度器
│   ├── crawler/               # 爬虫模块
│   │   ├── base.py            # 爬虫基类
│   │   ├── weibo.py           # 微博爬虫
│   │   ├── tieba.py           # 百度贴吧爬虫
│   │   ├── zhihu.py           # 知乎爬虫
│   │   └── manager.py         # 爬虫管理器（统一调度）
│   ├── analyzer/              # NLP 分析模块
│   │   └── sentiment.py       # 情感分析 + 风险评级
│   ├── reporter/              # 报表模块
│   │   └── excel_reporter.py  # Excel 报表生成
│   └── utils/
│       └── config.py          # 配置加载工具
├── data/                      # 数据库存储（自动创建）
├── reports/output/            # 报表输出目录（自动创建）
├── logs/                      # 日志目录（自动创建）
└── docs/
    └── 项目创新汇报.md         # 在岗革新创新项目汇报文档
```

---

## 🚀 快速开始

### 1. 环境准备

```bash
# 克隆项目
git clone https://github.com/YOUR_USERNAME/anti-fraud-monitor.git
cd anti-fraud-monitor

# 创建虚拟环境
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

```bash
# 复制配置模板
cp .env.example .env

# 编辑配置（填写 Cookie、监测频率等）
# WEIBO_COOKIE=...
# CRAWL_INTERVAL_MINUTES=60
```

### 3. 初始化数据库

```bash
python main.py initdb
```

### 4. 运行

```bash
# 启动持续监测（推荐，后台运行）
python main.py start

# 立即执行一次爬取
python main.py crawl

# 生成今日报表
python main.py report

# 生成指定日期报表
python main.py report --date 2026-04-28
```

---

## 📊 功能说明

### 监测平台

| 平台 | 爬虫状态 | 备注 |
|------|---------|------|
| 微博 | ✅ 已实现 | 需配置 Cookie |
| 百度贴吧 | ✅ 已实现 | 无需 Cookie |
| 知乎 | ✅ 已实现 | 需配置 Cookie |
| 抖音 | 🚧 规划中 | 需第三方接口 |
| 小红书 | 🚧 规划中 | 反爬较强 |
| B站 | 🚧 规划中 | |

### 风险分级

| 等级 | 标志 | 触发条件 |
|------|------|---------|
| 🔴 高风险 | HIGH | 命中高风险词 + 强负面情感 + 高传播 |
| 🟡 中风险 | MEDIUM | 命中中风险词 或 负面情感 |
| 🟢 低风险 | LOW | 中性提及 |

### 用户类型识别

| 类型 | 判定逻辑 |
|------|---------|
| 正常误伤投诉 | 情感偏负面、有诉求，无施压特征 |
| 疑似诈骗用户施压 | 命中施压模式词（集体投诉/联合施压/曝光运营商等）|
| 待核查 | 暂不能判定，需人工复核 |

### 报表内容

每日 Excel 报表包含 4 个工作表：
- **综合概览**：汇总数据 + 平台分布
- **高风险明细**：当日高风险帖子详情
- **全量数据**：所有监测记录
- **用户核查清单**：帖子中出现的手机号汇总，供内部核查关停时间

---

## ⚙️ 关键词配置

编辑 `config/keywords.yaml` 自定义监测关键词：

```yaml
keywords:
  high_risk:        # 高风险词（直接投诉/维权）
    - "中国移动封号"
    - "反诈误封"
    ...
  medium_risk:      # 中风险词（质疑/不满）
    - "停机"
    ...
  neutral:          # 中性监测词
    - "反诈中心"
    ...
```

---

## 🔐 隐私与合规

- 本工具仅抓取**平台公开内容**（公开帖子/评论），不涉及私信等非公开数据
- 手机号等个人信息采用**脱敏存储**原则
- 数据仅用于**公司内部舆情研判**，不对外共享
- 运营时请遵守各平台服务协议及相关法律法规

---

## 🗂️ 版本计划

| 版本 | 状态 | 主要功能 |
|------|------|---------|
| v1.0 | ✅ 当前 | 微博/知乎/贴吧监测 + Excel报表 |
| v1.1 | 🚧 规划 | 抖音/小红书接入 + 邮件告警 |
| v1.2 | 🚧 规划 | Web 可视化 Dashboard |
| v2.0 | 📅 远期 | 接入大模型（MiMo）自动生成舆情简报 |

---

## 🤝 贡献

欢迎提交 Issue 和 Pull Request。

---

## 📄 License

MIT License — 详见 [LICENSE](LICENSE)
