"""
Unit tests for config module
"""

import unittest
import os
import sys
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import config


class TestConfig(unittest.TestCase):
    """测试配置模块"""
    
    def test_proxy_config_structure(self):
        """测试代理配置结构"""
        self.assertIn('PROXY_CONFIG', dir(config))
        
        if config.PROXY_CONFIG:
            # 如果代理配置存在，检查结构
            self.assertIsInstance(config.PROXY_CONFIG, dict)
    
    def test_ai_config_structure(self):
        """测试AI配置结构"""
        self.assertIn('AI_CONFIG', dir(config))
        
        required_keys = ['model', 'backup_model', 'base_url', 'timeout']
        for key in required_keys:
            self.assertIn(key, config.AI_CONFIG)
    
    def test_api_config_structure(self):
        """测试API配置结构"""
        self.assertIn('API_CONFIG', dir(config))
        
        required_keys = ['openrouter_api_key', 'base_url']
        for key in required_keys:
            self.assertIn(key, config.API_CONFIG)
    
    def test_file_paths_structure(self):
        """测试文件路径配置结构"""
        self.assertIn('FILE_PATHS', dir(config))
        
        required_keys = [
            'theme_one_line', 'theme_paragraph', 'characters', 'locations', 'items',
            'story_outline', 'chapter_outline', 'chapter_summary', 'novel_text'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.FILE_PATHS)
    
    def test_generation_config_structure(self):
        """测试生成配置结构"""
        self.assertIn('GENERATION_CONFIG', dir(config))
        
        required_keys = [
            'theme_paragraph_length', 'character_description_length',
            'location_description_length', 'item_description_length',
            'story_outline_length', 'chapter_summary_length', 'novel_chapter_length'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.GENERATION_CONFIG)
    
    def test_retry_config_structure(self):
        """测试重试配置结构"""
        self.assertIn('RETRY_CONFIG', dir(config))
        
        required_keys = [
            'max_retries', 'base_delay', 'max_delay',
            'exponential_backoff', 'backoff_multiplier', 'jitter'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.RETRY_CONFIG)
    
    def test_config_values_types(self):
        """测试配置值的类型"""
        # AI配置类型检查
        self.assertIsInstance(config.AI_CONFIG['base_url'], str)
        self.assertIsInstance(config.AI_CONFIG['model'], str)
        self.assertIsInstance(config.AI_CONFIG['backup_model'], str)
        self.assertIsInstance(config.AI_CONFIG['timeout'], (int, float))
        
        # API配置类型检查
        # openrouter_api_key可能为None（如果未设置环境变量）
        if config.API_CONFIG['openrouter_api_key'] is not None:
            self.assertIsInstance(config.API_CONFIG['openrouter_api_key'], str)
        self.assertIsInstance(config.API_CONFIG['base_url'], str)
        
        # 重试配置类型检查
        self.assertIsInstance(config.RETRY_CONFIG['max_retries'], int)
        self.assertIsInstance(config.RETRY_CONFIG['base_delay'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['max_delay'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['backoff_multiplier'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['exponential_backoff'], bool)
        self.assertIsInstance(config.RETRY_CONFIG['jitter'], bool)
    
    def test_config_values_reasonable(self):
        """测试配置值是否合理"""
        # 重试配置合理性检查
        self.assertGreater(config.RETRY_CONFIG['max_retries'], 0)
        self.assertGreater(config.RETRY_CONFIG['base_delay'], 0)
        self.assertGreater(config.RETRY_CONFIG['max_delay'], 0)
        self.assertGreaterEqual(config.RETRY_CONFIG['max_delay'], 
                               config.RETRY_CONFIG['base_delay'])
        self.assertGreater(config.RETRY_CONFIG['backoff_multiplier'], 1)
        
        # AI配置合理性检查
        self.assertGreater(config.AI_CONFIG['timeout'], 0)
        self.assertTrue(config.AI_CONFIG['base_url'].startswith('http'))
        
        # API配置合理性检查
        self.assertTrue(config.API_CONFIG['base_url'].startswith('http'))
    
    @patch('httpx.Client')
    def test_setup_proxy_with_config(self, mock_httpx_client):
        """测试带配置的代理设置"""
        test_proxy_config = {
            'enabled': True,
            'http_proxy': 'http://proxy:8080',
            'https_proxy': 'http://proxy:8080'
        }
        
        with patch.object(config, 'PROXY_CONFIG', test_proxy_config):
            config.setup_proxy()
        
        # 这个测试主要确保函数可以正常调用而不抛出异常
        self.assertTrue(True)
    
    def test_setup_proxy_without_config(self):
        """测试没有代理配置的代理设置"""
        test_proxy_config = {
            'enabled': False,
            'http_proxy': '',
            'https_proxy': ''
        }
        
        with patch.object(config, 'PROXY_CONFIG', test_proxy_config):
            # 应该不抛出异常
            config.setup_proxy()
        
        self.assertTrue(True)

    def test_ai_config_values(self):
        """测试AI配置值的有效性"""
        # 检查模型名称不为空
        self.assertIsInstance(config.AI_CONFIG['model'], str)
        self.assertGreater(len(config.AI_CONFIG['model']), 0)
        
        # 检查备用模型名称不为空
        self.assertIsInstance(config.AI_CONFIG['backup_model'], str)
        self.assertGreater(len(config.AI_CONFIG['backup_model']), 0)
        
        # 检查超时时间为正整数
        self.assertIsInstance(config.AI_CONFIG['timeout'], int)
        self.assertGreater(config.AI_CONFIG['timeout'], 0)


class TestConfigIntegration(unittest.TestCase):
    """测试配置模块的集成功能"""
    
    def test_meta_directories_exist(self):
        """测试元数据目录配置"""
        self.assertIn('META_DIR', dir(config))
        self.assertIn('META_BACKUP_DIR', dir(config))
        
        # 测试目录路径是否合理
        self.assertIsInstance(str(config.META_DIR), str)
        self.assertIsInstance(str(config.META_BACKUP_DIR), str)
    
    def test_all_file_paths_use_meta_dir(self):
        """测试所有文件路径都使用meta目录"""
        meta_dir = config.META_DIR
        
        for key, file_path in config.FILE_PATHS.items():
            # 检查文件路径是否在meta目录下
            self.assertTrue(str(file_path).startswith(str(meta_dir)))


if __name__ == '__main__':
    unittest.main() 