# 如何将项目上传到 GitHub

## 前提条件

1. 本地已安装 [Git](https://git-scm.com/)
2. 已注册 GitHub 账号
3. 已在 GitHub 创建空仓库（如 `anti-fraud-monitor`）

---

## 步骤

### 第一步：在 GitHub 创建仓库

1. 登录 https://github.com
2. 点击右上角 **New repository**
3. 仓库名：`anti-fraud-monitor`
4. 描述：`客户自媒体反诈微舆情监测工具 - China Mobile Ningxia`
5. 选择 **Public**（供小米 Token 计划审核）
6. **不要**勾选 Initialize README（本地已有）
7. 点击 **Create repository**

---

### 第二步：本地初始化并推送

打开 PowerShell，进入项目目录执行：

```powershell
cd C:\Users\71486\WorkBuddy\20260429123956\anti-fraud-monitor

# 初始化 git
git init

# 配置用户信息（首次使用）
git config user.name "你的名字"
git config user.email "你的邮箱@example.com"

# 添加所有文件
git add .

# 首次提交
git commit -m "feat: 初始化客户自媒体反诈微舆情监测工具框架"

# 关联远程仓库（替换 YOUR_USERNAME）
git remote add origin https://github.com/YOUR_USERNAME/anti-fraud-monitor.git

# 推送
git branch -M main
git push -u origin main
```

---

### 第三步：添加 GitHub Topics（有利于小米 Token 计划发现）

推送完成后，在仓库页面点击 **⚙ Settings → Topics**，添加：

```
anti-fraud  sentiment-analysis  china-mobile  nlp  python  telecom
```

---

### 第四步：提交小米 MiMo Token 计划

访问小米 Token 计划官网，填写：
- 项目名称：客户自媒体反诈微舆情监测工具
- GitHub 地址：https://github.com/YOUR_USERNAME/anti-fraud-monitor
- 项目描述：面向电信运营商反诈业务的自媒体舆情自动监测系统，支持微博/知乎/贴吧等平台，后续将接入 MiMo 大模型实现舆情智能简报生成

---

## 后续更新流程

```powershell
# 每次修改后
git add .
git commit -m "feat/fix/docs: 简要描述改动"
git push
```
