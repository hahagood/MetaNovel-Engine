"""
Entity Management Module

This module provides a generic CRUD interface for managing different entities 
(characters, locations, items) with unified UI logic.
"""

import questionary
from data_manager import data_manager
from llm_service import llm_service


class EntityConfig:
    """实体配置类，定义不同实体的配置信息"""
    
    def __init__(self, name, plural_name, data_key, 
                 reader_func, adder_func, updater_func, deleter_func,
                 generator_func, description_key="description"):
        self.name = name                    # 实体中文名（如"角色"）
        self.plural_name = plural_name      # 复数形式（如"角色"）
        self.data_key = data_key           # 数据文件键名（如"characters"）
        self.reader_func = reader_func      # 读取函数
        self.adder_func = adder_func       # 添加函数
        self.updater_func = updater_func    # 更新函数
        self.deleter_func = deleter_func    # 删除函数
        self.generator_func = generator_func # AI生成函数
        self.description_key = description_key # 描述字段键名


# 预定义实体配置
ENTITY_CONFIGS = {
    "characters": EntityConfig(
        name="角色",
        plural_name="角色",
        data_key="characters",
        reader_func=data_manager.read_characters,
        adder_func=data_manager.add_character,
        updater_func=data_manager.update_character,
        deleter_func=data_manager.delete_character,
        generator_func=llm_service.generate_character_description
    ),
    "locations": EntityConfig(
        name="场景",
        plural_name="场景",
        data_key="locations",
        reader_func=data_manager.read_locations,
        adder_func=data_manager.add_location,
        updater_func=data_manager.update_location,
        deleter_func=data_manager.delete_location,
        generator_func=llm_service.generate_location_description
    ),
    "items": EntityConfig(
        name="道具",
        plural_name="道具",
        data_key="items",
        reader_func=data_manager.read_items,
        adder_func=data_manager.add_item,
        updater_func=data_manager.update_item,
        deleter_func=data_manager.delete_item,
        generator_func=llm_service.generate_item_description
    )
}


