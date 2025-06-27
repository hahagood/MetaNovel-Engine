"""
Unit tests for llm_service module
"""

import unittest
import tempfile
import json
import os
from unittest.mock import patch, MagicMock, AsyncMock

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_service import LLMService


class TestLLMService(unittest.TestCase):
    """测试LLMService类的功能"""
    
    def setUp(self):
        """每个测试前的设置"""
        # 创建临时的prompts.json文件
        self.test_prompts = {
            "theme_paragraph": {
                "base_prompt": "请将以下主题扩展：{one_line_theme}",
                "user_prompt_template": "{base_prompt}\n\n用户要求：{user_prompt}"
            },
            "character_description": {
                "base_prompt": "请为角色 '{char_name}' 创建描述",
                "user_prompt_template": "{base_prompt}\n\n用户要求：{user_prompt}"
            }
        }
        
        # 创建临时文件
        self.temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False)
        json.dump(self.test_prompts, self.temp_file, ensure_ascii=False, indent=2)
        self.temp_file.close()
        
        # Mock配置
        self.mock_config = {
            'theme_paragraph_length': '300-500字',
            'character_description_length': '200-400字'
        }
        
        # 创建LLMService实例
        with patch('llm_service.GENERATION_CONFIG', self.mock_config):
            with patch('builtins.open', side_effect=self._mock_open):
                self.llm_service = LLMService()
    
    def tearDown(self):
        """每个测试后的清理"""
        # 删除临时文件
        os.unlink(self.temp_file.name)
    
    def _mock_open(self, filename, mode='r', **kwargs):
        """模拟open函数，用于读取prompts.json"""
        if 'prompts.json' in filename:
            return open(self.temp_file.name, mode, **kwargs)
        else:
            # 对于其他文件，使用原始的open
            return open(filename, mode, **kwargs)
    
    def test_prompt_loading(self):
        """测试提示词加载"""
        self.assertIn("theme_paragraph", self.llm_service.prompts)
        self.assertIn("character_description", self.llm_service.prompts)
    
    def test_get_prompt_basic(self):
        """测试基础提示词获取"""
        prompt = self.llm_service._get_prompt(
            "theme_paragraph", 
            one_line_theme="测试主题"
        )
        self.assertIn("测试主题", prompt)
        self.assertIn("请将以下主题扩展", prompt)
    
    def test_get_prompt_with_user_input(self):
        """测试带用户输入的提示词获取"""
        prompt = self.llm_service._get_prompt(
            "theme_paragraph",
            user_prompt="使其更加幽默",
            one_line_theme="测试主题"
        )
        self.assertIn("测试主题", prompt)
        self.assertIn("用户要求：使其更加幽默", prompt)
    
    def test_get_prompt_not_found(self):
        """测试获取不存在的提示词类型"""
        prompt = self.llm_service._get_prompt("nonexistent_type")
        self.assertIsNone(prompt)
    
    @patch('llm_service.OpenAI')
    def test_client_initialization(self, mock_openai):
        """测试客户端初始化"""
        # 重新初始化以触发客户端创建
        with patch('llm_service.GENERATION_CONFIG', self.mock_config):
            service = LLMService()
            service._initialize_clients()
        
        # 验证OpenAI客户端被调用
        mock_openai.assert_called()
    
    @patch('llm_service.OpenAI')
    def test_is_available(self, mock_openai):
        """测试服务可用性检查"""
        with patch('llm_service.GENERATION_CONFIG', self.mock_config):
            service = LLMService()
            
            # 模拟客户端存在
            service.client = MagicMock()
            self.assertTrue(service.is_available())
            
            # 模拟客户端不存在
            service.client = None
            self.assertFalse(service.is_available())
    
    def test_generate_theme_paragraph_with_mock(self):
        """测试段落主题生成（使用模拟）"""
        # 模拟AI响应
        mock_response = "这是一个生成的段落主题..."
        
        with patch.object(self.llm_service, '_make_request', return_value=mock_response):
            result = self.llm_service.generate_theme_paragraph("测试主题")
            self.assertEqual(result, mock_response)
    
    def test_generate_character_description_with_mock(self):
        """测试角色描述生成（使用模拟）"""
        mock_response = "这是一个生成的角色描述..."
        
        with patch.object(self.llm_service, '_make_request', return_value=mock_response):
            result = self.llm_service.generate_character_description("测试角色")
            self.assertEqual(result, mock_response)
    
    def test_error_handling_in_make_request(self):
        """测试请求中的错误处理"""
        # 模拟客户端不可用
        self.llm_service.client = None
        result = self.llm_service._make_request("测试提示词")
        self.assertIsNone(result)
    
    def test_fallback_prompts(self):
        """测试后备提示词机制"""
        # 创建一个没有prompts.json的服务实例
        with patch('builtins.open', side_effect=FileNotFoundError):
            with patch('llm_service.GENERATION_CONFIG', self.mock_config):
                service = LLMService()
        
        # 测试后备提示词是否工作
        with patch.object(service, '_make_request', return_value="测试响应"):
            result = service.generate_theme_paragraph("测试主题")
            self.assertEqual(result, "测试响应")


class TestLLMServiceAsync(unittest.IsolatedAsyncioTestCase):
    """测试LLMService异步功能"""
    
    async def asyncSetUp(self):
        """异步测试设置"""
        self.mock_config = {
            'theme_paragraph_length': '300-500字',
            'character_description_length': '200-400字'
        }
        
        with patch('llm_service.GENERATION_CONFIG', self.mock_config):
            self.llm_service = LLMService()
    
    async def test_async_client_availability(self):
        """测试异步客户端可用性"""
        # 模拟异步客户端存在
        self.llm_service.async_client = MagicMock()
        self.assertTrue(self.llm_service.is_async_available())
        
        # 模拟异步客户端不存在
        self.llm_service.async_client = None
        self.assertFalse(self.llm_service.is_async_available())
    
    async def test_async_generate_chapter_summary(self):
        """测试异步章节概要生成"""
        mock_response = "这是一个生成的章节概要..."
        chapter = {"title": "第一章", "outline": "章节大纲"}
        
        with patch.object(self.llm_service, '_make_async_request', return_value=mock_response):
            result = await self.llm_service.generate_chapter_summary_async(
                chapter, 1, "上下文信息"
            )
            self.assertEqual(result, mock_response)
    
    async def test_async_batch_generation(self):
        """测试异步批量生成"""
        mock_response = "批量生成的概要..."
        chapters = [
            {"title": "第一章", "outline": "大纲1"},
            {"title": "第二章", "outline": "大纲2"}
        ]
        
        with patch.object(self.llm_service, 'generate_chapter_summary_async', return_value=mock_response):
            results = await self.llm_service.generate_all_summaries_async(
                chapters, "上下文信息"
            )
            self.assertEqual(len(results), 2)
            for result in results:
                self.assertEqual(result["summary"], mock_response)


if __name__ == '__main__':
    unittest.main() 