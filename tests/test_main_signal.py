#!/usr/bin/env python3
"""
测试主程序的信号处理功能
"""

import time
import sys
import os
import signal
import subprocess
import threading

# 添加父目录到路径中以便导入模块
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def test_main_signal_handling():
    """测试主程序的信号处理功能"""
    print("启动主程序进行信号处理测试...")
    
    # 启动主程序
    process = subprocess.Popen(
        [sys.executable, "meta_novel_cli.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        preexec_fn=os.setsid  # 创建新的进程组
    )
    
    def send_interrupt():
        """日后发送中断信号"""
        time.sleep(2)
        print("发送 SIGINT 信号...")
        try:
            os.killpg(os.getpgid(process.pid), signal.SIGINT)
        except ProcessLookupError:
            print("进程已经结束")
    
    # 在另一个线程中发送中断信号
    interrupt_thread = threading.Thread(target=send_interrupt)
    interrupt_thread.start()
    
    # 等待进程结束
    try:
        stdout, stderr = process.communicate(timeout=10)
        print("程序输出:")
        print(stdout)
        if stderr:
            print("错误输出:")
            print(stderr)
        print(f"退出代码: {process.returncode}")
        
        if "感谢使用 MetaNovel Engine" in stdout:
            print("✅ 测试成功：程序显示了正确的退出界面")
        else:
            print("❌ 测试失败：程序没有显示预期的退出界面")
            
    except subprocess.TimeoutExpired:
        print("❌ 测试超时：程序没有在预期时间内退出")
        os.killpg(os.getpgid(process.pid), signal.SIGKILL)
    except EOFError:
        print("❌ 测试失败：由EOFError中断")
    
    interrupt_thread.join()

if __name__ == "__main__":
    test_main_signal_handling()
