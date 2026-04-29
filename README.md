# 客户自媒体反诈微舆情监测工具

> 面向电信运营商反诈业务的客户自媒体舆情自动监测平台

## 项目背景

电信运营商通过反诈模型对高风险号码实施关停管控，但存在两个问题：
1. 部分正常用户因模型误判被关停，在自媒体平台投诉形成负面舆情
2. 真实诈骗用户可能利用舆论手段向运营商施压

本工具实现对主流自媒体平台相关舆情的自动监测、智能分级和报表生成，辅助内部研判。

## 功能概述

### 监测平台

| 平台 | 状态 | 说明 |
|------|------|------|
| 微博 | ✅ 已实现 | 需配置Cookie |
| 知乎 | ✅ 已实现 | 需配置Cookie |
| 百度贴吧 | ✅ 已实现 | 无需Cookie |
| 抖音 | 🚧 框架 | 需接入第三方数据源或开放平台 |
| 小红书 | 🚧 框架 | 反爬较强，建议走第三方接口 |
| 快手 | 🚧 框架 | 需配置数据源 |

### 风险分级

- **高风险** 🔴：直接投诉/提及工信部/维权施压
- **中风险** 🟡：质疑停机原因/表达不满
- **低风险** 🟢：中性提及

分级逻辑：关键词命中权重 + SnowNLP情感分析 + 传播量 + 施压模式识别

### 用户类型识别

- 正常误伤投诉：情感偏负面，有合理诉求
- 疑似诈骗施压：命中"集体投诉"/"联合施压"/"曝光运营商"等特征模式

## 快速开始

### 环境准备

```bash
git clone https://github.com/N-E-C/anti-fraud-monitor.git
cd anti-fraud-monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 配置

```bash
cp .env.example .env
# 编辑 .env 填入平台Cookie等配置
```

关键词配置在 `config/keywords.yaml`，按需调整。

### 运行

```bash
python main.py initdb                    # 初始化数据库
python main.py crawl                     # 执行一次爬取测试
python main.py start                     # 启动定时调度（持续监测）
python main.py report --date 2026-04-30  # 生成指定日期报表
```

## 项目结构

```
├── main.py                    # CLI入口
├── config/keywords.yaml       # 关键词配置
├── src/
│   ├── models.py              # 数据库模型（SQLAlchemy）
│   ├── scheduler.py           # 定时调度（APScheduler）
│   ├── crawler/               # 爬虫模块
│   │   ├── base.py            # 基类定义
│   │   ├── manager.py         # 爬虫管理器
│   │   ├── weibo.py           # 微博
│   │   ├── zhihu.py           # 知乎
│   │   └── tieba.py           # 贴吧
│   ├── analyzer/
│   │   └── sentiment.py       # 情感分析 + 风险评级
│   ├── reporter/
│   │   └── excel_reporter.py  # Excel报表生成
│   └── utils/
│       └── config.py          # 配置加载
└── reports/output/            # 报表输出目录
```

## 报表说明

每日自动生成Excel报表，包含4个工作表：
- 综合概览：汇总统计 + 平台分布
- 高风险明细：当日高风险内容详情
- 全量数据：完整监测记录
- 用户核查清单：提取的手机号，供内部核查关停时间

## 关于新平台扩展

抖音/小红书/快手的爬虫框架已预留，但这些平台反爬机制较强，无公开搜索API。接入方案：
1. 第三方数据平台接口（蝉妈妈、飞瓜等，需付费）
2. 官方开放平台申请（需企业资质，门槛较高）
3. RSS订阅或关键词监控服务

根据实际需求和预算选择合适的接入方式。

## 注意事项

- 仅抓取平台公开内容，不涉及私信等非公开数据
- 手机号等敏感信息脱敏存储
- 数据仅供内部研判使用
- 运行时注意控制抓取频率，避免触发反爬

## 后续规划

- [ ] 邮件告警（高风险内容自动推送）
- [ ] Web可视化Dashboard
- [ ] 接入大模型生成舆情简报
- [ ] 更多数据源接入

## License

MIT