class EntityManager:
    """通用实体管理器"""
    
    def __init__(self, entity_config):
        self.config = entity_config
    
    def handle_entity_management(self):
        """处理实体管理的主循环"""
        while True:
            # 每次循环重新读取数据
            entities_data = self.config.reader_func()
            
            # 显示当前实体列表
            self._display_entity_list(entities_data)
            
            # 获取操作选项
            choices = self._get_menu_choices(entities_data)
            
            action = questionary.select(
                "请选择您要进行的操作：",
                choices=choices,
                use_indicator=True
            ).ask()
            
            if action is None:
                break
            elif action.startswith("1."):
                # 添加新实体
                self._add_entity()
            elif action.startswith("2.") and entities_data:
                # 查看实体详情
                self._view_entity()
            elif action.startswith("2.") and not entities_data:
                # 返回上级菜单（当没有实体时）
                break
            elif action.startswith("3."):
                # 修改实体信息
                self._edit_entity()
            elif action.startswith("4."):
                # 删除实体
                self._delete_entity()
            elif action.startswith("5.") or action.startswith("2."):
                # 返回上级菜单
                break
    
    def _display_entity_list(self, entities_data):
        """显示实体列表"""
        if entities_data:
            print(f"\n--- 当前{self.config.plural_name}列表 ---")
            for i, (entity_name, entity_info) in enumerate(entities_data.items(), 1):
                description = entity_info.get(self.config.description_key, '无描述')
                truncated_desc = description[:50] + ('...' if len(description) > 50 else '')
                print(f"{i}. {entity_name}: {truncated_desc}")
            print("------------------------\n")
        else:
            print(f"\n当前没有{self.config.plural_name}信息。\n")
    
    def _get_menu_choices(self, entities_data):
        """获取菜单选项"""
        if entities_data:
            return [
                f"1. 添加新{self.config.name}",
                f"2. 查看{self.config.name}详情",
                f"3. 修改{self.config.name}信息",
                f"4. 删除{self.config.name}",
                "5. 返回上级菜单"
            ]
        else:
            return [
                f"1. 添加新{self.config.name}",
                "2. 返回上级菜单"
            ]
    
    def _add_entity(self):
        """添加新实体"""
        print(f"\n--- 添加新{self.config.name} ---")
        print(f"请输入{self.config.name}信息（可以是名称、JSON格式、或任何描述）")
        print(f"AI会自动理解您的输入并生成标准的{self.config.name}描述。")
        
        user_input = questionary.text(f"请输入{self.config.name}信息:").ask()
        if not user_input or not user_input.strip():
            print(f"{self.config.name}信息不能为空。\n")
            return
        
        user_input = user_input.strip()
        
        # 构造给LLM的提示词，让LLM自己解析输入并返回标准格式
        llm_prompt = f"""用户想要创建一个{self.config.name}，提供的信息如下：
{user_input}

请基于这些信息生成{self.config.name}描述。如果用户提供了JSON格式或结构化信息，请解析其中的内容。
如果只提供了名称，请基于名称创造合适的{self.config.name}描述。

请按以下JSON格式返回：
{{
  "name": "{self.config.name}名称",
  "description": "详细的{self.config.name}描述"
}}"""
        
        print(f"正在调用 AI 解析并生成{self.config.name}信息，请稍候...")
        
        # 使用JSON请求方法获取结构化结果
        if hasattr(self.config, 'json_generator_func'):
            ai_result = self.config.json_generator_func(llm_prompt)
        else:
            # 临时使用字符描述生成器
            ai_response = self.config.generator_func("", llm_prompt)
            if not ai_response:
                print("AI生成失败，请稍后重试。")
                return
            
            # 尝试从响应中提取JSON
            import json
            import re
            try:
                # 尝试提取JSON
                json_match = re.search(r'\{.*\}', ai_response, re.DOTALL)
                if json_match:
                    ai_result = json.loads(json_match.group(0))
                else:
                    # 如果没有找到JSON，使用原始输入作为名称
                    entity_name = user_input.split(',')[0].strip().strip('"').split(':')[-1].strip()
                    ai_result = {"name": entity_name, "description": ai_response}
            except:
                # JSON解析失败，使用原始输入作为名称
                entity_name = user_input.split(',')[0].strip().strip('"').split(':')[-1].strip()
                ai_result = {"name": entity_name, "description": ai_response}
        
        if not ai_result:
            print("AI生成失败，请稍后重试。")
            return
        
        # 提取角色名称和描述
        entity_name = ai_result.get("name", "未知").strip()
        generated_description = ai_result.get("description", "").strip()
        
        if not entity_name or not generated_description:
            print("AI返回的数据格式不完整，请重试。")
            return
        
        # 检查是否已存在
        entities_data = self.config.reader_func()
        if entity_name in entities_data:
            print(f"{self.config.name} '{entity_name}' 已存在。\n")
            return
        
        print(f"\n--- AI 生成的{self.config.name}：{entity_name} ---")
        print(generated_description)
        print("------------------------\n")
        
        # 提供操作选项
        action = questionary.select(
            "请选择您要进行的操作：",
            choices=[
                "1. 接受并保存",
                "2. 修改后保存",
                "3. 放弃此次生成"
            ],
            use_indicator=True
        ).ask()

        if action is None or action.startswith("3."):
            print("已放弃此次生成。\n")
            return
        elif action.startswith("1."):
            # 直接保存
            if self.config.adder_func(entity_name, generated_description):
                print(f"{self.config.name} '{entity_name}' 已保存。\n")
            else:
                print(f"保存{self.config.name}时出错。\n")
        elif action.startswith("2."):
            # 修改后保存
            edited_description = questionary.text(
                f"请修改{self.config.name}描述:",
                default=generated_description,
                multiline=True
            ).ask()

            if edited_description and edited_description.strip():
                if self.config.adder_func(entity_name, edited_description):
                    print(f"{self.config.name} '{entity_name}' 已保存。\n")
                else:
                    print(f"保存{self.config.name}时出错。\n")
            else:
                print("操作已取消或内容为空，未保存。\n")
    
    def _view_entity(self):
        """查看实体详情"""
        entities_data = self.config.reader_func()
        if not entities_data:
            print(f"\n当前没有{self.config.plural_name}信息。\n")
            return
            
        entity_names = list(entities_data.keys())
        entity_name = questionary.select(
            f"请选择要查看的{self.config.name}：",
            choices=entity_names,
            use_indicator=True
        ).ask()
        
        if entity_name:
            entity_info = entities_data[entity_name]
            print(f"\n--- {self.config.name}详情：{entity_name} ---")
            print(entity_info.get(self.config.description_key, '无描述'))
            print("------------------------\n")
    
    def _edit_entity(self):
        """编辑实体信息"""
        entities_data = self.config.reader_func()
        if not entities_data:
            print(f"\n当前没有{self.config.plural_name}信息可编辑。\n")
            return
            
        entity_names = list(entities_data.keys())
        entity_name = questionary.select(
            f"请选择要修改的{self.config.name}：",
            choices=entity_names,
            use_indicator=True
        ).ask()
        
        if not entity_name:
            return
        
        current_description = entities_data[entity_name].get(self.config.description_key, '')
        print(f"\n--- 当前{self.config.name}描述：{entity_name} ---")
        print(current_description)
        print("------------------------\n")
        
        edited_description = questionary.text(
            f"请修改{self.config.name}描述:",
            default=current_description,
            multiline=True
        ).ask()
        
        if edited_description and edited_description.strip() and edited_description != current_description:
            if self.config.updater_func(entity_name, edited_description):
                print(f"{self.config.name} '{entity_name}' 已更新。\n")
            else:
                print(f"更新{self.config.name}时出错。\n")
        elif edited_description is None:
            print("操作已取消。\n")
        else:
            print("内容未更改。\n")
    
    def _delete_entity(self):
        """删除实体"""
        entities_data = self.config.reader_func()
        if not entities_data:
            print(f"\n当前没有{self.config.plural_name}信息可删除。\n")
            return
            
        entity_names = list(entities_data.keys())
        entity_name = questionary.select(
            f"请选择要删除的{self.config.name}：",
            choices=entity_names,
            use_indicator=True
        ).ask()
        
        if not entity_name:
            return
        
        confirm = questionary.confirm(f"确定要删除{self.config.name} '{entity_name}' 吗？").ask()
        if confirm:
            if self.config.deleter_func(entity_name):
                print(f"{self.config.name} '{entity_name}' 已删除。\n")
            else:
                print(f"删除{self.config.name}时出错。\n")
        else:
            print("操作已取消。\n")


# 创建预定义的实体管理器实例
character_manager = EntityManager(ENTITY_CONFIGS["characters"])
location_manager = EntityManager(ENTITY_CONFIGS["locations"])
item_manager = EntityManager(ENTITY_CONFIGS["items"])


# 提供便捷的接口函数
def handle_characters():
    """处理角色管理"""
    character_manager.handle_entity_management()


def handle_locations():
    """处理场景管理"""
    location_manager.handle_entity_management()


def handle_items():
    """处理道具管理"""
    item_manager.handle_entity_management() 