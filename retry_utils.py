import asyncio
import random
import time
from typing import Callable, Any, Optional, List, Union
from openai import APIStatusError
from config import RETRY_CONFIG

class RetryError(Exception):
    """重试最终失败的异常"""
    def __init__(self, message: str, last_exception: Exception, retry_count: int):
        super().__init__(message)
        self.last_exception = last_exception
        self.retry_count = retry_count

class RetryManager:
    """智能重试管理器"""
    
    def __init__(self, config: dict = None):
        self.config = config or RETRY_CONFIG
        
    def is_retryable_error(self, error: Exception) -> bool:
        """判断错误是否可以重试"""
        # 检查API状态错误
        if isinstance(error, APIStatusError):
            return error.status_code in self.config["retryable_status_codes"]
        
        # 检查其他异常
        error_str = str(error).lower()
        return any(
            keyword in error_str 
            for keyword in self.config["retryable_exceptions"]
        )
    
    def calculate_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        if not self.config["exponential_backoff"]:
            delay = self.config["base_delay"]
        else:
            delay = self.config["base_delay"] * (
                self.config["backoff_multiplier"] ** (attempt - 1)
            )
        
        # 限制最大延迟
        delay = min(delay, self.config["max_delay"])
        
        # 添加随机抖动
        if self.config["jitter"]:
            jitter_range = self.config["retry_delay_jitter_range"]
            jitter = random.uniform(-jitter_range, jitter_range)
            delay += jitter
            delay = max(0.1, delay)  # 确保延迟不会太小
        
        return delay
    
    async def retry_async(
        self, 
        func: Callable, 
        *args, 
        task_name: str = "",
        progress_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Any:
        """异步重试函数"""
        last_exception = None
        
        for attempt in range(1, self.config["max_retries"] + 1):
            try:
                if progress_callback and attempt > 1:
                    progress_callback(f"{task_name} - 重试第{attempt-1}次")
                
                result = await func(*args, **kwargs)
                
                if attempt > 1 and progress_callback:
                    progress_callback(f"{task_name} - 重试成功")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否可重试
                if not self.is_retryable_error(e):
                    if progress_callback:
                        progress_callback(f"{task_name} - 不可重试的错误: {e}")
                    raise e
                
                # 如果是最后一次尝试，抛出重试错误
                if attempt >= self.config["max_retries"]:
                    if progress_callback:
                        progress_callback(f"{task_name} - 重试{attempt-1}次后仍失败")
                    raise RetryError(
                        f"重试{self.config['max_retries']}次后仍失败: {str(e)}", 
                        e, 
                        attempt - 1
                    )
                
                # 计算延迟并等待
                delay = self.calculate_delay(attempt)
                if progress_callback:
                    progress_callback(f"{task_name} - 第{attempt}次失败，{delay:.1f}s后重试: {str(e)[:50]}")
                
                await asyncio.sleep(delay)
        
        # 这行代码理论上不会执行到
        raise RetryError("重试逻辑异常", last_exception, self.config["max_retries"])
    
    def retry_sync(
        self, 
        func: Callable, 
        *args, 
        task_name: str = "",
        progress_callback: Optional[Callable[[str], None]] = None,
        **kwargs
    ) -> Any:
        """同步重试函数"""
        last_exception = None
        
        for attempt in range(1, self.config["max_retries"] + 1):
            try:
                if progress_callback and attempt > 1:
                    progress_callback(f"{task_name} - 重试第{attempt-1}次")
                
                result = func(*args, **kwargs)
                
                if attempt > 1 and progress_callback:
                    progress_callback(f"{task_name} - 重试成功")
                
                return result
                
            except Exception as e:
                last_exception = e
                
                # 检查是否可重试
                if not self.is_retryable_error(e):
                    if progress_callback:
                        progress_callback(f"{task_name} - 不可重试的错误: {e}")
                    raise e
                
                # 如果是最后一次尝试，抛出重试错误
                if attempt >= self.config["max_retries"]:
                    if progress_callback:
                        progress_callback(f"{task_name} - 重试{attempt-1}次后仍失败")
                    raise RetryError(
                        f"重试{self.config['max_retries']}次后仍失败: {str(e)}", 
                        e, 
                        attempt - 1
                    )
                
                # 计算延迟并等待
                delay = self.calculate_delay(attempt)
                if progress_callback:
                    progress_callback(f"{task_name} - 第{attempt}次失败，{delay:.1f}s后重试: {str(e)[:50]}")
                
                time.sleep(delay)
        
        # 这行代码理论上不会执行到
        raise RetryError("重试逻辑异常", last_exception, self.config["max_retries"])

class BatchRetryManager:
    """批量重试管理器"""
    
    def __init__(self, config: dict = None):
        self.retry_manager = RetryManager(config)
        self.config = config or RETRY_CONFIG
    
    async def retry_failed_tasks_async(
        self,
        failed_tasks: List[tuple],  # [(task_id, task_func, *args, **kwargs), ...]
        progress_callback: Optional[Callable[[str], None]] = None
    ) -> tuple:
        """异步重试失败的任务"""
        if not self.config["enable_batch_retry"] or not failed_tasks:
            return {}, []
        
        if progress_callback:
            progress_callback(f"开始重试 {len(failed_tasks)} 个失败的任务...")
        
        retry_results = {}
        still_failed = []
        
        # 为每个失败的任务创建重试任务
        retry_tasks = []
        for task_id, task_func, args, kwargs in failed_tasks:
            task_name = kwargs.pop('task_name', f"任务{task_id}")
            retry_task = self.retry_manager.retry_async(
                task_func, *args, 
                task_name=task_name,
                progress_callback=progress_callback,
                **kwargs
            )
            retry_tasks.append((task_id, task_name, retry_task))
        
        # 并发执行所有重试任务
        try:
            # 创建任务列表，只包含协程对象
            task_coroutines = [task for _, _, task in retry_tasks]
            
            # 并发执行所有重试任务
            results = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # 处理重试结果
            for (task_id, task_name, _), result in zip(retry_tasks, results):
                if isinstance(result, Exception):
                    still_failed.append(task_id)
                    if progress_callback:
                        if isinstance(result, RetryError):
                            progress_callback(f"{task_name} - 重试最终失败（重试{result.retry_count}次）")
                        else:
                            progress_callback(f"{task_name} - 重试异常: {result}")
                else:
                    retry_results[task_id] = result
                    if progress_callback:
                        progress_callback(f"{task_name} - 重试成功")
                        
        except Exception as e:
            if progress_callback:
                progress_callback(f"批量重试过程中出现异常: {e}")
            # 如果整体失败，所有任务都仍然失败
            still_failed = [task_id for task_id, _, _ in retry_tasks]
        
        return retry_results, still_failed

# 创建全局重试管理器实例
retry_manager = RetryManager()
batch_retry_manager = BatchRetryManager()

# 装饰器函数
def with_retry(task_name: str = ""):
    """重试装饰器"""
    def decorator(func):
        if asyncio.iscoroutinefunction(func):
            async def async_wrapper(*args, **kwargs):
                return await retry_manager.retry_async(func, *args, task_name=task_name, **kwargs)
            return async_wrapper
        else:
            def sync_wrapper(*args, **kwargs):
                return retry_manager.retry_sync(func, *args, task_name=task_name, **kwargs)
            return sync_wrapper
    return decorator 