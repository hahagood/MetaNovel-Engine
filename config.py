import os
import platform
from pathlib import Path
from dotenv import load_dotenv
from typing import Dict, Optional

# 加载.env文件中的环境变量
load_dotenv()

def get_app_data_dir() -> Path:
    """
    根据操作系统获取应用数据目录
    
    Returns:
        Path: 跨平台的应用数据目录路径
        
    各平台路径：
    - Windows: %LOCALAPPDATA%/MetaNovel (C:/Users/username/AppData/Local/MetaNovel)
    - macOS: ~/Library/Application Support/MetaNovel
    - Linux: ~/.metanovel (遵循传统Unix惯例)
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: 使用LocalAppData目录
        appdata_local = os.environ.get('LOCALAPPDATA')
        if appdata_local:
            return Path(appdata_local) / "MetaNovel"
        else:
            # 降级方案：如果环境变量不存在，使用默认路径
            return Path.home() / "AppData" / "Local" / "MetaNovel"
            
    elif system == "darwin":
        # macOS: 使用Application Support目录
        return Path.home() / "Library" / "Application Support" / "MetaNovel"
        
    else:
        # Linux和其他Unix系统: 使用传统的隐藏目录
        # 也可以考虑XDG标准，但为了向后兼容，保持现有方案
        return Path.home() / ".metanovel"


def get_user_documents_dir() -> Path:
    """
    根据操作系统获取用户文档目录
    
    Returns:
        Path: 跨平台的用户文档目录路径
        
    各平台路径：
    - Windows: %USERPROFILE%/Documents
    - macOS: ~/Documents
    - Linux: ~/Documents 或 ~/文档 (根据系统语言)
    """
    system = platform.system().lower()
    
    if system == "windows":
        # Windows: 使用 USERPROFILE/Documents
        user_profile = os.environ.get('USERPROFILE')
        if user_profile:
            documents_dir = Path(user_profile) / "Documents"
        else:
            # 降级方案
            documents_dir = Path.home() / "Documents"
            
    else:
        # macOS 和 Linux: 使用 ~/Documents
        documents_dir = Path.home() / "Documents"
        
        # Linux特殊处理：如果是中文系统，可能是"文档"目录
        if system == "linux":
            chinese_docs = Path.home() / "文档"
            if chinese_docs.exists() and chinese_docs.is_dir():
                documents_dir = chinese_docs
    
    return documents_dir

# --- 基础配置 ---
# 注意：这些是默认配置，多项目模式下会被动态路径覆盖
META_DIR = Path("meta")
META_BACKUP_DIR = Path("meta_backup")

# --- API配置 ---
API_CONFIG = {
    "openrouter_api_key": os.getenv("OPENROUTER_API_KEY"),
    "base_url": "https://openrouter.ai/api/v1",
}

# --- 网络配置 ---
PROXY_CONFIG = {
    "enabled": bool(os.getenv("HTTP_PROXY") or os.getenv("HTTPS_PROXY")),
    "http_proxy": os.getenv("HTTP_PROXY", "http://127.0.0.1:7890"),
    "https_proxy": os.getenv("HTTPS_PROXY", "http://127.0.0.1:7890")
}

# --- AI模型配置 ---
AI_CONFIG = {
    "model": os.getenv("DEFAULT_MODEL", "google/gemini-2.5-pro-preview-06-05"),
    "backup_model": os.getenv("BACKUP_MODEL", "meta-llama/llama-3.1-8b-instruct"),
    "base_url": "https://openrouter.ai/api/v1",
    "timeout": int(os.getenv("REQUEST_TIMEOUT", "60"))
}

# --- 文件路径配置 ---
# 注意：这是默认配置，多项目模式下使用get_project_paths()生成动态路径
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

def get_project_paths(project_path: Optional[Path] = None) -> Dict[str, Path]:
    """
    根据项目路径生成动态文件路径配置
    
    Args:
        project_path: 项目路径，如果为None则使用默认路径
        
    Returns:
        Dict[str, Path]: 文件路径配置字典
    """
    if project_path is None:
        # 使用默认路径（单项目模式）
        meta_dir = META_DIR
        backup_dir = META_BACKUP_DIR
    else:
        # 使用项目路径（多项目模式）
        meta_dir = project_path / "meta"
        backup_dir = project_path / "meta_backup"
    
    return {
        "meta_dir": meta_dir,
        "backup_dir": backup_dir,
        "theme_one_line": meta_dir / "theme_one_line.json",
        "theme_paragraph": meta_dir / "theme_paragraph.json",
        "characters": meta_dir / "characters.json",
        "locations": meta_dir / "locations.json",
        "items": meta_dir / "items.json",
        "story_outline": meta_dir / "story_outline.json",
        "chapter_outline": meta_dir / "chapter_outline.json",
        "chapter_summary": meta_dir / "chapter_summary.json",
        "novel_text": meta_dir / "novel_text.json"
    }

# --- 生成内容配置 ---
GENERATION_CONFIG = {
    "theme_paragraph_length": "200字左右",
    "character_description_length": "150-200字左右",
    "location_description_length": "150-200字左右", 
    "item_description_length": "150-200字左右",
    "story_outline_length": "500-800字左右",
    "chapter_outline_length": "800-1200字左右",
    "chapter_summary_length": "300-500字左右",
    "novel_chapter_length": "2000-4000字左右",
    "novel_critique_length": "200-300字左右",
    "enable_refinement": bool(os.getenv("ENABLE_REFINEMENT", "true").lower() == "true"),
    "show_critique_to_user": bool(os.getenv("SHOW_CRITIQUE_TO_USER", "true").lower() == "true"),
    "refinement_mode": os.getenv("REFINEMENT_MODE", "auto")  # auto, manual, disabled
}

# --- 智能重试机制配置 ---
RETRY_CONFIG = {
    "max_retries": int(os.getenv("RETRY_MAX_ATTEMPTS", "3")),              # 最大重试次数
    "base_delay": float(os.getenv("RETRY_DELAY", "1.0")),          # 基础延迟时间（秒）
    "max_delay": float(os.getenv("MAX_RETRY_DELAY", "30.0")),      # 最大延迟时间（秒）
    "exponential_backoff": True,   # 是否使用指数退避
    "backoff_multiplier": float(os.getenv("BACKOFF_FACTOR", "2.0")), # 退避倍数
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
    "retry_delay_jitter_range": float(os.getenv("JITTER_RANGE", "0.1"))  # 抖动范围（秒）
}

# --- 导出配置 ---
EXPORT_CONFIG = {
    "use_custom_path": False,  # 是否使用自定义导出路径
    "custom_export_path": "",  # 自定义导出路径
    "default_export_path": get_user_documents_dir() / "MetaNovel"  # 默认导出路径
}

def setup_proxy():
    """设置代理配置"""
    if PROXY_CONFIG["enabled"]:
        os.environ['http_proxy'] = PROXY_CONFIG["http_proxy"]
        os.environ['https_proxy'] = PROXY_CONFIG["https_proxy"]

def validate_config():
    """验证配置的有效性"""
    if not API_CONFIG["openrouter_api_key"]:
        print("警告: 未找到OPENROUTER_API_KEY环境变量")
        print("请设置环境变量或创建.env文件")
        return False
    return True

def get_export_base_dir() -> Path:
    """
    获取导出基础目录
    
    Returns:
        Path: 导出基础目录路径
    """
    if EXPORT_CONFIG["use_custom_path"] and EXPORT_CONFIG["custom_export_path"]:
        custom_path = Path(EXPORT_CONFIG["custom_export_path"])
        if custom_path.is_absolute():
            return custom_path
        else:
            # 相对路径：相对于用户文档目录
            return get_user_documents_dir() / custom_path
    else:
        # 使用默认路径
        return EXPORT_CONFIG["default_export_path"]


def set_custom_export_path(path: str) -> bool:
    """
    设置自定义导出路径
    
    Args:
        path: 导出路径（可以是绝对路径或相对路径）
        
    Returns:
        bool: 设置成功返回True
    """
    try:
        # 验证路径是否有效
        test_path = Path(path)
        if not test_path.is_absolute():
            # 相对路径：相对于用户文档目录
            test_path = get_user_documents_dir() / path
        
        # 尝试创建目录以验证权限
        test_path.mkdir(parents=True, exist_ok=True)
        
        # 设置配置
        EXPORT_CONFIG["custom_export_path"] = path
        EXPORT_CONFIG["use_custom_path"] = True
        
        return True
    except Exception as e:
        print(f"设置导出路径时出错: {e}")
        return False


def reset_export_path():
    """重置导出路径为默认值"""
    EXPORT_CONFIG["use_custom_path"] = False
    EXPORT_CONFIG["custom_export_path"] = ""


def get_export_path_info() -> Dict[str, str]:
    """
    获取导出路径信息
    
    Returns:
        Dict: 包含导出路径信息的字典
    """
    base_dir = get_export_base_dir()
    
    return {
        "current_path": str(base_dir),
        "is_custom": EXPORT_CONFIG["use_custom_path"],
        "custom_path": EXPORT_CONFIG["custom_export_path"],
        "default_path": str(EXPORT_CONFIG["default_export_path"]),
        "documents_dir": str(get_user_documents_dir())
    }


def ensure_directories(project_path: Optional[Path] = None):
    """
    确保必要的目录存在
    
    Args:
        project_path: 项目路径，如果为None则使用默认路径
    """
    paths = get_project_paths(project_path)
    paths["meta_dir"].mkdir(parents=True, exist_ok=True)
    paths["backup_dir"].mkdir(parents=True, exist_ok=True) 