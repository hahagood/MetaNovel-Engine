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
        
        required_keys = ['base_url', 'api_key', 'model', 'timeout']
        for key in required_keys:
            self.assertIn(key, config.AI_CONFIG)
    
    def test_file_config_structure(self):
        """测试文件配置结构"""
        self.assertIn('FILE_CONFIG', dir(config))
        
        required_keys = [
            'meta_dir', 'characters_file', 'locations_file', 'items_file',
            'theme_one_line_file', 'theme_paragraph_file', 'story_outline_file',
            'chapter_outline_file', 'chapter_summaries_file', 'novel_chapters_file'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.FILE_CONFIG)
    
    def test_generation_config_structure(self):
        """测试生成配置结构"""
        self.assertIn('GENERATION_CONFIG', dir(config))
        
        required_keys = [
            'theme_paragraph_length', 'character_description_length',
            'location_description_length', 'item_description_length',
            'story_outline_length', 'chapter_outline_length',
            'chapter_summary_length', 'novel_chapter_length'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.GENERATION_CONFIG)
    
    def test_retry_config_structure(self):
        """测试重试配置结构"""
        self.assertIn('RETRY_CONFIG', dir(config))
        
        required_keys = [
            'max_retries', 'base_delay', 'max_delay',
            'exponential_base', 'jitter', 'timeout'
        ]
        
        for key in required_keys:
            self.assertIn(key, config.RETRY_CONFIG)
    
    def test_config_values_types(self):
        """测试配置值的类型"""
        # AI配置类型检查
        self.assertIsInstance(config.AI_CONFIG['base_url'], str)
        self.assertIsInstance(config.AI_CONFIG['api_key'], str)
        self.assertIsInstance(config.AI_CONFIG['model'], str)
        self.assertIsInstance(config.AI_CONFIG['timeout'], (int, float))
        
        # 重试配置类型检查
        self.assertIsInstance(config.RETRY_CONFIG['max_retries'], int)
        self.assertIsInstance(config.RETRY_CONFIG['base_delay'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['max_delay'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['exponential_base'], (int, float))
        self.assertIsInstance(config.RETRY_CONFIG['jitter'], bool)
        self.assertIsInstance(config.RETRY_CONFIG['timeout'], (int, float))
    
    def test_config_values_reasonable(self):
        """测试配置值是否合理"""
        # 重试配置合理性检查
        self.assertGreater(config.RETRY_CONFIG['max_retries'], 0)
        self.assertGreater(config.RETRY_CONFIG['base_delay'], 0)
        self.assertGreater(config.RETRY_CONFIG['max_delay'], 0)
        self.assertGreaterEqual(config.RETRY_CONFIG['max_delay'], 
                               config.RETRY_CONFIG['base_delay'])
        self.assertGreater(config.RETRY_CONFIG['exponential_base'], 1)
        self.assertGreater(config.RETRY_CONFIG['timeout'], 0)
        
        # AI配置合理性检查
        self.assertGreater(config.AI_CONFIG['timeout'], 0)
        self.assertTrue(config.AI_CONFIG['base_url'].startswith('http'))
    
    @patch('httpx.Client')
    def test_setup_proxy_with_config(self, mock_httpx_client):
        """测试带配置的代理设置"""
        test_proxy_config = {
            'http://': 'http://proxy:8080',
            'https://': 'http://proxy:8080'
        }
        
        with patch.object(config, 'PROXY_CONFIG', test_proxy_config):
            config.setup_proxy()
        
        # 这个测试主要确保函数可以正常调用而不抛出异常
        self.assertTrue(True)
    
    def test_setup_proxy_without_config(self):
        """测试没有代理配置的代理设置"""
        with patch.object(config, 'PROXY_CONFIG', None):
            # 应该不抛出异常
            config.setup_proxy()
        
        self.assertTrue(True)


class TestConfigIntegration(unittest.TestCase):
    """测试配置模块的集成功能"""
    
    def test_file_paths_exist(self):
        """测试文件路径配置的目录是否可以创建"""
        meta_dir = config.FILE_CONFIG['meta_dir']
        
        # 测试路径是否是绝对路径或相对路径
        self.assertIsInstance(meta_dir, str)
        self.assertGreater(len(meta_dir), 0)
    
    def test_all_file_configs_have_meta_dir_prefix(self):
        """测试所有文件配置都以meta目录为前缀"""
        meta_dir = config.FILE_CONFIG['meta_dir']
        
        file_keys = [key for key in config.FILE_CONFIG.keys() 
                    if key.endswith('_file')]
        
        for key in file_keys:
            file_path = config.FILE_CONFIG[key]
            # 检查文件路径是否在meta目录下
            self.assertTrue(file_path.startswith(meta_dir) or 
                           os.path.commonpath([meta_dir, file_path]) == meta_dir)


if __name__ == '__main__':
    unittest.main() 