"""
Unit tests for llm_service module
"""

import unittest
import os
import sys
import json
import tempfile
import shutil
from unittest.mock import patch, MagicMock

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from llm_service import LLMService
from config import API_CONFIG

# --- Test Data ---
DEFAULT_PROMPTS_CONTENT = {
  "theme_paragraph": {
    "base_prompt": "主题：{one_line_theme}",
    "user_prompt_template": "{base_prompt}, 要求：{user_prompt}"
  }
}

class TestLLMService(unittest.TestCase):
    """测试LLMService类的功能"""

    @patch('llm_service.LLMService._load_prompts')
    @patch('llm_service.LLMService._initialize_clients')
    def setUp(self, mock_init_clients, mock_load_prompts):
        """每个测试前的设置"""
        self.llm_service = LLMService()
        # Manually set the prompts for testing
        self.llm_service.prompts = DEFAULT_PROMPTS_CONTENT

    def tearDown(self):
        """每个测试后的清理"""
        pass

    def test_prompt_loading(self):
        """测试提示词加载"""
        self.assertIn("theme_paragraph", self.llm_service.prompts)

    def test_get_prompt_basic(self):
        """测试基础提示词获取"""
        prompt = self.llm_service._get_prompt("theme_paragraph", one_line_theme="测试主题")
        self.assertIn("主题：测试主题", prompt)

    def test_get_prompt_with_user_input(self):
        """测试带用户输入的提示词获取"""
        prompt = self.llm_service._get_prompt("theme_paragraph", user_prompt="用户要求", one_line_theme="测试主题")
        self.assertIn("主题：测试主题", prompt)
        self.assertIn("要求：用户要求", prompt)

    def test_get_prompt_not_found(self):
        """测试获取不存在的提示词类型"""
        prompt = self.llm_service._get_prompt("non_existent_type")
        self.assertIsNone(prompt)

    @patch.dict(API_CONFIG, {"openrouter_api_key": "fake_key"})
    @patch('llm_service.OpenAI')
    @patch('llm_service.AsyncOpenAI')
    def test_client_initialization(self, mock_async_openai, mock_openai):
        """测试客户端初始化"""
        # Re-initializing to test this specific part
        service = LLMService()
        mock_openai.assert_called()
        mock_async_openai.assert_called()

if __name__ == '__main__':
    unittest.main()