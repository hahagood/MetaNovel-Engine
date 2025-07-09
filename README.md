# MetaNovel-Engine

![Version](https://img.shields.io/badge/version-v0.0.14-blue.svg)
![Python](https://img.shields.io/badge/python-3.8+-green.svg)
![License](https://img.shields.io/badge/license-MIT-yellow.svg)

> **AI辅助小说创作引擎** - 结构化、分阶段的长篇小说创作工具

## 💡 为什么选择 MetaNovel-Engine？

- **🎯 省钱高效**：结构化创作流程，避免重复生成，大幅节省AI费用
- **📚 多项目管理**：同时创作多部小说，数据完全独立，不会混乱
- **🎨 个性化配置**：每个项目独立的AI提示词，科幻、言情、悬疑各有专属风格
- **🔄 渐进式创作**：从一句话想法到完整小说，7步骤层层递进，思路清晰
- **🌍 完整世界观**：角色、场景、道具统一管理，保持故事连贯性

## 🚀 5分钟快速开始

### 1. 安装运行
```bash
git clone https://github.com/hahagood/MetaNovel-Engine.git
cd MetaNovel-Engine
pip install -r requirements.txt
python meta_novel_cli.py
```

### 2. 配置API（首次使用）
将 `.env.example` 复制为 `.env`，填入你的OpenRouter API密钥：
```bash
cp .env.example .env
# 编辑 .env 文件，填入：OPENROUTER_API_KEY=your_api_key_here
```

### 3. 开始创作
运行程序后，选择"创建新项目"，按照7步流程开始你的小说创作之旅！

## 📝 创作流程：7步工作流

| 步骤 | 功能 | 用途 |
|------|------|------|
| 1️⃣ | **设置主题** | 确立一句话核心创意 |
| 2️⃣ | **扩展主题** | 发展为详细的故事概念 |
| 3️⃣ | **世界设定** | 创建角色、场景、道具 |
| 4️⃣ | **故事大纲** | 撰写500-800字的故事框架 |
| 5️⃣ | **分章细纲** | 分解为5-10个章节大纲 |
| 6️⃣ | **章节概要** | 每章300-500字详细概要 |
| 7️⃣ | **生成正文** | 生成2000-4000字完整章节 |

*每个步骤都可以查看、编辑和重新生成，确保创作质量*

## ⚙️ 核心功能

### 📁 项目管理
- 无限创建小说项目，数据完全隔离
- 快速切换不同项目，继续创作
- 自动备份，防止数据丢失

### 🎨 个性化AI
- 每个项目独立的提示词配置
- 针对不同题材调整AI创作风格
- 支持自定义AI模型和参数

### 📤 导出功能
- 支持单章节或整本小说导出
- 自动生成标准文本格式
- 可自定义导出路径

### 🔧 系统设置
- AI模型切换
- 网络代理配置
- 智能重试设置

## 🆘 常见问题

**Q: 需要什么API密钥？**
A: 需要OpenRouter的API密钥，支持多种AI模型，价格便宜。

**Q: 创作一部小说需要多少费用？**
A: 通过结构化流程，通常一部10万字小说的AI费用在10-30美元。

**Q: 支持中文创作吗？**
A: 完全支持中文，所有提示词都已优化为中文创作。

**Q: 旧版本数据如何迁移？**
A: 运行 `python migrate_to_multi_project.py` 即可自动迁移。

## 📄 开源协议

本项目采用 MIT License 开源协议。

## 🚀 开始创作

**准备好开始你的AI辅助小说创作之旅了吗？**

1. 克隆项目：`git clone https://github.com/hahagood/MetaNovel-Engine.git`
2. 安装依赖：`pip install -r requirements.txt`
3. 配置API密钥
4. 运行：`python meta_novel_cli.py`
5. 创建你的第一个项目！

---

**让AI成为你最好的创作伙伴！** ✨