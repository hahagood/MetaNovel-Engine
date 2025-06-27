"""
数据模型定义 - 使用Pydantic进行数据验证和类型安全
"""

from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Optional, Any
from datetime import datetime
import json


class Character(BaseModel):
    """角色数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    name: str = Field(..., description="角色姓名")
    description: str = Field(..., description="角色描述")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class Location(BaseModel):
    """场景数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    name: str = Field(..., description="场景名称")
    description: str = Field(..., description="场景描述")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class Item(BaseModel):
    """道具数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    name: str = Field(..., description="道具名称")
    description: str = Field(..., description="道具描述")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class Chapter(BaseModel):
    """章节数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    title: str = Field(..., description="章节标题")
    outline: str = Field(..., description="章节大纲")
    order: int = Field(..., description="章节序号")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class ChapterSummary(BaseModel):
    """章节概要数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    chapter_num: int = Field(..., description="章节编号")
    title: str = Field(..., description="章节标题")
    summary: str = Field(..., description="章节概要")
    word_count: Optional[int] = Field(default=0, description="字数统计")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class NovelChapter(BaseModel):
    """小说章节数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    chapter_num: int = Field(..., description="章节编号")
    title: str = Field(..., description="章节标题")
    content: str = Field(..., description="章节内容")
    word_count: Optional[int] = Field(default=0, description="字数统计")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="更新时间")


class ThemeOneLine(BaseModel):
    """一句话主题数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    theme: str = Field(..., description="一句话主题")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class ThemeParagraph(BaseModel):
    """段落主题数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    theme: str = Field(..., description="段落主题")
    based_on: Optional[str] = Field(default=None, description="基于的一句话主题")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class StoryOutline(BaseModel):
    """故事大纲数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()},
        str_strip_whitespace=True
    )
    
    title: str = Field(..., description="故事标题")
    outline: str = Field(..., description="故事大纲")
    word_count: Optional[int] = Field(default=0, description="字数统计")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")


class ChapterOutline(BaseModel):
    """分章细纲数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )
    
    chapters: List[Chapter] = Field(default_factory=list, description="章节列表")
    total_chapters: Optional[int] = Field(default=0, description="总章节数")
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="创建时间")
    
    def __len__(self):
        return len(self.chapters)


class WorldSettings(BaseModel):
    """世界设定数据模型"""
    characters: Dict[str, Character] = Field(default_factory=dict, description="角色设定")
    locations: Dict[str, Location] = Field(default_factory=dict, description="场景设定")
    items: Dict[str, Item] = Field(default_factory=dict, description="道具设定")
    
    @property
    def character_count(self) -> int:
        return len(self.characters)
    
    @property
    def location_count(self) -> int:
        return len(self.locations)
    
    @property
    def item_count(self) -> int:
        return len(self.items)


class ProjectData(BaseModel):
    """项目完整数据模型"""
    model_config = ConfigDict(
        json_encoders={datetime: lambda dt: dt.isoformat()}
    )
    
    theme_one_line: Optional[ThemeOneLine] = None
    theme_paragraph: Optional[ThemeParagraph] = None
    story_outline: Optional[StoryOutline] = None
    chapter_outline: Optional[ChapterOutline] = None
    world_settings: WorldSettings = Field(default_factory=WorldSettings)
    chapter_summaries: Dict[int, ChapterSummary] = Field(default_factory=dict)
    novel_chapters: Dict[int, NovelChapter] = Field(default_factory=dict)
    created_at: Optional[datetime] = Field(default_factory=datetime.now, description="项目创建时间")
    updated_at: Optional[datetime] = Field(default_factory=datetime.now, description="最后更新时间")
    
    @property
    def completion_status(self) -> Dict[str, bool]:
        """获取项目完成状态"""
        return {
            "theme_one_line": self.theme_one_line is not None,
            "theme_paragraph": self.theme_paragraph is not None,
            "story_outline": self.story_outline is not None,
            "chapter_outline": self.chapter_outline is not None and len(self.chapter_outline.chapters) > 0,
            "world_settings": (self.world_settings.character_count > 0 or 
                             self.world_settings.location_count > 0 or 
                             self.world_settings.item_count > 0),
            "chapter_summaries": len(self.chapter_summaries) > 0,
            "novel_chapters": len(self.novel_chapters) > 0
        }
    
    @property
    def total_word_count(self) -> int:
        """计算总字数"""
        return sum(chapter.word_count or 0 for chapter in self.novel_chapters.values())


# 工具函数
def validate_json_data(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """验证JSON数据并转换为Pydantic模型"""
    try:
        return model_class(**data)
    except Exception as e:
        raise ValueError(f"数据验证失败: {e}")


def model_to_dict(model: BaseModel) -> Dict[str, Any]:
    """将Pydantic模型转换为字典（支持datetime序列化）"""
    return json.loads(model.model_dump_json())


def dict_to_model(data: Dict[str, Any], model_class: BaseModel) -> BaseModel:
    """将字典转换为Pydantic模型"""
    return model_class(**data) 