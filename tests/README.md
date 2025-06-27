# MetaNovel-Engine 测试系统

## 概述

本测试系统为MetaNovel-Engine提供全面的单元测试覆盖，确保代码质量和功能稳定性。

## 测试结构

```
tests/
├── __init__.py              # 测试包初始化
├── test_config.py           # 配置模块测试
├── test_data_manager.py     # 数据管理模块测试
├── test_entity_manager.py   # 实体管理模块测试
├── test_llm_service.py      # LLM服务模块测试
└── README.md               # 本文档
```

## 运行测试

### 运行所有测试

```bash
python run_tests.py
```

### 运行特定测试模块

```bash
python run_tests.py test_data_manager
python run_tests.py test_llm_service
python run_tests.py test_entity_manager
python run_tests.py test_config
```

### 使用unittest直接运行

```bash
# 运行所有测试
python -m unittest discover tests

# 运行特定测试文件
python -m unittest tests.test_data_manager

# 运行特定测试类
python -m unittest tests.test_data_manager.TestDataManager

# 运行特定测试方法
python -m unittest tests.test_data_manager.TestDataManager.test_character_operations
```

## 测试覆盖范围

### test_config.py
- 配置结构验证
- 配置值类型检查
- 配置合理性验证
- 代理设置测试

### test_data_manager.py
- 文件读写操作
- CRUD操作（角色、场景、道具）
- 备份功能
- 前置条件检查
- 错误处理

### test_entity_manager.py
- 实体配置创建
- 通用CRUD界面逻辑
- 菜单选项生成
- 用户交互模拟
- 预定义配置验证

### test_llm_service.py
- 提示词加载和格式化
- AI客户端初始化
- 同步和异步请求
- 批量生成功能
- 错误处理和后备机制

## 测试最佳实践

1. **使用Mock**: 所有外部依赖都通过Mock模拟，确保测试的独立性
2. **临时文件**: 使用临时目录和文件，测试后自动清理
3. **异步测试**: 使用`unittest.IsolatedAsyncioTestCase`测试异步功能
4. **错误覆盖**: 测试正常流程和异常情况
5. **完整清理**: 每个测试后恢复初始状态

## 添加新测试

当添加新功能时，请按以下步骤添加相应测试：

1. 在适当的测试文件中添加测试方法
2. 使用描述性的测试方法名
3. 包含必要的Mock和断言
4. 测试正常和异常情况
5. 确保测试独立且可重复

## 测试依赖

测试系统使用Python标准库的`unittest`框架，无需额外依赖。主要使用的测试工具：

- `unittest.TestCase`: 基础测试类
- `unittest.mock`: Mock对象和补丁
- `tempfile`: 临时文件和目录
- `unittest.IsolatedAsyncioTestCase`: 异步测试支持

## 持续集成

测试系统设计为可集成到CI/CD流程中：

- 返回标准退出码（0=成功，1=失败）
- 提供详细的测试输出
- 支持单独运行测试模块
- 无外部依赖，易于在不同环境中运行 