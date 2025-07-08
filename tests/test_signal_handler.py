#!/usr/bin/env python3
"""
测试信号处理功能的脚本
"""

import time
import sys
import os

# 添加父目录到路径中以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from signal_handler import setup_graceful_exit, cleanup_graceful_exit
from ui_utils import ui, console

def test_signal_handling():
    """测试信号处理功能"""
    print("设置信号处理...")
    setup_graceful_exit()
    
    try:
        print("开始测试循环，请按 Ctrl+C 来测试退出功能...")
        print("(程序将在10秒后自动退出)")
        
        for i in range(10):
            console.print(f"测试循环 {i+1}/10 - 按 Ctrl+C 可以安全退出")
            time.sleep(1)
            
        print("测试循环完成")
        
    except KeyboardInterrupt:
        print("收到 KeyboardInterrupt，程序将正常退出")
        
    finally:
        cleanup_graceful_exit()
        print("信号处理器已清理")

if __name__ == "__main__":
    test_signal_handling()
