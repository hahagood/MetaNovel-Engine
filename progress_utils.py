import time
import threading
import sys
from typing import Callable, Optional

class ProgressDisplay:
    """进度显示类，支持实时状态更新和进度条"""
    
    def __init__(self):
        self.is_running = False
        self.current_message = ""
        self.progress_thread = None
        self.completed_tasks = 0
        self.total_tasks = 0
        self.start_time = None
        
    def start_progress(self, total_tasks: int = 0, initial_message: str = "处理中..."):
        """开始进度显示"""
        if self.is_running:
            return
            
        self.is_running = True
        self.current_message = initial_message
        self.total_tasks = total_tasks
        self.completed_tasks = 0
        self.start_time = time.time()
        
        self.progress_thread = threading.Thread(target=self._progress_worker)
        self.progress_thread.daemon = True
        self.progress_thread.start()
    
    def update_progress(self, message: str, increment: bool = True):
        """更新进度信息"""
        if increment:
            self.completed_tasks += 1
        self.current_message = message
    
    def update_status_only(self, message: str):
        """只更新状态消息，不增加完成计数"""
        self.current_message = message
    
    def add_retry_indicator(self, base_message: str, retry_count: int, error_msg: str = ""):
        """添加重试指示符到消息"""
        retry_msg = f"{base_message} - 重试第{retry_count}次"
        if error_msg:
            retry_msg += f" ({error_msg[:25]}...)" if len(error_msg) > 25 else f" ({error_msg})"
        self.update_status_only(retry_msg)
    
    def stop_progress(self):
        """停止进度显示"""
        if not self.is_running:
            return
            
        self.is_running = False
        if self.progress_thread:
            self.progress_thread.join(timeout=1)
        
        # 清除当前行并移动到行首
        sys.stdout.write('\r' + ' ' * 80 + '\r')
        sys.stdout.flush()
        
        # 显示最终结果
        elapsed_time = time.time() - self.start_time if self.start_time else 0
        if self.total_tasks > 0:
            print(f"✅ 完成 {self.completed_tasks}/{self.total_tasks} 个任务，耗时 {elapsed_time:.1f}s")
        else:
            print(f"✅ 任务完成，耗时 {elapsed_time:.1f}s")
    
    def _progress_worker(self):
        """进度显示工作线程"""
        spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        spinner_idx = 0
        
        while self.is_running:
            spinner = spinner_chars[spinner_idx % len(spinner_chars)]
            spinner_idx += 1
            
            if self.total_tasks > 0:
                progress_percent = (self.completed_tasks / self.total_tasks) * 100
                progress_bar = self._create_progress_bar(progress_percent)
                status_text = f"{spinner} {progress_bar} {self.completed_tasks}/{self.total_tasks} - {self.current_message}"
            else:
                status_text = f"{spinner} {self.current_message}"
            
            # 限制显示长度，避免换行
            max_width = 80
            if len(status_text) > max_width:
                status_text = status_text[:max_width-3] + "..."
            
            sys.stdout.write(f'\r{status_text}')
            sys.stdout.flush()
            
            time.sleep(0.1)
    
    def _create_progress_bar(self, percent: float, width: int = 20) -> str:
        """创建进度条"""
        filled = int(width * percent / 100)
        bar = '█' * filled + '░' * (width - filled)
        return f"[{bar}] {percent:.1f}%"

class AsyncProgressManager:
    """异步任务进度管理器"""
    
    def __init__(self):
        self.display = ProgressDisplay()
        
    def start(self, total_tasks: int, initial_message: str = "开始处理..."):
        """开始进度跟踪"""
        self.display.start_progress(total_tasks, initial_message)
        
    def update(self, message: str, increment: bool = True):
        """更新进度"""
        self.display.update_progress(message, increment)
    
    def finish(self, final_message: str = "处理完成"):
        """结束进度跟踪"""
        self.display.update_progress(final_message, False)
        time.sleep(0.5)  # 让用户看到最终消息
        self.display.stop_progress()
    
    def create_callback(self) -> Callable[[str], None]:
        """创建进度回调函数"""
        def callback(message: str):
            self.update(message)
        return callback

def run_with_progress(async_func, *args, **kwargs):
    """运行异步函数并显示进度"""
    import asyncio
    
    # 检查是否已经在异步环境中
    try:
        loop = asyncio.get_running_loop()
        # 如果已经在事件循环中，直接返回协程
        return async_func(*args, **kwargs)
    except RuntimeError:
        # 不在事件循环中，创建新的事件循环
        return asyncio.run(async_func(*args, **kwargs))

# 简化的进度显示函数
def show_simple_progress(message: str, duration: float = 2.0):
    """显示简单的进度动画"""
    spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
    end_time = time.time() + duration
    spinner_idx = 0
    
    while time.time() < end_time:
        spinner = spinner_chars[spinner_idx % len(spinner_chars)]
        sys.stdout.write(f'\r{spinner} {message}')
        sys.stdout.flush()
        spinner_idx += 1
        time.sleep(0.1)
    
    sys.stdout.write('\r' + ' ' * (len(message) + 5) + '\r')
    sys.stdout.flush() 