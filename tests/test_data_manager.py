"""
Unit tests for data_manager module
"""

import unittest
import tempfile
import shutil
import os
import json
from unittest.mock import patch, MagicMock

# Add project root to path for imports
import sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from data_manager import DataManager


class TestDataManager(unittest.TestCase):
    """测试DataManager类的功能"""
    
    def setUp(self):
        """每个测试前的设置"""
        # 创建临时目录用于测试
        self.test_dir = tempfile.mkdtemp()
        self.original_meta_dir = os.path.join(self.test_dir, "meta")
        
        # 模拟配置
        self.mock_config = {
            'meta_dir': self.original_meta_dir,
            'characters_file': os.path.join(self.original_meta_dir, "characters.json"),
            'locations_file': os.path.join(self.original_meta_dir, "locations.json"),
            'items_file': os.path.join(self.original_meta_dir, "items.json"),
            'theme_one_line_file': os.path.join(self.original_meta_dir, "theme_one_line.json"),
            'theme_paragraph_file': os.path.join(self.original_meta_dir, "theme_paragraph.json"),
            'story_outline_file': os.path.join(self.original_meta_dir, "story_outline.json"),
            'chapter_outline_file': os.path.join(self.original_meta_dir, "chapter_outline.json"),
            'chapter_summaries_file': os.path.join(self.original_meta_dir, "chapter_summaries.json"),
            'novel_chapters_file': os.path.join(self.original_meta_dir, "novel_chapters.json")
        }
        
        # 创建DataManager实例，使用模拟配置
        with patch('data_manager.FILE_CONFIG', self.mock_config):
            self.data_manager = DataManager()
    
    def tearDown(self):
        """每个测试后的清理"""
        # 删除临时目录
        shutil.rmtree(self.test_dir)
    
    def test_ensure_meta_dir(self):
        """测试确保meta目录存在"""
        self.data_manager._ensure_meta_dir()
        self.assertTrue(os.path.exists(self.original_meta_dir))
    
    def test_read_write_theme_one_line(self):
        """测试一句话主题的读写"""
        theme = "一个关于勇气的故事"
        
        # 测试写入
        result = self.data_manager.write_theme_one_line(theme)
        self.assertTrue(result)
        
        # 测试读取
        read_theme = self.data_manager.read_theme_one_line()
        self.assertEqual(read_theme, theme)
        
        # 测试读取不存在的文件
        os.remove(self.mock_config['theme_one_line_file'])
        empty_theme = self.data_manager.read_theme_one_line()
        self.assertEqual(empty_theme, "")
    
    def test_read_write_theme_paragraph(self):
        """测试段落主题的读写"""
        paragraph = "这是一个详细的段落主题描述..."
        
        # 测试写入
        result = self.data_manager.write_theme_paragraph(paragraph)
        self.assertTrue(result)
        
        # 测试读取
        read_paragraph = self.data_manager.read_theme_paragraph()
        self.assertEqual(read_paragraph, paragraph)
    
    def test_character_operations(self):
        """测试角色CRUD操作"""
        char_name = "测试角色"
        char_desc = "这是一个测试角色的描述"
        
        # 测试添加角色
        result = self.data_manager.add_character(char_name, char_desc)
        self.assertTrue(result)
        
        # 测试读取角色
        characters = self.data_manager.read_characters()
        self.assertIn(char_name, characters)
        self.assertEqual(characters[char_name]["description"], char_desc)
        
        # 测试更新角色
        new_desc = "更新后的角色描述"
        result = self.data_manager.update_character(char_name, new_desc)
        self.assertTrue(result)
        
        updated_characters = self.data_manager.read_characters()
        self.assertEqual(updated_characters[char_name]["description"], new_desc)
        
        # 测试删除角色
        result = self.data_manager.delete_character(char_name)
        self.assertTrue(result)
        
        final_characters = self.data_manager.read_characters()
        self.assertNotIn(char_name, final_characters)
    
    def test_location_operations(self):
        """测试场景CRUD操作"""
        loc_name = "测试场景"
        loc_desc = "这是一个测试场景的描述"
        
        # 测试添加场景
        result = self.data_manager.add_location(loc_name, loc_desc)
        self.assertTrue(result)
        
        # 测试读取场景
        locations = self.data_manager.read_locations()
        self.assertIn(loc_name, locations)
        self.assertEqual(locations[loc_name]["description"], loc_desc)
        
        # 测试更新场景
        new_desc = "更新后的场景描述"
        result = self.data_manager.update_location(loc_name, new_desc)
        self.assertTrue(result)
        
        # 测试删除场景
        result = self.data_manager.delete_location(loc_name)
        self.assertTrue(result)
        
        final_locations = self.data_manager.read_locations()
        self.assertNotIn(loc_name, final_locations)
    
    def test_item_operations(self):
        """测试道具CRUD操作"""
        item_name = "测试道具"
        item_desc = "这是一个测试道具的描述"
        
        # 测试添加道具
        result = self.data_manager.add_item(item_name, item_desc)
        self.assertTrue(result)
        
        # 测试读取道具
        items = self.data_manager.read_items()
        self.assertIn(item_name, items)
        self.assertEqual(items[item_name]["description"], item_desc)
        
        # 测试更新道具
        new_desc = "更新后的道具描述"
        result = self.data_manager.update_item(item_name, new_desc)
        self.assertTrue(result)
        
        # 测试删除道具
        result = self.data_manager.delete_item(item_name)
        self.assertTrue(result)
        
        final_items = self.data_manager.read_items()
        self.assertNotIn(item_name, final_items)
    
    def test_backup_restore(self):
        """测试备份和恢复功能"""
        # 创建一些测试数据
        self.data_manager.write_theme_one_line("测试主题")
        self.data_manager.add_character("角色1", "描述1")
        
        # 执行备份
        backup_success = self.data_manager.backup_data()
        self.assertTrue(backup_success)
        
        # 修改数据
        self.data_manager.write_theme_one_line("修改后的主题")
        
        # 恢复数据（这个测试需要手动实现restore功能）
        # 目前只测试备份是否成功
    
    def test_check_prerequisites(self):
        """测试前置条件检查"""
        # 初始状态应该都不存在
        one_line_exists, paragraph_exists = self.data_manager.check_prerequisites_for_world_setting()
        self.assertFalse(one_line_exists)
        self.assertFalse(paragraph_exists)
        
        # 添加一句话主题
        self.data_manager.write_theme_one_line("测试主题")
        one_line_exists, paragraph_exists = self.data_manager.check_prerequisites_for_world_setting()
        self.assertTrue(one_line_exists)
        self.assertFalse(paragraph_exists)
        
        # 添加段落主题
        self.data_manager.write_theme_paragraph("测试段落")
        one_line_exists, paragraph_exists = self.data_manager.check_prerequisites_for_world_setting()
        self.assertTrue(one_line_exists)
        self.assertTrue(paragraph_exists)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试写入无效路径
        with patch('data_manager.FILE_CONFIG', {'theme_one_line_file': '/invalid/path/file.json'}):
            dm = DataManager()
            result = dm.write_theme_one_line("测试")
            self.assertFalse(result)


if __name__ == '__main__':
    unittest.main() 