"""
信号处理模块 - 处理Ctrl+C中断信号，实现优雅退出
"""

import signal
import sys
from ui_utils import ui, console
from rich.panel import Panel
from rich.text import Text

class GracefulExit:
    """优雅退出处理器"""
    
    def __init__(self):
        self.exit_requested = False
        self.original_handler = None
    
    def setup_signal_handler(self):
        """设置信号处理器"""
        # 保存原始的信号处理器
        self.original_handler = signal.signal(signal.SIGINT, self._signal_handler)
    
    def restore_signal_handler(self):
        """恢复原始信号处理器"""
        if self.original_handler is not None:
            signal.signal(signal.SIGINT, self.original_handler)
    
    def _signal_handler(self, signum, frame):
        """信号处理函数"""
        self.exit_requested = True
        self._show_exit_screen()
        sys.exit(0)
    
    def _show_exit_screen(self):
        """显示退出界面"""
        console.clear()
        # 使用与UI中相同的退出界面
        ui.print_goodbye()
    
    def check_exit_requested(self):
        """检查是否请求退出"""
        return self.exit_requested
    
    def reset_exit_flag(self):
        """重置退出标志"""
        self.exit_requested = False

# 创建全局实例
graceful_exit = GracefulExit()

def setup_graceful_exit():
    """设置优雅退出处理"""
    graceful_exit.setup_signal_handler()

def cleanup_graceful_exit():
    """清理优雅退出处理"""
    graceful_exit.restore_signal_handler()

def is_exit_requested():
    """检查是否请求退出"""
    return graceful_exit.check_exit_requested()

def reset_exit_flag():
    """重置退出标志"""
    graceful_exit.reset_exit_flag()
