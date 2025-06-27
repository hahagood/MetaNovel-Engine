#!/usr/bin/env python3
"""
Test runner for MetaNovel-Engine

This script runs all unit tests and provides a summary report.
"""

import unittest
import sys
import os

# Add current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def run_tests():
    """运行所有测试"""
    # 发现并加载所有测试
    loader = unittest.TestLoader()
    start_dir = 'tests'
    suite = loader.discover(start_dir, pattern='test_*.py')
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 返回测试结果
    return result.wasSuccessful()

def run_specific_test(test_module):
    """运行特定的测试模块"""
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromName(f'tests.{test_module}')
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result.wasSuccessful()

if __name__ == '__main__':
    print("MetaNovel-Engine 测试套件")
    print("=" * 50)
    
    if len(sys.argv) > 1:
        # 运行特定测试模块
        test_module = sys.argv[1]
        print(f"运行测试模块: {test_module}")
        success = run_specific_test(test_module)
    else:
        # 运行所有测试
        print("运行所有测试...")
        success = run_tests()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ 所有测试通过！")
        sys.exit(0)
    else:
        print("❌ 测试失败！")
        sys.exit(1) 