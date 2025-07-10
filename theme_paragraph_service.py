"""
主题段落服务模块
负责主题分析、作品类型推荐、主题段落生成等功能
"""

import json
from typing import Dict, List, Optional, Tuple
from ui_utils import ui, console
from rich.panel import Panel
from rich.text import Text
from llm_service import llm_service
from project_data_manager import project_data_manager


class ThemeParagraphService:
    """主题段落服务类"""
    
    def __init__(self):
        self.data_manager = project_data_manager.get_data_manager()
    
    def analyze_theme_and_get_genres(self, one_line_theme: str) -> Optional[Dict]:
        """分析主题并获取推荐的作品类型"""
        if not llm_service.is_available():
            ui.print_error("AI服务不可用，请检查配置。")
            return None
        
        try:
            # 使用新的主题分析prompt
            result = llm_service.analyze_theme_genres(one_line_theme)
            return result
        except Exception as e:
            ui.print_error(f"主题分析失败: {e}")
            return None
    
    def display_genre_recommendations(self, analysis_result: Dict) -> Optional[str]:
        """显示类型推荐并获取用户选择"""
        if not analysis_result or 'recommended_genres' not in analysis_result:
            ui.print_warning("未能获取有效的类型推荐")
            return None
        
        genres = analysis_result['recommended_genres']
        primary = analysis_result.get('primary_recommendation', '')
        reasoning = analysis_result.get('reasoning', '')
        
        # 显示分析结果
        ui.print_info("🎯 AI分析结果：")
        if primary and reasoning:
            ui.print_panel(f"最推荐：{primary}\n\n理由：{reasoning}", title="主要推荐")
        
        # 显示所有推荐
        console.print(Panel(Text("📚 推荐作品类型", justify="center"), border_style="bold cyan"))
        
        genre_options = []
        for i, genre_info in enumerate(genres, 1):
            genre_name = genre_info.get('genre', '')
            reason = genre_info.get('reason', '')
            potential = genre_info.get('potential', '')
            
            content = f"[bold]{genre_name}[/bold]\n推荐理由：{reason}\n故事潜力：{potential}"
            ui.print_panel(content, title=f"选项 {i}")
            genre_options.append(genre_name)
        
        # 让用户选择
        genre_options.append("其他（手动输入）")
        genre_options.append("返回")
        
        choice = ui.display_menu("请选择您倾向的作品类型：", genre_options)
        
        if choice == '0':  # 返回
            return None
        elif choice == str(len(genre_options) - 1):  # 其他
            selected_genre = ui.prompt("请输入您想要的作品类型:")
            return selected_genre.strip() if selected_genre else None
        else:
            # 选择了推荐的类型
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(genres):
                    return genres[choice_idx]['genre']
            except (ValueError, IndexError):
                pass
        
        return None
    
    def get_user_creative_intent(self) -> str:
        """获取用户的创作意图"""
        ui.print_info("💡 请告诉我您的创作意图和特别要求：")
        ui.print_info("例如：突出心理描写、增加动作场面、强调情感冲突、营造悬疑氛围等")
        
        intent = ui.prompt("您的创作意图（必填）:")
        return intent.strip() if intent else ""
    
    def generate_paragraph_variants(self, one_line_theme: str, selected_genre: str, user_intent: str) -> Optional[Dict]:
        """生成3个版本的主题段落"""
        if not llm_service.is_available():
            ui.print_error("AI服务不可用，请检查配置。")
            return None
        
        try:
            # 使用新的变体生成prompt
            result = llm_service.generate_theme_paragraph_variants(
                one_line_theme, selected_genre, user_intent
            )
            return result
        except Exception as e:
            ui.print_error(f"段落生成失败: {e}")
            return None
    
    def display_variants_and_get_choice(self, variants_result: Dict) -> Optional[str]:
        """显示3个版本并获取用户选择"""
        if not variants_result or 'variants' not in variants_result:
            ui.print_warning("未能获取有效的段落版本")
            return None
        
        variants = variants_result['variants']
        
        console.print(Panel(Text("📝 三个版本供您选择", justify="center"), border_style="bold green"))
        
        # 定义版本标识符
        version_labels = ['A', 'B', 'C']
        
        for i, variant in enumerate(variants):
            version_label = version_labels[i] if i < len(version_labels) else f'版本{i+1}'
            focus = variant.get('focus', '')
            content = variant.get('content', '')
            
            panel_content = f"[bold cyan]{focus}[/bold cyan]\n\n{content}"
            ui.print_panel(panel_content, title=f"版本{version_label}")
        
        # 让用户选择
        options = [f"选择版本{version_labels[i]}" for i in range(min(len(variants), len(version_labels)))]
        # 如果版本数超过预定义标识符，使用数字
        if len(variants) > len(version_labels):
            for i in range(len(version_labels), len(variants)):
                options.append(f"选择版本{i+1}")
        
        options.extend(["重新生成", "返回"])
        
        choice = ui.display_menu("请选择您最喜欢的版本：", options)
        
        if choice == '0':  # 返回
            return None
        elif choice == str(len(options) - 1):  # 重新生成
            return "regenerate"
        else:
            # 选择了某个版本
            try:
                choice_idx = int(choice) - 1
                if 0 <= choice_idx < len(variants):
                    return variants[choice_idx]['content']
            except (ValueError, IndexError):
                pass
        
        return None
    
    def save_selected_paragraph(self, paragraph_content: str) -> bool:
        """保存选中的段落"""
        try:
            self.data_manager.write_theme_paragraph(paragraph_content)
            return True
        except Exception as e:
            ui.print_error(f"保存失败: {e}")
            return False
    
    def run_enhanced_theme_paragraph_workflow(self, one_line_theme_data: Dict) -> bool:
        """运行增强的主题段落工作流"""
        if not isinstance(one_line_theme_data, dict) or not one_line_theme_data.get("theme"):
            ui.print_warning("请先设置一句话主题。")
            return False
        
        one_line_theme = one_line_theme_data["theme"]
        
        ui.print_info(f"📖 当前主题：{one_line_theme}")
        
        while True:
            # 第一步：分析主题并推荐类型
            ui.print_info("🔍 正在分析主题...")
            analysis_result = self.analyze_theme_and_get_genres(one_line_theme)
            
            if not analysis_result:
                ui.print_error("主题分析失败，请重试。")
                return False
            
            # 第二步：用户选择作品类型
            selected_genre = self.display_genre_recommendations(analysis_result)
            
            if not selected_genre:
                # 用户选择返回
                return False
            
            ui.print_success(f"✅ 已选择作品类型：{selected_genre}")
            
            # 第三步：获取用户创作意图
            user_intent = self.get_user_creative_intent()
            
            if not user_intent:
                ui.print_warning("创作意图不能为空，请重新输入。")
                continue
            
            ui.print_success(f"✅ 创作意图：{user_intent}")
            
            # 第四步：生成3个版本
            ui.print_info("🎨 正在生成3个版本的故事构想...")
            variants_result = self.generate_paragraph_variants(one_line_theme, selected_genre, user_intent)
            
            if not variants_result:
                ui.print_error("段落生成失败，请重试。")
                continue
            
            # 第五步：用户选择版本
            while True:
                selected_content = self.display_variants_and_get_choice(variants_result)
                
                if not selected_content:
                    # 用户选择返回
                    break
                elif selected_content == "regenerate":
                    # 重新生成
                    ui.print_info("🔄 正在重新生成...")
                    variants_result = self.generate_paragraph_variants(one_line_theme, selected_genre, user_intent)
                    if not variants_result:
                        ui.print_error("重新生成失败。")
                        break
                    continue
                else:
                    # 用户选择了某个版本
                    if self.save_selected_paragraph(selected_content):
                        ui.print_success("✅ 段落主题已保存！")
                        ui.print_panel(selected_content, title="已保存的段落主题")
                        return True
                    else:
                        ui.print_error("保存失败，请重试。")
                        break
            
            # 询问是否重新开始
            if not ui.confirm("是否重新开始选择作品类型？"):
                break
        
        return False


# 创建全局实例
theme_paragraph_service = ThemeParagraphService()