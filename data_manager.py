import json
from pathlib import Path
from config import FILE_PATHS, ensure_directories, get_project_paths
from datetime import datetime
from typing import Optional, Dict
import time

class DataManager:
    """数据管理类，封装所有文件读写操作"""
    
    def __init__(self, project_path: Optional[Path] = None):
        """
        初始化数据管理器
        
        Args:
            project_path: 项目路径，如果为None则使用默认路径（单项目模式）
        """
        self.project_path = project_path
        self.file_paths = get_project_paths(project_path)
        ensure_directories(project_path)
        
        # 添加状态缓存
        self._status_cache = None
        self._status_cache_time = None
        self._cache_ttl = 2  # 缓存2秒
    
    def _clear_status_cache(self):
        """清除状态缓存"""
        self._status_cache = None
        self._status_cache_time = None
    
    def get_path(self, key):
        """获取指定类型文件的路径"""
        return self.file_paths.get(key)
    
    def read_json_file(self, file_path):
        """读取JSON文件"""
        try:
            if file_path.exists():
                with file_path.open('r', encoding='utf-8') as f:
                    return json.load(f)
            return {}
        except (json.JSONDecodeError, IOError) as e:
            # 静默处理文件读取错误，避免在启动时显示错误信息
            return {}
    
    def write_json_file(self, file_path, data):
        """写入JSON文件"""
        try:
            with file_path.open('w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)
            # 清除缓存，因为数据可能已更改
            self._clear_status_cache()
            return True
        except IOError as e:
            # 静默处理文件写入错误，避免在启动时显示错误信息
            return False
    
    # ===== 通用CRUD方法 =====
    def add_item_to_dict(self, file_path, key, value):
        """向字典类型的JSON文件添加项目"""
        data = self.read_json_file(file_path)
        # 添加时间戳
        if isinstance(value, dict):
            value["created_at"] = datetime.now().isoformat()
        data[key] = value
        return self.write_json_file(file_path, data)
    
    def update_item_in_dict(self, file_path, key, value):
        """更新字典类型的JSON文件中的项目"""
        data = self.read_json_file(file_path)
        if key in data:
            # 保留原创建时间，更新修改时间
            if isinstance(value, dict) and isinstance(data[key], dict):
                value["created_at"] = data[key].get("created_at", datetime.now().isoformat())
                value["updated_at"] = datetime.now().isoformat()
            data[key] = value
            return self.write_json_file(file_path, data)
        return False
    
    def delete_item_from_dict(self, file_path, key):
        """从字典类型的JSON文件删除项目"""
        data = self.read_json_file(file_path)
        if key in data:
            del data[key]
            return self.write_json_file(file_path, data)
        return False
    
    def get_item_from_dict(self, file_path, key):
        """从字典类型的JSON文件获取项目"""
        data = self.read_json_file(file_path)
        return data.get(key, None)
    
    def list_items_in_dict(self, file_path):
        """列出字典类型的JSON文件中的所有项目"""
        return self.read_json_file(file_path)
    
    # ===== 主题相关 =====
    def read_theme_one_line(self):
        """读取一句话主题数据（支持新旧格式）"""
        data = self.read_json_file(self.file_paths["theme_one_line"])
        
        # 如果文件不存在或为空，返回None
        if not data:
            return None
        
        # 如果是新格式（包含novel_name和theme的字典），直接返回
        if isinstance(data, dict) and ("novel_name" in data or "theme" in data):
            return data
        
        # 如果是旧格式（只有theme字段的字典），转换为新格式
        if isinstance(data, dict) and "theme" in data:
            return data
        
        # 如果是字符串格式（更旧的版本），转换为新格式
        if isinstance(data, str):
            return data
        
        # 其他情况返回空字符串
        return ""
    
    def write_theme_one_line(self, data):
        """写入一句话主题数据（支持字符串和字典格式）"""
        if isinstance(data, str):
            # 如果传入的是字符串，保存为主题内容
            save_data = {
                "theme": data,
                "created_at": datetime.now().isoformat()
            }
        elif isinstance(data, dict):
            # 如果传入的是字典，保持原有结构并添加时间戳
            save_data = data.copy()
            save_data["created_at"] = datetime.now().isoformat()
        else:
            return False
        
        return self.write_json_file(self.file_paths["theme_one_line"], save_data)
    
    def read_theme_paragraph(self):
        """读取段落主题"""
        data = self.read_json_file(self.file_paths["theme_paragraph"])
        return data.get("theme_paragraph", "")
    
    def write_theme_paragraph(self, theme_paragraph):
        """写入段落主题"""
        data = {
            "theme_paragraph": theme_paragraph,
            "created_at": datetime.now().isoformat()
        }
        return self.write_json_file(self.file_paths["theme_paragraph"], data)
    
    def delete_theme_paragraph(self):
        """删除段落主题"""
        return self.write_json_file(self.file_paths["theme_paragraph"], {})
    
    # ===== 角色相关 =====
    def read_characters(self):
        """读取所有角色"""
        return self.list_items_in_dict(self.file_paths["characters"])
    
    def write_characters(self, characters_data):
        """写入角色数据"""
        return self.write_json_file(self.file_paths["characters"], characters_data)
    
    def add_character(self, name, description):
        """添加角色"""
        return self.add_item_to_dict(
            self.file_paths["characters"],
            name,
            {"description": description}
        )

    def update_character(self, name, description):
        """更新角色"""
        return self.update_item_in_dict(
            self.file_paths["characters"],
            name,
            {"description": description}
        )

    def delete_character(self, name):
        """删除角色"""
        return self.delete_item_from_dict(self.file_paths["characters"], name)

    # ===== 场景相关 =====
    def read_locations(self):
        """读取所有场景"""
        return self.list_items_in_dict(self.file_paths["locations"])
    
    def write_locations(self, locations_data):
        """写入场景数据"""
        return self.write_json_file(self.file_paths["locations"], locations_data)
    
    def add_location(self, name, description):
        """添加场景"""
        return self.add_item_to_dict(
            self.file_paths["locations"],
            name,
            {"description": description}
        )

    def update_location(self, name, description):
        """更新场景"""
        return self.update_item_in_dict(
            self.file_paths["locations"],
            name,
            {"description": description}
        )

    def delete_location(self, name):
        """删除场景"""
        return self.delete_item_from_dict(self.file_paths["locations"], name)
    
    # ===== 道具相关 =====
    def read_items(self):
        """读取所有道具"""
        return self.list_items_in_dict(self.file_paths["items"])
    
    def write_items(self, items_data):
        """写入道具数据"""
        return self.write_json_file(self.file_paths["items"], items_data)
    
    def add_item(self, name, description):
        """添加道具"""
        return self.add_item_to_dict(
            self.file_paths["items"],
            name,
            {"description": description}
        )

    def update_item(self, name, description):
        """更新道具"""
        return self.update_item_in_dict(
            self.file_paths["items"],
            name,
            {"description": description}
        )

    def delete_item(self, name):
        """删除道具"""
        return self.delete_item_from_dict(self.file_paths["items"], name)
    
    # ===== 故事大纲相关 =====
    def read_story_outline(self):
        """读取故事大纲"""
        data = self.read_json_file(self.file_paths["story_outline"])
        return data.get("outline", "")
    
    def write_story_outline(self, outline):
        """写入故事大纲"""
        data = {
            "outline": outline,
            "created_at": datetime.now().isoformat(),
            "word_count": len(outline)
        }
        return self.write_json_file(self.file_paths["story_outline"], data)
    
    def delete_story_outline(self):
        """删除故事大纲"""
        return self.write_json_file(self.file_paths["story_outline"], {})
    
    # ===== 分章细纲相关 =====
    def read_chapter_outline(self):
        """读取分章细纲"""
        data = self.read_json_file(self.file_paths["chapter_outline"])
        return data.get("chapters", [])
    
    def write_chapter_outline(self, chapters):
        """写入分章细纲"""
        data = {
            "chapters": chapters,
            "total_chapters": len(chapters),
            "created_at": datetime.now().isoformat()
        }
        return self.write_json_file(self.file_paths["chapter_outline"], data)
    
    def delete_chapter_outline(self):
        """删除分章细纲"""
        return self.write_json_file(self.file_paths["chapter_outline"], {})
    
    # ===== 章节概要相关 =====
    def read_chapter_summaries(self):
        """读取所有章节概要"""
        data = self.read_json_file(self.file_paths["chapter_summary"])
        return data.get("summaries", {})
    
    def write_chapter_summaries(self, summaries):
        """写入章节概要"""
        data = {"summaries": summaries}
        return self.write_json_file(self.file_paths["chapter_summary"], data)
    
    def get_chapter_summary(self, chapter_num):
        """获取单个章节概要"""
        summaries = self.read_chapter_summaries()
        chapter_key = f"chapter_{chapter_num}"
        return summaries.get(chapter_key, {})
    
    def set_chapter_summary(self, chapter_num, title, summary):
        """设置单个章节概要"""
        summaries = self.read_chapter_summaries()
        chapter_key = f"chapter_{chapter_num}"
        summaries[chapter_key] = {"title": title, "summary": summary}
        return self.write_chapter_summaries(summaries)
    
    def delete_chapter_summary(self, chapter_num):
        """删除单个章节概要"""
        summaries = self.read_chapter_summaries()
        chapter_key = f"chapter_{chapter_num}"
        if chapter_key in summaries:
            del summaries[chapter_key]
            return self.write_chapter_summaries(summaries)
        return False
    
    # ===== 小说正文相关 =====
    def read_novel_chapters(self):
        """读取所有小说章节"""
        data = self.read_json_file(self.file_paths["novel_text"])
        return data.get("chapters", {})
    
    def write_novel_chapters(self, chapters):
        """写入小说章节"""
        data = {"chapters": chapters}
        return self.write_json_file(self.file_paths["novel_text"], data)
    
    def get_novel_chapter(self, chapter_num):
        """获取单个小说章节"""
        chapters = self.read_novel_chapters()
        chapter_key = f"chapter_{chapter_num}"
        return chapters.get(chapter_key, {})
    
    def set_novel_chapter(self, chapter_num, title, content):
        """设置单个小说章节"""
        chapters = self.read_novel_chapters()
        chapter_key = f"chapter_{chapter_num}"
        chapters[chapter_key] = {
            "title": title,
            "content": content,
            "word_count": len(content)
        }
        return self.write_novel_chapters(chapters)
    
    def delete_novel_chapter(self, chapter_num):
        """删除单个小说章节"""
        chapters = self.read_novel_chapters()
        chapter_key = f"chapter_{chapter_num}"
        if chapter_key in chapters:
            del chapters[chapter_key]
            return self.write_novel_chapters(chapters)
        return False
    
    # ===== 综合信息获取 =====
    def get_context_info(self):
        """获取上下文信息，用于AI生成"""
        context_parts = []
        
        # 读取主题信息
        theme = self.read_theme_one_line()
        if theme:
            context_parts.append(f"主题：{theme}")
        
        # 读取角色信息
        characters_data = self.read_characters()
        if characters_data:
            context_parts.append("主要角色：")
            for char_name, char_data in characters_data.items():
                context_parts.append(f"- {char_name}: {char_data.get('description', '无描述')}")
        
        # 读取场景信息
        locations_data = self.read_locations()
        if locations_data:
            context_parts.append("重要场景：")
            for loc_name, loc_data in locations_data.items():
                context_parts.append(f"- {loc_name}: {loc_data.get('description', '无描述')}")
        
        # 读取道具信息
        items_data = self.read_items()
        if items_data:
            context_parts.append("重要道具：")
            for item_name, item_data in items_data.items():
                context_parts.append(f"- {item_name}: {item_data.get('description', '无描述')}")
        
        # 读取故事大纲
        outline = self.read_story_outline()
        if outline:
            context_parts.append(f"故事大纲：{outline}")
        
        return "\n".join(context_parts)
    
    def get_characters_info_string(self):
        """获取角色信息字符串，用于AI生成"""
        characters_data = self.read_characters()
        if not characters_data:
            return ""
        
        characters_info = "\n\n已有角色信息：\n"
        for char_name, char_data in characters_data.items():
            characters_info += f"- {char_name}: {char_data.get('description', '无描述')}\n"
        
        return characters_info
    
    # ===== 前置条件检查 =====
    def check_prerequisites_for_world_setting(self):
        """检查世界设定的前置条件"""
        one_line_exists = self.file_paths["theme_one_line"].exists()
        paragraph_exists = self.file_paths["theme_paragraph"].exists()
        return one_line_exists, paragraph_exists
    
    def check_prerequisites_for_story_outline(self):
        """检查故事大纲的前置条件"""
        one_line_exists = self.file_paths["theme_one_line"].exists()
        paragraph_exists = self.file_paths["theme_paragraph"].exists()
        return one_line_exists, paragraph_exists
    
    def check_prerequisites_for_chapter_outline(self):
        """检查分章细纲的前置条件"""
        return self.file_paths["story_outline"].exists()
    
    def check_prerequisites_for_chapter_summary(self):
        """检查章节概要的前置条件"""
        return self.file_paths["chapter_outline"].exists()
    
    def check_prerequisites_for_novel_generation(self):
        """检查小说生成的前置条件"""
        return self.file_paths["chapter_summary"].exists()
    
    # ===== 小说正文相关 =====
    def read_novel_chapters(self):
        """读取小说正文数据"""
        data = self.read_json_file(self.file_paths["novel_text"])
        return data.get("chapters", {})
    
    def write_novel_chapters(self, chapters_data):
        """写入小说正文数据"""
        data = {"chapters": chapters_data}
        return self.write_json_file(self.file_paths["novel_text"], data)
    
    def set_novel_chapter(self, chapter_num, title, content):
        """设置单个章节的正文"""
        chapters = self.read_novel_chapters()
        chapter_key = f"chapter_{chapter_num}"
        chapters[chapter_key] = {
            "title": title,
            "content": content,
            "word_count": len(content)
        }
        return self.write_novel_chapters(chapters)
    
    def delete_novel_chapter(self, chapter_num):
        """删除单个章节的正文"""
        chapters = self.read_novel_chapters()
        chapter_key = f"chapter_{chapter_num}"
        if chapter_key in chapters:
            del chapters[chapter_key]
            return self.write_novel_chapters(chapters)
        return False

    def get_project_status_details(self) -> Dict[str, Dict]:
        """获取项目各阶段的详细完成状态（带缓存）"""
        current_time = time.time()
        
        # 检查缓存是否有效
        if (self._status_cache is not None and 
            self._status_cache_time is not None and
            current_time - self._status_cache_time < self._cache_ttl):
            return self._status_cache
            
        # 重新计算状态
        status = self._calculate_project_status_details()
        
        # 更新缓存
        self._status_cache = status
        self._status_cache_time = current_time
        
        return status
    
    def _calculate_project_status_details(self) -> Dict[str, Dict]:
        """计算项目各阶段的详细完成状态"""
        # 快速预检查：如果没有任何meta文件，直接返回空状态
        meta_files = [
            self.file_paths['theme_one_line'],
            self.file_paths['theme_paragraph'], 
            self.file_paths['characters'],
            self.file_paths['locations'],
            self.file_paths['items'],
            self.file_paths['story_outline'],
            self.file_paths['chapter_outline'],
            self.file_paths['chapter_summary'],  # 修复：使用正确的键名
            self.file_paths['novel_text']        # 修复：使用正确的键名
        ]
        
        # 如果没有任何文件存在，返回默认状态（避免多次文件访问）
        if not any(Path(f).exists() for f in meta_files):
            return {
                "theme_one_line": {"completed": False, "details": "未设置"},
                "theme_paragraph": {"completed": False, "details": "未生成"},
                "world_settings": {"completed": False, "details": "未设定"},
                "story_outline": {"completed": False, "details": "未生成"},
                "chapter_outline": {"completed": False, "details": "未生成"},
                "chapter_summaries": {"completed": False, "details": "未生成"},
                "novel_chapters": {"completed": False, "details": "未生成"}
            }
        
        # 正常详细检查
        status = {}

        # 1. 小说名称与主题
        theme_data = self.read_theme_one_line()
        if theme_data and (theme_data.get("theme") or (isinstance(theme_data, str) and theme_data)):
            status["theme_one_line"] = {"completed": True, "details": "已设置"}
        else:
            status["theme_one_line"] = {"completed": False, "details": "未设置"}

        # 2. 段落主题
        paragraph = self.read_theme_paragraph()
        if paragraph:
            status["theme_paragraph"] = {"completed": True, "details": f"已生成，{len(paragraph)}字"}
        else:
            status["theme_paragraph"] = {"completed": False, "details": "未生成"}

        # 3. 世界设定
        characters = self.read_characters()
        locations = self.read_locations()
        items = self.read_items()
        ws_details = []
        if characters: ws_details.append(f"角色({len(characters)})")
        if locations: ws_details.append(f"场景({len(locations)})")  
        if items: ws_details.append(f"道具({len(items)})")
        if ws_details:
            status["world_settings"] = {"completed": True, "details": "、".join(ws_details)}
        else:
            status["world_settings"] = {"completed": False, "details": "未设定"}
            
        # 4. 故事大纲
        outline = self.read_story_outline()
        if outline:
            status["story_outline"] = {"completed": True, "details": f"已生成，{len(outline)}字"}
        else:
            status["story_outline"] = {"completed": False, "details": "未生成"}
            
        # 5. 分章细纲
        chapters = self.read_chapter_outline()
        if chapters:
            status["chapter_outline"] = {"completed": True, "details": f"共 {len(chapters)} 章"}
        else:
            status["chapter_outline"] = {"completed": False, "details": "未生成"}
            
        # 6. 章节概要
        summaries = self.read_chapter_summaries()
        if summaries:
            status["chapter_summaries"] = {"completed": True, "details": f"已生成 {len(summaries)}/{len(chapters) if chapters else '?'} 章"}
        else:
            status["chapter_summaries"] = {"completed": False, "details": "未生成"}
            
        # 7. 小说正文
        novel_chapters = self.read_novel_chapters()
        if novel_chapters:
            total_words = sum(ch.get('word_count', 0) for ch in novel_chapters.values())
            status["novel_chapters"] = {"completed": True, "details": f"已生成 {len(novel_chapters)} 章，共 {total_words} 字"}
        else:
            status["novel_chapters"] = {"completed": False, "details": "未生成"}
            
        return status

# 创建全局数据管理实例
data_manager = DataManager() 