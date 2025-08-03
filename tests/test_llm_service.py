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
from pathlib import Path

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

    def test_get_prompts_path_multi_project_mode(self):
        """测试在多项目模式下_get_prompts_path的行为"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_path = Path(tmpdir)
            project_prompts_path = project_path / 'prompts.json'
            
            # 模拟项目prompts文件
            with open(project_prompts_path, 'w', encoding='utf-8') as f:
                json.dump({"test": "project_prompt"}, f)

            # 模拟 project_data_manager
            mock_data_manager = MagicMock()
            mock_data_manager.project_path = project_path
            
            # 我们需要模拟 'project_data_manager.project_data_manager.get_data_manager'
            # 因为在 llm_service.py 中是这样导入的
            with patch('project_data_manager.project_data_manager.get_data_manager', return_value=mock_data_manager):
                # 创建一个新的LLMService实例以触发路径加载
                # 我们需要绕过构造函数中的 _load_prompts 和 _initialize_clients
                with patch.object(LLMService, '_load_prompts'), patch.object(LLMService, '_initialize_clients'):
                    service = LLMService()
                
                # 直接调用私有方法进行测试
                returned_path = service._get_prompts_path()
                
                # 断言返回的路径是项目路径，而不是根路径
                self.assertEqual(returned_path, project_prompts_path)
                
                # 验证加载的内容是否也正确
                service._load_prompts() # 重新加载
                self.assertEqual(service.prompts.get("test"), "project_prompt")

if __name__ == '__main__':
    unittest.main()