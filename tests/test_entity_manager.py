"""
Unit tests for entity_manager module
"""

import unittest
from unittest.mock import patch, MagicMock
import os
import sys

# Add project root to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from entity_manager import EntityConfig, EntityManager, ENTITY_CONFIGS


class TestEntityConfig(unittest.TestCase):
    """测试EntityConfig类"""
    
    def test_entity_config_creation(self):
        """测试实体配置创建"""
        config = EntityConfig(
            name="测试实体",
            plural_name="测试实体列表",
            data_key="test_entities",
            reader_func=lambda: {},
            adder_func=lambda x, y: True,
            updater_func=lambda x, y: True,
            deleter_func=lambda x: True,
            generator_func=lambda x, y: "生成的内容"
        )
        
        self.assertEqual(config.name, "测试实体")
        self.assertEqual(config.plural_name, "测试实体列表")
        self.assertEqual(config.data_key, "test_entities")
        self.assertEqual(config.description_key, "description")  # 默认值


class TestEntityManager(unittest.TestCase):
    """测试EntityManager类"""
    
    def setUp(self):
        """测试设置"""
        # 创建模拟的实体配置
        self.mock_config = EntityConfig(
            name="角色",
            plural_name="角色",
            data_key="characters",
            reader_func=MagicMock(return_value={}),
            adder_func=MagicMock(return_value=True),
            updater_func=MagicMock(return_value=True),
            deleter_func=MagicMock(return_value=True),
            generator_func=MagicMock(return_value="生成的角色描述")
        )
        
        self.entity_manager = EntityManager(self.mock_config)
    
    def test_entity_manager_creation(self):
        """测试实体管理器创建"""
        self.assertEqual(self.entity_manager.config, self.mock_config)
    
    def test_display_entity_list_empty(self):
        """测试显示空实体列表"""
        with patch('builtins.print') as mock_print:
            self.entity_manager._display_entity_list({})
            
            # 检查是否打印了空列表消息
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertTrue(any("当前没有角色信息" in call for call in print_calls))
    
    def test_display_entity_list_with_data(self):
        """测试显示有数据的实体列表"""
        test_data = {
            "角色1": {"description": "这是角色1的描述"},
            "角色2": {"description": "这是一个很长的角色描述，应该被截断以确保显示格式正确"}
        }
        
        with patch('builtins.print') as mock_print:
            self.entity_manager._display_entity_list(test_data)
            
            # 检查是否打印了角色列表
            print_calls = [call[0][0] for call in mock_print.call_args_list]
            self.assertTrue(any("当前角色列表" in call for call in print_calls))
            self.assertTrue(any("角色1" in call for call in print_calls))
            self.assertTrue(any("角色2" in call for call in print_calls))
    
    def test_get_menu_choices_empty(self):
        """测试空数据时的菜单选项"""
        choices = self.entity_manager._get_menu_choices({})
        self.assertEqual(len(choices), 2)
        self.assertTrue(any("添加新角色" in choice for choice in choices))
        self.assertTrue(any("返回上级菜单" in choice for choice in choices))
    
    def test_get_menu_choices_with_data(self):
        """测试有数据时的菜单选项"""
        test_data = {"角色1": {"description": "描述1"}}
        choices = self.entity_manager._get_menu_choices(test_data)
        self.assertEqual(len(choices), 5)
        self.assertTrue(any("添加新角色" in choice for choice in choices))
        self.assertTrue(any("查看角色详情" in choice for choice in choices))
        self.assertTrue(any("修改角色信息" in choice for choice in choices))
        self.assertTrue(any("删除角色" in choice for choice in choices))
        self.assertTrue(any("返回上级菜单" in choice for choice in choices))
    
    @patch('entity_manager.questionary')
    def test_add_entity_success(self, mock_questionary):
        """测试成功添加实体"""
        # 模拟用户输入
        mock_questionary.text.return_value.ask.side_effect = ["新角色", ""]
        mock_questionary.confirm.return_value.ask.return_value = True
        mock_questionary.select.return_value.ask.return_value = "1. 接受并保存"
        
        # 模拟数据读取返回空（角色不存在）
        self.mock_config.reader_func.return_value = {}
        
        with patch('builtins.print'):
            self.entity_manager._add_entity()
        
        # 验证函数调用
        self.mock_config.reader_func.assert_called()
        self.mock_config.generator_func.assert_called_with("新角色", "")
        self.mock_config.adder_func.assert_called_with("新角色", "生成的角色描述")
    
    @patch('entity_manager.questionary')
    def test_add_entity_already_exists(self, mock_questionary):
        """测试添加已存在的实体"""
        # 模拟用户输入
        mock_questionary.text.return_value.ask.return_value = "已存在角色"
        
        # 模拟数据读取返回已存在的角色
        self.mock_config.reader_func.return_value = {
            "已存在角色": {"description": "已存在的描述"}
        }
        
        with patch('builtins.print') as mock_print:
            self.entity_manager._add_entity()
        
        # 验证打印了存在消息
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("已存在" in call for call in print_calls))
        
        # 验证没有调用生成函数
        self.mock_config.generator_func.assert_not_called()
    
    @patch('entity_manager.questionary')
    def test_view_entity(self, mock_questionary):
        """测试查看实体详情"""
        # 模拟用户选择
        mock_questionary.select.return_value.ask.return_value = "角色1"
        
        # 模拟数据
        test_data = {
            "角色1": {"description": "角色1的详细描述"}
        }
        self.mock_config.reader_func.return_value = test_data
        
        with patch('builtins.print') as mock_print:
            self.entity_manager._view_entity()
        
        # 验证打印了角色详情
        print_calls = [call[0][0] for call in mock_print.call_args_list]
        self.assertTrue(any("角色详情：角色1" in call for call in print_calls))
        self.assertTrue(any("角色1的详细描述" in call for call in print_calls))
    
    @patch('entity_manager.questionary')
    def test_edit_entity(self, mock_questionary):
        """测试编辑实体"""
        # 模拟用户输入
        mock_questionary.select.return_value.ask.return_value = "角色1"
        mock_questionary.text.return_value.ask.return_value = "修改后的描述"
        
        # 模拟数据
        test_data = {
            "角色1": {"description": "原始描述"}
        }
        self.mock_config.reader_func.return_value = test_data
        
        with patch('builtins.print'):
            self.entity_manager._edit_entity()
        
        # 验证调用了更新函数
        self.mock_config.updater_func.assert_called_with("角色1", "修改后的描述")
    
    @patch('entity_manager.questionary')
    def test_delete_entity(self, mock_questionary):
        """测试删除实体"""
        # 模拟用户输入
        mock_questionary.select.return_value.ask.return_value = "角色1"
        mock_questionary.confirm.return_value.ask.return_value = True
        
        # 模拟数据
        test_data = {
            "角色1": {"description": "要删除的角色"}
        }
        self.mock_config.reader_func.return_value = test_data
        
        with patch('builtins.print'):
            self.entity_manager._delete_entity()
        
        # 验证调用了删除函数
        self.mock_config.deleter_func.assert_called_with("角色1")


class TestEntityConfigs(unittest.TestCase):
    """测试预定义的实体配置"""
    
    def test_predefined_configs_exist(self):
        """测试预定义配置是否存在"""
        self.assertIn("characters", ENTITY_CONFIGS)
        self.assertIn("locations", ENTITY_CONFIGS)
        self.assertIn("items", ENTITY_CONFIGS)
    
    def test_character_config(self):
        """测试角色配置"""
        config = ENTITY_CONFIGS["characters"]
        self.assertEqual(config.name, "角色")
        self.assertEqual(config.data_key, "characters")
    
    def test_location_config(self):
        """测试场景配置"""
        config = ENTITY_CONFIGS["locations"]
        self.assertEqual(config.name, "场景")
        self.assertEqual(config.data_key, "locations")
    
    def test_item_config(self):
        """测试道具配置"""
        config = ENTITY_CONFIGS["items"]
        self.assertEqual(config.name, "道具")
        self.assertEqual(config.data_key, "items")


if __name__ == '__main__':
    unittest.main() 