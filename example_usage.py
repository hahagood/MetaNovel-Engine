#!/usr/bin/env python3
"""
MetaNovel Engine 新功能使用示例
展示如何使用 Pydantic 数据模型和 Rich UI 界面
"""

from models import Character, Location, ChapterOutline, Chapter, ProjectData, model_to_dict
from ui_utils import ui, console
from data_manager import DataManager

def demo_rich_ui():
    """演示Rich UI功能"""
    ui.print_title("🎨 Rich UI 演示")
    
    # 欢迎信息
    ui.print_welcome()
    
    # 不同类型的消息
    ui.print_success("操作成功完成！")
    ui.print_warning("请注意：这是一个警告信息")
    ui.print_info("提示：这是一些有用的信息")
    ui.print_error("错误：操作失败")
    
    # 美观的面板
    ui.print_panel(
        "这是一个信息面板\n包含多行内容\n支持各种样式",
        title="信息面板",
        style="cyan"
    )

def demo_pydantic_models():
    """演示Pydantic数据模型"""
    ui.print_title("🔧 Pydantic 数据模型演示")
    
    # 创建角色
    hero = Character(
        name="艾莉亚",
        description="勇敢的女战士，擅长剑术和魔法"
    )
    
    villain = Character(
        name="暗影领主",
        description="邪恶的黑暗法师，企图统治世界"
    )
    
    ui.print_success(f"创建角色: {hero.name}")
    ui.print_success(f"创建角色: {villain.name}")
    
    # 创建场景
    castle = Location(
        name="月光城堡",
        description="古老的城堡，坐落在山巅，被月光笼罩"
    )
    
    ui.print_success(f"创建场景: {castle.name}")
    
    # 创建章节
    chapter1 = Chapter(
        title="命运的召唤",
        outline="艾莉亚接受了拯救世界的使命，踏上了冒险之路",
        order=1
    )
    
    chapter2 = Chapter(
        title="月光城堡",
        outline="艾莉亚抵达月光城堡，发现了暗影领主的阴谋",
        order=2
    )
    
    ui.print_success(f"创建章节: {chapter1.title}")
    ui.print_success(f"创建章节: {chapter2.title}")
    
    # 创建章节大纲
    outline = ChapterOutline()
    outline.chapters = [chapter1, chapter2]
    outline.total_chapters = len(outline.chapters)
    
    ui.print_success(f"创建章节大纲，包含 {len(outline)} 个章节")
    
    # 创建项目数据
    project = ProjectData()
    project.world_settings.characters[hero.name] = hero
    project.world_settings.characters[villain.name] = villain
    project.world_settings.locations[castle.name] = castle
    project.chapter_outline = outline
    
    ui.print_success("创建完整项目数据模型")
    
    # 显示项目状态
    ui.print_project_status(project.completion_status)
    
    return project

def demo_data_manager():
    """演示数据管理器功能"""
    ui.print_title("💾 数据管理器演示")
    
    dm = DataManager()
    
    # 使用统一CRUD接口
    ui.print_subtitle("使用统一CRUD接口")
    
    # 添加角色
    success = dm.add_character("示例角色", "这是一个示例角色")
    if success:
        ui.print_success("添加角色成功")
    
    # 读取角色
    characters = dm.read_characters()
    if characters:
        ui.print_characters_table(characters)
    
    # 更新角色
    success = dm.update_character("示例角色", "这是更新后的示例角色")
    if success:
        ui.print_success("更新角色成功")
    
    # 清理演示数据
    dm.delete_character("示例角色")
    ui.print_info("清理演示数据完成")

def demo_integration():
    """演示集成使用"""
    ui.print_title("🔗 集成使用演示")
    
    ui.print_subtitle("Pydantic + Rich + DataManager 集成")
    
    # 创建Pydantic模型
    character = Character(
        name="集成示例角色",
        description="展示Pydantic与其他组件集成的角色"
    )
    
    # 使用Rich显示
    ui.print_success(f"创建Pydantic角色: {character.name}")
    ui.print_json(model_to_dict(character), "角色数据")
    
    # 保存到数据管理器
    dm = DataManager()
    success = dm.add_character(character.name, character.description)
    
    if success:
        ui.print_success("Pydantic模型成功保存到数据管理器")
        
        # 读取并用Rich显示
        saved_characters = dm.read_characters()
        ui.print_characters_table(saved_characters)
        
        # 清理
        dm.delete_character(character.name)
        ui.print_info("清理集成示例数据完成")

def main():
    """主演示函数"""
    console.print("\n" + "="*70, style="bold magenta")
    ui.print_title("🚀 MetaNovel Engine 新功能演示")
    console.print("="*70 + "\n", style="bold magenta")
    
    # 运行各个演示
    demo_rich_ui()
    ui.print_separator()
    
    project = demo_pydantic_models()
    ui.print_separator()
    
    demo_data_manager()
    ui.print_separator()
    
    demo_integration()
    ui.print_separator()
    
    # 总结
    ui.print_title("✨ 演示完成")
    
    summary_text = """
## 🎯 新功能总结

### 1. Pydantic 数据模型
- **类型安全**: 自动验证数据类型
- **数据验证**: 确保数据格式正确
- **自动文档**: IDE自动补全支持
- **时间戳管理**: 自动记录创建和更新时间

### 2. Rich UI 界面
- **美观表格**: 角色、场景、章节列表展示
- **彩色消息**: 成功、警告、错误、信息提示
- **面板组件**: 信息框、进度条、菜单
- **Markdown支持**: 格式化文本显示

### 3. 统一数据访问
- **CRUD接口**: 统一的增删改查方法
- **减少重复**: 消除重复代码
- **一致性**: 所有数据操作使用相同模式
- **可维护性**: 更容易维护和扩展

### 🌟 这些改进让MetaNovel Engine更加：
- **专业** - 企业级的代码质量
- **美观** - 现代化的用户界面
- **健壮** - 类型安全和数据验证
- **易用** - 一致的API设计
    """
    
    ui.print_markdown(summary_text)
    
    ui.print_success("🎉 所有新功能演示完成！")
    ui.print_goodbye()

if __name__ == "__main__":
    main() 