import os
from pathlib import Path

# --- 基础配置 ---
META_DIR = Path("meta")
META_BACKUP_DIR = Path("meta_backup")

# --- 网络配置 ---
PROXY_CONFIG = {
    "enabled": True,
    "url": "http://127.0.0.1:8118"
}

# --- AI模型配置 ---
AI_CONFIG = {
    "model": "google/gemini-2.5-pro-preview-06-05",
    "base_url": "https://openrouter.ai/api/v1",
    "timeout": 60,
    "max_retries": 3
}

# --- 文件路径配置 ---
FILE_PATHS = {
    "theme_one_line": META_DIR / "theme_one_line.json",
    "theme_paragraph": META_DIR / "theme_paragraph.json", 
    "characters": META_DIR / "characters.json",
    "locations": META_DIR / "locations.json",
    "items": META_DIR / "items.json",
    "story_outline": META_DIR / "story_outline.json",
    "chapter_outline": META_DIR / "chapter_outline.json",
    "chapter_summary": META_DIR / "chapter_summary.json",
    "novel_text": META_DIR / "novel_text.json"
}

# --- 生成内容配置 ---
GENERATION_CONFIG = {
    "theme_paragraph_length": "200字左右",
    "character_description_length": "150-200字左右",
    "location_description_length": "150-200字左右", 
    "item_description_length": "150-200字左右",
    "story_outline_length": "500-800字左右",
    "chapter_summary_length": "300-500字左右",
    "novel_chapter_length": "2000-4000字左右"
}

# --- 智能重试机制配置 ---
RETRY_CONFIG = {
    "max_retries": 3,              # 最大重试次数
    "base_delay": 1.0,             # 基础延迟时间（秒）
    "max_delay": 30.0,             # 最大延迟时间（秒）
    "exponential_backoff": True,   # 是否使用指数退避
    "backoff_multiplier": 2.0,     # 退避倍数
    "jitter": True,                # 是否添加随机抖动
    "retryable_status_codes": [    # 可重试的HTTP状态码
        429,  # Too Many Requests (rate limit)
        500,  # Internal Server Error
        502,  # Bad Gateway
        503,  # Service Unavailable
        504,  # Gateway Timeout
    ],
    "retryable_exceptions": [      # 可重试的异常关键词
        "timeout", "connection", "network", "dns", "ssl"
    ],
    "enable_batch_retry": True,    # 是否启用批量重试
    "retry_delay_jitter_range": 0.1  # 抖动范围（秒）
}

def setup_proxy():
    """设置代理配置"""
    if PROXY_CONFIG["enabled"]:
        os.environ['http_proxy'] = PROXY_CONFIG["url"]
        os.environ['https_proxy'] = PROXY_CONFIG["url"]

def ensure_directories():
    """确保必要的目录存在"""
    META_DIR.mkdir(exist_ok=True)
    META_BACKUP_DIR.mkdir(exist_ok=True) 