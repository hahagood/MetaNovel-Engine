import os
import json
import re
import httpx
import asyncio
from datetime import datetime
from pathlib import Path
from openai import OpenAI, APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletion
from config import API_CONFIG, AI_CONFIG, GENERATION_CONFIG, PROXY_CONFIG, validate_config
from retry_utils import retry_manager, RetryError

class LLMService:
    """AI大语言模型服务类，封装所有AI交互逻辑"""
    
    def __init__(self):
        self.client = None
        self.async_client = None
        self.prompts = {}
        self._load_prompts()
        self._initialize_clients()
    
    def _load_prompts(self):
        """加载提示词配置"""
        try:
            # 获取当前项目的prompts.json路径
            prompts_path = self._get_prompts_path()
            with open(prompts_path, 'r', encoding='utf-8') as f:
                self.prompts = json.load(f)
        except FileNotFoundError:
            # 静默处理文件未找到，避免在启动时显示错误信息
            self.prompts = {}
        except json.JSONDecodeError as e:
            # 静默处理JSON格式错误，避免在启动时显示错误信息
            self.prompts = {}
    
    def _get_prompts_path(self):
        """获取当前项目的prompts.json路径"""
        try:
            # 导入放在方法内部，避免循环导入
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if data_manager and data_manager.project_path:
                # 多项目模式：使用项目路径下的prompts.json
                prompts_path = data_manager.project_path / 'prompts.json'
                
                # 如果项目路径下不存在prompts.json，从根目录复制默认的
                if not prompts_path.exists():
                    import shutil
                    # 优先从根目录的 prompts.json 复制
                    root_prompts = Path('prompts.json')
                    if root_prompts.exists():
                        shutil.copy2(root_prompts, prompts_path)
                        print(f"已为项目复制默认prompts.json到: {prompts_path}")
                    else:
                        # 如果根目录也没有，尝试从默认模板复制
                        default_prompts = Path('prompts.default.json')
                        if default_prompts.exists():
                            shutil.copy2(default_prompts, prompts_path)
                            print(f"已为项目复制默认prompts模板到: {prompts_path}")
                
                return prompts_path
        except ImportError:
            # 在某些测试或启动场景下，可能无法导入 project_data_manager
            pass
        except Exception as e:
            # 记录错误，但不影响核心逻辑
            print(f"获取项目特定prompts路径时出错: {e}，将使用默认路径。")

        # 单项目模式或回退方案：使用根目录的prompts.json
        return Path('prompts.json')
    
    def reload_prompts(self):
        """重新加载prompts配置，用于项目切换时"""
        self._load_prompts()
    
    def _get_prompt(self, prompt_type, user_prompt="", **kwargs):
        """获取格式化的提示词"""
        if prompt_type not in self.prompts:
            # 如果找不到配置，返回None，由调用方处理
            return None
        
        # 确保user_prompt不是None
        if user_prompt is None:
            user_prompt = ""
        
        prompt_config = self.prompts[prompt_type]
        
        # 格式化基础提示词
        base_prompt = prompt_config["base_prompt"].format(**kwargs, **GENERATION_CONFIG)
        
        # 如果有用户自定义提示词，使用模板组合
        if user_prompt.strip() and "user_prompt_template" in prompt_config:
            return prompt_config["user_prompt_template"].format(
                base_prompt=base_prompt,
                user_prompt=user_prompt.strip()
            )
        else:
            return base_prompt
    
    def _initialize_clients(self):
        """初始化同步和异步客户端"""
        try:
            # 验证配置
            if not validate_config():
                self.client = None
                self.async_client = None
                return
            
            # 构建HTTP客户端配置
            client_kwargs = {
                "base_url": API_CONFIG["base_url"],
                "api_key": API_CONFIG["openrouter_api_key"]
            }
            
            # 如果启用代理，配置HTTP客户端
            if PROXY_CONFIG["enabled"]:
                proxy_url = PROXY_CONFIG["http_proxy"]
                
                # 同步客户端
                http_client = httpx.Client(proxy=proxy_url)
                client_kwargs["http_client"] = http_client
                
                # 异步客户端
                async_http_client = httpx.AsyncClient(proxy=proxy_url)
                async_client_kwargs = client_kwargs.copy()
                async_client_kwargs["http_client"] = async_http_client
            else:
                async_client_kwargs = client_kwargs.copy()
            
            # 创建客户端
            self.client = OpenAI(**client_kwargs)
            self.async_client = AsyncOpenAI(**async_client_kwargs)
            
        except Exception as e:
            # 静默处理AI客户端初始化错误，避免在启动时显示错误信息
            self.client = None
            self.async_client = None
    
    def is_available(self):
        """检查AI服务是否可用"""
        return self.client is not None
    
    def is_async_available(self):
        """检查异步AI服务是否可用"""
        return self.async_client is not None
    
    def _save_critique_data(self, chapter_num, chapter_title, critique_data, timestamp=None):
        """保存批评数据到文件"""
        if not GENERATION_CONFIG.get('save_intermediate_data', True):
            return
        
        try:
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            # 读取现有的critiques数据
            critiques_path = data_manager.get_path("critiques")
            if critiques_path.exists():
                with open(critiques_path, 'r', encoding='utf-8') as f:
                    critiques = json.load(f)
            else:
                critiques = {}
            
            # 添加新的critique数据
            chapter_key = f"chapter_{chapter_num}"
            if chapter_key not in critiques:
                critiques[chapter_key] = []
            
            critique_entry = {
                "timestamp": timestamp,
                "chapter_title": chapter_title,
                "critique_data": critique_data
            }
            
            critiques[chapter_key].append(critique_entry)
            
            # 保存到文件
            critiques_path.parent.mkdir(parents=True, exist_ok=True)
            with open(critiques_path, 'w', encoding='utf-8') as f:
                json.dump(critiques, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存critique数据时出错: {e}")
    
    def _save_refinement_history(self, chapter_num, chapter_title, initial_content, refined_content, critique_data, timestamp=None):
        """保存修正历史到文件（只保存摘要信息，不保存完整内容）"""
        if not GENERATION_CONFIG.get('save_intermediate_data', True):
            return
        
        try:
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            # 读取现有的refinement历史数据
            history_path = data_manager.get_path("refinement_history")
            if history_path.exists():
                with open(history_path, 'r', encoding='utf-8') as f:
                    history = json.load(f)
            else:
                history = {}
            
            # 添加新的refinement记录（只保存摘要）
            chapter_key = f"chapter_{chapter_num}"
            if chapter_key not in history:
                history[chapter_key] = []
            
            refinement_entry = {
                "timestamp": timestamp,
                "chapter_title": chapter_title,
                "initial_word_count": len(initial_content) if initial_content else 0,
                "refined_word_count": len(refined_content) if refined_content else 0,
                "critique_summary": self._extract_critique_summary(critique_data),
                "word_count_change": (len(refined_content) - len(initial_content)) if (initial_content and refined_content) else 0,
                "improvement_percentage": round(((len(refined_content) - len(initial_content)) / len(initial_content)) * 100, 2) if initial_content else 0
            }
            
            history[chapter_key].append(refinement_entry)
            
            # 保存到文件
            history_path.parent.mkdir(parents=True, exist_ok=True)
            with open(history_path, 'w', encoding='utf-8') as f:
                json.dump(history, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存refinement历史时出错: {e}")
    
    def _extract_critique_summary(self, critique_data):
        """从critique数据中提取摘要信息"""
        try:
            if isinstance(critique_data, str):
                parsed_data = json.loads(critique_data)
            else:
                parsed_data = critique_data
            
            return {
                "issues_count": len(parsed_data.get("issues", [])),
                "strengths": parsed_data.get("strengths", []),
                "priority_fixes": parsed_data.get("priority_fixes", []),
                "issue_categories": [issue.get("category", "") for issue in parsed_data.get("issues", [])]
            }
        except:
            return {"raw_critique": str(critique_data)[:200] + "..." if len(str(critique_data)) > 200 else str(critique_data)}
    
    def _save_initial_draft(self, chapter_num, chapter_title, content, timestamp=None):
        """保存初稿内容到单独文件"""
        if not GENERATION_CONFIG.get('save_intermediate_data', True):
            return
        
        try:
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            # 读取现有的初稿数据
            drafts_path = data_manager.get_path("initial_drafts")
            if drafts_path.exists():
                with open(drafts_path, 'r', encoding='utf-8') as f:
                    drafts = json.load(f)
            else:
                drafts = {}
            
            # 添加新的初稿数据
            chapter_key = f"chapter_{chapter_num}"
            if chapter_key not in drafts:
                drafts[chapter_key] = []
            
            draft_entry = {
                "timestamp": timestamp,
                "chapter_title": chapter_title,
                "content": content,
                "word_count": len(content) if content else 0
            }
            
            drafts[chapter_key].append(draft_entry)
            
            # 保存到文件
            drafts_path.parent.mkdir(parents=True, exist_ok=True)
            with open(drafts_path, 'w', encoding='utf-8') as f:
                json.dump(drafts, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存初稿数据时出错: {e}")
    
    def _save_refined_draft(self, chapter_num, chapter_title, content, timestamp=None):
        """保存修订内容到单独文件"""
        if not GENERATION_CONFIG.get('save_intermediate_data', True):
            return
        
        try:
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if timestamp is None:
                timestamp = datetime.now().isoformat()
            
            # 读取现有的修订数据
            refined_path = data_manager.get_path("refined_drafts")
            if refined_path.exists():
                with open(refined_path, 'r', encoding='utf-8') as f:
                    refined = json.load(f)
            else:
                refined = {}
            
            # 添加新的修订数据
            chapter_key = f"chapter_{chapter_num}"
            if chapter_key not in refined:
                refined[chapter_key] = []
            
            refined_entry = {
                "timestamp": timestamp,
                "chapter_title": chapter_title,
                "content": content,
                "word_count": len(content) if content else 0
            }
            
            refined[chapter_key].append(refined_entry)
            
            # 保存到文件
            refined_path.parent.mkdir(parents=True, exist_ok=True)
            with open(refined_path, 'w', encoding='utf-8') as f:
                json.dump(refined, f, ensure_ascii=False, indent=2)
                
        except Exception as e:
            print(f"保存修订数据时出错: {e}")
    
    
    def _make_json_request(self, prompt, timeout=None, task_name="", with_retry=True):
        """专门用于需要JSON响应的请求（同步版本）"""
        for attempt in range(3):  # 最多尝试3次
            response_text = self._make_request(prompt, timeout, task_name, with_retry)
            if response_text is None:
                return None
            
            try:
                # 尝试直接解析JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # 尝试提取被```json ... ```包裹的代码块
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # 尝试提取被```包裹的代码块（不带json标识）
                code_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if code_match:
                    try:
                        return json.loads(code_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # 如果还是失败，且不是最后一次尝试，发送修复请求
                if attempt < 2:
                    print(f"[{task_name}] JSON解析失败，尝试修复 (第{attempt + 1}次)")
                    prompt = f"你上次返回的内容不是有效的JSON格式。请修正并返回严格的JSON格式：\n\n{response_text}\n\n请确保你的回答是严格的JSON格式，不要包含任何其他文字。"
                else:
                    print(f"[{task_name}] 多次尝试后仍无法解析JSON格式")
                    return None
        
        return None
    
    async def _make_json_request_async(self, prompt, timeout=None, task_name="", with_retry=True, progress_callback=None):
        """专门用于需要JSON响应的请求（异步版本）"""
        for attempt in range(3):  # 最多尝试3次
            response_text = await self._make_async_request(prompt, timeout, task_name, with_retry, progress_callback)
            if response_text is None:
                return None
            
            try:
                # 尝试直接解析JSON
                return json.loads(response_text)
            except json.JSONDecodeError:
                # 尝试提取被```json ... ```包裹的代码块
                json_match = re.search(r"```json\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # 尝试提取被```包裹的代码块（不带json标识）
                code_match = re.search(r"```\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if code_match:
                    try:
                        return json.loads(code_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # 如果还是失败，且不是最后一次尝试，发送修复请求
                if attempt < 2:
                    error_msg = f"[{task_name}] JSON解析失败，尝试修复 (第{attempt + 1}次)"
                    print(error_msg)
                    if progress_callback:
                        progress_callback(error_msg)
                    prompt = f"你上次返回的内容不是有效的JSON格式。请修正并返回严格的JSON格式：\n\n{response_text}\n\n请确保你的回答是严格的JSON格式，不要包含任何其他文字。"
                else:
                    error_msg = f"[{task_name}] 多次尝试后仍无法解析JSON格式"
                    print(error_msg)
                    if progress_callback:
                        progress_callback(error_msg)
                    return None
        
        return None
    
    def _make_request(self, prompt, timeout=None, task_name="", with_retry=True):
        """通用的AI请求方法（同步版本）"""
        if not self.is_available():
            return None
        
        if timeout is None:
            timeout = AI_CONFIG["timeout"]
        
        def _do_request():
            """执行实际的请求"""
            completion = self.client.chat.completions.create(
                model=AI_CONFIG["model"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                timeout=timeout,
            )
            return completion.choices[0].message.content
        
        if with_retry:
            try:
                return retry_manager.retry_sync(_do_request, task_name=task_name)
            except RetryError as e:
                print(f"\n[{task_name}] 重试{e.retry_count}次后仍失败: {e.last_exception}")
                return None
            except Exception as e:
                print(f"\n[{task_name}] 不可重试的错误: {e}")
                return None
        else:
            # 原有的直接请求逻辑（向后兼容）
            try:
                return _do_request()
            except APIStatusError as e:
                print(f"\n错误: 调用 API 时出错 (状态码: {e.status_code})")
                if e.status_code == 429:
                    print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
                else:
                    print(f"详细信息: {e.response.text}")
                return None
            except Exception as e:
                print(f"\n调用 AI 时出错: {e}")
                if "Timeout" in str(e) or "timed out" in str(e):
                    print("\n错误：请求超时。")
                    print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
                return None
    
    async def _make_async_request(self, prompt, timeout=None, task_name="", with_retry=True, progress_callback=None):
        """通用的AI请求方法（异步版本）"""
        if not self.is_async_available():
            return None
        
        if timeout is None:
            timeout = AI_CONFIG["timeout"]
        
        async def _do_async_request():
            """执行实际的异步请求"""
            completion = await self.async_client.chat.completions.create(
                model=AI_CONFIG["model"],
                messages=[
                    {
                        "role": "user",
                        "content": prompt,
                    }
                ],
                timeout=timeout,
            )
            return completion.choices[0].message.content
        
        if with_retry:
            try:
                return await retry_manager.retry_async(
                    _do_async_request,
                    task_name=task_name,
                    progress_callback=progress_callback
                )
            except RetryError as e:
                error_msg = f"[{task_name}] 重试{e.retry_count}次后仍失败: {e.last_exception}"
                print(f"\n{error_msg}")
                if progress_callback:
                    progress_callback(error_msg)
                return None
            except Exception as e:
                error_msg = f"[{task_name}] 不可重试的错误: {e}"
                print(f"\n{error_msg}")
                if progress_callback:
                    progress_callback(error_msg)
                return None
        else:
            # 原有的直接请求逻辑（向后兼容）
            try:
                return await _do_async_request()
            except APIStatusError as e:
                error_msg = f"调用 API 时出错 (状态码: {e.status_code})"
                if task_name:
                    error_msg = f"[{task_name}] {error_msg}"
                print(f"\n{error_msg}")
                if e.status_code == 429:
                    print("API 资源配额已用尽或达到速率限制。请检查您在 OpenRouter 的账户。")
                else:
                    print(f"详细信息: {e.response.text}")
                return None
            except Exception as e:
                error_msg = f"调用 AI 时出错: {e}"
                if task_name:
                    error_msg = f"[{task_name}] {error_msg}"
                print(f"\n{error_msg}")
                if "Timeout" in str(e) or "timed out" in str(e):
                    print("\n错误：请求超时。")
                    print("这很可能是您的网络无法连接到 OpenRouter 的服务器。请检查您的网络连接、代理或防火墙设置。")
                return None
    
    def generate_theme_paragraph(self, one_line_theme, user_prompt=""):
        """生成段落主题"""
        if user_prompt is None:
            user_prompt = ""
            
        prompt = self._get_prompt("theme_paragraph", user_prompt, one_line_theme=one_line_theme)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请将以下这个一句话小说主题，扩展成一段更加具体、包含更多情节可能性的段落大纲，字数在{GENERATION_CONFIG['theme_paragraph_length']}。请直接输出扩写后的段落，不要包含额外说明和标题。\n\n一句话主题：{one_line_theme}"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def analyze_theme_genres(self, one_line_theme, user_prompt=""):
        """分析主题并推荐作品类型"""
        if user_prompt is None:
            user_prompt = ""
            
        prompt = self._get_prompt("theme_analysis", user_prompt, one_line_theme=one_line_theme)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请分析以下一句话主题，并推荐3-5种最适合的作品类型（如科幻、奇幻、悬疑、情感等），以JSON格式返回。\n\n主题：{one_line_theme}"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_json_request(prompt, task_name="主题分析")
    
    def generate_theme_paragraph_variants(self, one_line_theme, selected_genre, user_intent, user_prompt=""):
        """生成3个版本的主题段落"""
        if user_prompt is None:
            user_prompt = ""
            
        prompt = self._get_prompt("theme_paragraph_variants", user_prompt, 
                                 one_line_theme=one_line_theme,
                                 selected_genre=selected_genre,
                                 user_intent=user_intent)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请根据以下信息生成3个不同版本的故事构想，每个版本约{GENERATION_CONFIG['theme_paragraph_length']}字，以JSON格式返回。\n\n主题：{one_line_theme}\n类型：{selected_genre}\n用户意图：{user_intent}"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_json_request(prompt, task_name="主题段落生成")
    
    def generate_theme_paragraph_with_genre(self, one_line_theme, selected_genre, user_intent, user_prompt=""):
        """基于类型和用户意图生成主题段落"""
        if user_prompt is None:
            user_prompt = ""
            
        prompt = self._get_prompt("theme_paragraph", user_prompt, 
                                 one_line_theme=one_line_theme,
                                 selected_genre=selected_genre,
                                 user_intent=user_intent)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请将以下一句话主题按照{selected_genre}类型的风格，扩展成一段具体的故事构想，字数在{GENERATION_CONFIG['theme_paragraph_length']}。\n\n主题：{one_line_theme}\n用户意图：{user_intent}"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_character_description(self, char_name, user_prompt="", one_line_theme="", story_context=""):
        """生成角色描述"""
        # 如果没有提供上下文信息，尝试从数据管理器获取
        if not one_line_theme or not story_context:
            # 导入放在方法内部，避免循环导入
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if not one_line_theme:
                theme_data = data_manager.read_theme_one_line()
                if isinstance(theme_data, dict):
                    one_line_theme = theme_data.get("theme", "")
                elif isinstance(theme_data, str):
                    one_line_theme = theme_data
                else:
                    one_line_theme = ""
            
            if not story_context:
                # 使用段落主题作为故事背景
                story_context = data_manager.read_theme_paragraph() or ""
        
        prompt = self._get_prompt("character_description", user_prompt, 
                                  char_name=char_name, 
                                  one_line_theme=one_line_theme,
                                  story_context=story_context)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请为小说角色 '{char_name}' 创建一个详细的角色描述，包括外貌特征、性格特点、背景故事、能力特长等方面，字数在{GENERATION_CONFIG['character_description_length']}。请直接输出角色描述，不要包含额外说明和标题。"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_location_description(self, loc_name, user_prompt="", one_line_theme="", story_context=""):
        """生成场景描述"""
        # 如果没有提供上下文信息，尝试从数据管理器获取
        if not one_line_theme or not story_context:
            # 导入放在方法内部，避免循环导入
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if not one_line_theme:
                theme_data = data_manager.read_theme_one_line()
                if isinstance(theme_data, dict):
                    one_line_theme = theme_data.get("theme", "")
                elif isinstance(theme_data, str):
                    one_line_theme = theme_data
                else:
                    one_line_theme = ""
            
            if not story_context:
                # 使用段落主题作为故事背景
                story_context = data_manager.read_theme_paragraph() or ""
        
        prompt = self._get_prompt("location_description", user_prompt, 
                                  loc_name=loc_name, 
                                  one_line_theme=one_line_theme,
                                  story_context=story_context)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请为小说场景 '{loc_name}' 创建一个详细的场景描述，包括地理位置、环境特色、建筑风格、氛围感受、历史背景、重要特征等方面，字数在{GENERATION_CONFIG['location_description_length']}。请直接输出场景描述，不要包含额外说明和标题。"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_item_description(self, item_name, user_prompt="", one_line_theme="", story_context=""):
        """生成道具描述"""
        # 如果没有提供上下文信息，尝试从数据管理器获取
        if not one_line_theme or not story_context:
            # 导入放在方法内部，避免循环导入
            from project_data_manager import project_data_manager
            data_manager = project_data_manager.get_data_manager()
            
            if not one_line_theme:
                theme_data = data_manager.read_theme_one_line()
                if isinstance(theme_data, dict):
                    one_line_theme = theme_data.get("theme", "")
                elif isinstance(theme_data, str):
                    one_line_theme = theme_data
                else:
                    one_line_theme = ""
            
            if not story_context:
                # 使用段落主题作为故事背景
                story_context = data_manager.read_theme_paragraph() or ""
        
        prompt = self._get_prompt("item_description", user_prompt, 
                                  item_name=item_name, 
                                  one_line_theme=one_line_theme,
                                  story_context=story_context)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请为小说道具 '{item_name}' 创建一个详细的道具描述，包括外观特征、材质工艺、功能用途、历史来源、特殊能力、重要意义等方面，字数在{GENERATION_CONFIG['item_description_length']}。请直接输出道具描述，不要包含额外说明和标题。"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_story_outline(self, one_line_theme, paragraph_theme, characters_info="", user_prompt=""):
        """生成故事大纲"""
        prompt = self._get_prompt("story_outline", user_prompt, 
                                  one_line_theme=one_line_theme, 
                                  paragraph_theme=paragraph_theme,
                                  characters_info=characters_info)
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于以下信息创建一个详细的小说故事大纲：

一句话主题：{one_line_theme}

段落主题：{paragraph_theme}{characters_info}

请创建一个包含以下要素的完整故事大纲：
1. 故事背景设定
2. 主要情节线索
3. 关键转折点
4. 冲突与高潮
5. 结局方向

大纲应该详细具体，字数在{GENERATION_CONFIG['story_outline_length']}。请直接输出故事大纲，不要包含额外说明和标题。"""
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_chapter_outline(self, one_line_theme, story_outline, characters_info="", user_prompt=""):
        """生成分章细纲"""
        prompt = self._get_prompt("chapter_outline", user_prompt, 
                                one_line_theme=one_line_theme, 
                                story_outline=story_outline, 
                                characters_info=characters_info)
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于以下信息创建详细的分章细纲：

主题：{one_line_theme}

故事大纲：{story_outline}{characters_info}

请将故事分解为5-10个章节，每个章节包含：
1. 章节标题
2. 章节大纲（150-200字）
3. 主要情节点
4. 角色发展

请以JSON格式输出，格式如下：
{{
  "chapters": [
    {{
      "title": "章节标题",
      "outline": "章节详细大纲内容"
    }}
  ]
}}

请确保输出的是有效的JSON格式。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        # 使用专门的JSON请求方法
        result = self._make_json_request(prompt, task_name="分章细纲")
        if result and isinstance(result, dict):
            return result
        else:
            # 如果JSON解析失败，返回原始文本
            return self._make_request(prompt)
    
    def generate_chapter_summary(self, chapter, chapter_num, context_info, user_prompt=""):
        """生成章节概要"""
        if user_prompt is None:
            user_prompt = ""

        base_prompt = f"""请基于以下信息为第{chapter_num}章创建详细的章节概要：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

请创建一个详细的章节概要，包含：
1. 场景设定（时间、地点、环境）
2. 主要人物及其行动
3. 关键情节发展
4. 对话要点
5. 情感氛围
6. 与整体故事的连接

概要应该详细具体，字数在{GENERATION_CONFIG['chapter_summary_length']}，为后续的正文写作提供充分的指导。请直接输出章节概要，不要包含额外说明和标题。"""
        
        if user_prompt and user_prompt.strip():
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        return self._make_request(full_prompt)
    
    def generate_novel_chapter(self, chapter, summary_info, chapter_num, context_info, user_prompt=""):
        """生成单章小说正文"""
        if user_prompt is None:
            user_prompt = ""

        task_name = f"章节 {chapter_num} 正文生成"
        prompt = self._get_prompt(
            "novel_chapter",
            user_prompt=user_prompt,
            chapter_num=chapter_num,
            chapter=chapter,
            summary_info=summary_info,
            context_info=context_info
        )
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于以下信息为第{chapter_num}章创建完整的小说正文：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

章节概要：
{summary_info.get('summary', '无概要')}

请创建完整的小说正文，要求：
1. 生动的场景描写和环境渲染
2. 丰富的人物对话和内心独白
3. 细腻的情感表达和心理描写
4. 流畅的情节推进和节奏控制
5. 符合小说文学风格的语言表达
6. 与前后章节的自然衔接

正文应该详细完整，字数在{GENERATION_CONFIG['novel_chapter_length']}。请直接输出小说正文，不要包含章节标题和额外说明。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        # 小说正文生成需要更长时间
        return self._make_request(prompt, timeout=120)

    # 新增异步方法
    async def generate_chapter_summary_async(self, chapter, chapter_num, context_info, user_prompt="", progress_callback=None):
        """异步生成章节概要"""
        if user_prompt is None:
            user_prompt = ""

        task_name = f"章节 {chapter_num} 概要生成"
        prompt = self._get_prompt(
            "chapter_summary",
            user_prompt=user_prompt,
            chapter_num=chapter_num,
            chapter=chapter,
            context_info=context_info
        )
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于以下信息为第{chapter_num}章创建详细的章节概要：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

请创建一个详细的章节概要，包含：
1. 场景设定（时间、地点、环境）
2. 主要人物及其行动
3. 关键情节发展
4. 对话要点
5. 情感氛围
6. 与整体故事的连接

概要应该详细具体，字数在{GENERATION_CONFIG['chapter_summary_length']}，为后续的正文写作提供充分的指导。请直接输出章节概要，不要包含额外说明和标题。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        return await self._make_async_request(
            prompt, 
            task_name=task_name,
            progress_callback=progress_callback
        )
    
    async def generate_novel_chapter_async(self, chapter, summary_info, chapter_num, context_info, user_prompt="", progress_callback=None):
        """异步生成单章小说正文"""
        if user_prompt is None:
            user_prompt = ""

        task_name = f"章节 {chapter_num} 正文生成"
        prompt = self._get_prompt(
            "novel_chapter",
            user_prompt=user_prompt,
            chapter_num=chapter_num,
            chapter=chapter,
            summary_info=summary_info,
            context_info=context_info
        )
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于以下信息为第{chapter_num}章创建完整的小说正文：

{context_info}

当前章节信息：
章节标题：{chapter.get('title', f'第{chapter_num}章')}
章节大纲：{chapter.get('outline', '无大纲')}

章节概要：
{summary_info.get('summary', '无概要')}

请创建完整的小说正文，要求：
1. 生动的场景描写和环境渲染
2. 丰富的人物对话和内心独白
3. 细腻的情感表达和心理描写
4. 流畅的情节推进和节奏控制
5. 符合小说文学风格的语言表达
6. 与前后章节的自然衔接

正文应该详细完整，字数在{GENERATION_CONFIG['novel_chapter_length']}。请直接输出小说正文，不要包含章节标题和额外说明。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        # 小说正文生成需要更长时间
        return await self._make_async_request(
            prompt, 
            timeout=120, 
            task_name=task_name,
            progress_callback=progress_callback
        )

    # 批量异步生成方法
    async def generate_all_summaries_async(self, chapters, context_info, user_prompt="", progress_callback=None):
        """异步批量生成所有章节概要"""
        if not self.is_async_available():
            return {}, []
        
        # 创建所有任务
        tasks = []
        for i, chapter in enumerate(chapters, 1):
            task = self.generate_chapter_summary_async(chapter, i, context_info, user_prompt, progress_callback)
            tasks.append((i, chapter, task))
        
        results = {}
        failed_chapters = []
        
        # 使用 asyncio.gather 真正并发执行所有任务
        try:
            if progress_callback:
                progress_callback("开始并发生成所有章节概要...")
            
            # 创建任务列表，只包含协程对象
            task_coroutines = [task for _, _, task in tasks]
            
            # 并发执行所有任务
            summaries = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # 处理结果
            for (i, chapter, _), summary in zip(tasks, summaries):
                if isinstance(summary, Exception):
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章概要生成异常: {summary}")
                elif summary:
                    results[f"chapter_{i}"] = {
                        "title": chapter.get('title', f'第{i}章'),
                        "summary": summary
                    }
                    if progress_callback:
                        progress_callback(f"第{i}章概要生成完成")
                else:
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章概要生成失败")
                        
        except Exception as e:
            if progress_callback:
                progress_callback(f"批量生成过程中出现异常: {e}")
            # 如果整体失败，所有章节都标记为失败
            failed_chapters = list(range(1, len(chapters) + 1))
        
        return results, failed_chapters
    
    async def generate_all_novels_async(self, chapters, summaries, context_info, user_prompt="", progress_callback=None):
        """异步批量生成所有章节正文"""
        if not self.is_async_available():
            return {}, []
        
        # 创建所有任务
        tasks = []
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key in summaries:
                chapter = chapters[i-1]
                summary_info = summaries[chapter_key]
                task = self.generate_novel_chapter_async(chapter, summary_info, i, context_info, user_prompt, progress_callback)
                tasks.append((i, chapter, task))
        
        results = {}
        failed_chapters = []
        
        # 使用 asyncio.gather 真正并发执行所有任务
        try:
            if progress_callback:
                progress_callback("开始并发生成所有章节正文...")
            
            # 创建任务列表，只包含协程对象
            task_coroutines = [task for _, _, task in tasks]
            
            # 并发执行所有任务
            contents = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # 处理结果
            for (i, chapter, _), content in zip(tasks, contents):
                if isinstance(content, Exception):
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章正文生成异常: {content}")
                elif content:
                    results[f"chapter_{i}"] = {
                        "title": chapter.get('title', f'第{i}章'),
                        "content": content,
                        "word_count": len(content)
                    }
                    if progress_callback:
                        progress_callback(f"第{i}章正文生成完成 ({len(content)}字)")
                else:
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章正文生成失败")
                        
        except Exception as e:
            if progress_callback:
                progress_callback(f"批量生成过程中出现异常: {e}")
            # 如果整体失败，将所有待生成的章节标记为失败
            failed_chapters = [i for i, _, _ in tasks]
        
        return results, failed_chapters
    
    async def generate_all_novels_with_refinement_async(self, chapters, summaries, context_info, user_prompt="", progress_callback=None):
        """异步批量生成所有章节正文，包含反思修正流程"""
        if not self.is_async_available():
            return {}, []
        
        # 创建所有任务
        tasks = []
        for i in range(1, len(chapters) + 1):
            chapter_key = f"chapter_{i}"
            if chapter_key in summaries:
                chapter = chapters[i-1]
                summary_info = summaries[chapter_key]
                task = self.generate_novel_chapter_with_refinement_async(
                    chapter, summary_info, i, context_info, user_prompt, progress_callback
                )
                tasks.append((i, chapter, task))
        
        results = {}
        failed_chapters = []
        
        # 使用 asyncio.gather 真正并发执行所有任务
        try:
            if progress_callback:
                progress_callback("开始并发智能生成所有章节正文...")
            
            # 创建任务列表，只包含协程对象
            task_coroutines = [task for _, _, task in tasks]
            
            # 并发执行所有任务
            contents = await asyncio.gather(*task_coroutines, return_exceptions=True)
            
            # 处理结果
            for (i, chapter, _), content in zip(tasks, contents):
                if isinstance(content, Exception):
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章智能生成异常: {content}")
                elif content:
                    results[f"chapter_{i}"] = {
                        "title": chapter.get('title', f'第{i}章'),
                        "content": content,
                        "word_count": len(content)
                    }
                    if progress_callback:
                        progress_callback(f"第{i}章智能生成完成 ({len(content)}字)")
                else:
                    failed_chapters.append(i)
                    if progress_callback:
                        progress_callback(f"第{i}章智能生成失败")
                        
        except Exception as e:
            if progress_callback:
                progress_callback(f"批量智能生成过程中出现异常: {e}")
            # 如果整体失败，将所有待生成的章节标记为失败
            failed_chapters = [i for i, _, _ in tasks]
        
        return results, failed_chapters
    
    def generate_novel_critique(self, chapter_title, chapter_num, chapter_content, context_info, user_prompt=""):
        """生成小说章节批评"""
        prompt = self._get_prompt("novel_critique", user_prompt, 
                                  chapter_title=chapter_title,
                                  chapter_num=chapter_num,
                                  chapter_content=chapter_content,
                                  context_info=context_info)
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请对以下小说章节进行批判性分析，以JSON格式输出：

章节标题：{chapter_title}
章节号：第{chapter_num}章

{chapter_content}

请输出JSON格式：
{{
  "issues": [
    {{
      "category": "character/plot/language/experience",
      "problem": "问题描述（简洁）",
      "suggestion": "改进建议（简洁）"
    }}
  ],
  "strengths": ["优点1", "优点2"],
  "priority_fixes": ["最需要修正的问题1", "最需要修正的问题2"]
}}

要求简洁，总体控制在{GENERATION_CONFIG['novel_critique_length']}。只返回JSON，不要其他文字。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        # 使用JSON请求方法
        result = self._make_json_request(prompt, timeout=90, task_name=f"第{chapter_num}章批评")
        if result and isinstance(result, dict):
            # 返回JSON字符串，便于后续处理
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 如果JSON解析失败，返回原始文本
            return self._make_request(prompt, timeout=90)
    
    def generate_novel_refinement(self, chapter_title, chapter_num, original_content, critique_feedback, context_info, user_prompt=""):
        """基于批评反馈修正小说章节"""
        prompt = self._get_prompt("novel_refinement", user_prompt, 
                                  chapter_title=chapter_title,
                                  chapter_num=chapter_num,
                                  original_content=original_content,
                                  critique_feedback=critique_feedback,
                                  context_info=context_info)
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于批评反馈对以下小说章节进行修正：

章节标题：{chapter_title}
章节号：第{chapter_num}章

原始正文：
{original_content}

批评反馈：
{critique_feedback}

请根据批评反馈进行针对性修正，改善被批评的问题，同时保持原有的优点。修正后的章节应该更加流畅自然，更能吸引读者。字数控制在{GENERATION_CONFIG['novel_chapter_length']}。请直接输出修正后的完整章节正文，不要包含标题和说明。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        return self._make_request(prompt, timeout=120)
    
    def generate_novel_chapter_with_refinement(self, chapter, summary_info, chapter_num, context_info, user_prompt="", progress_callback=None):
        """生成小说章节正文，包含反思修正流程"""
        timestamp = datetime.now().isoformat()
        chapter_title = chapter.get('title', f'第{chapter_num}章')
        
        # 首先生成初稿
        initial_content = self.generate_novel_chapter(chapter, summary_info, chapter_num, context_info, user_prompt)
        
        if not initial_content:
            return None
        
        # 保存初稿内容到单独文件
        self._save_initial_draft(chapter_num, chapter_title, initial_content, timestamp)
        
        # 检查是否启用反思修正
        if not GENERATION_CONFIG.get('enable_refinement', True):
            return initial_content
        
        # 生成批评反馈
        critique = self.generate_novel_critique(chapter_title, chapter_num, initial_content, context_info)
        
        if not critique:
            print(f"第{chapter_num}章批评生成失败，返回初稿")
            return initial_content
        
        # 保存critique数据
        try:
            critique_data = json.loads(critique) if isinstance(critique, str) else critique
            self._save_critique_data(chapter_num, chapter_title, critique_data, timestamp)
        except:
            # 如果critique不是有效的JSON，保存原始文本
            self._save_critique_data(chapter_num, chapter_title, {"raw_critique": critique}, timestamp)
        
        # 显示批评反馈（如果配置允许）
        if GENERATION_CONFIG.get('show_critique_to_user', True):
            try:
                import json
                critique_data = json.loads(critique)
                critique_msg = f"第{chapter_num}章批评: 发现{len(critique_data.get('issues', []))}个问题"
                if critique_data.get('priority_fixes'):
                    critique_msg += f", 优先修正: {critique_data['priority_fixes'][0]}"
                if progress_callback:
                    progress_callback(critique_msg)
            except:
                # 如果不是JSON格式，显示简化版本
                critique_msg = f"第{chapter_num}章批评反馈：{critique[:100]}..."
                if progress_callback:
                    progress_callback(critique_msg)
        
        # 检查修正模式
        refinement_mode = GENERATION_CONFIG.get('refinement_mode', 'auto')
        
        if refinement_mode == 'disabled':
            return initial_content
        elif refinement_mode == 'manual':
            # 手动模式：询问用户是否要修正
            should_refine = ui.confirm(f"是否要基于批评反馈修正第{chapter_num}章？")
            if not should_refine:
                return initial_content
        
        # 生成修正版本
        refined_content = self.generate_novel_refinement(chapter_title, chapter_num, initial_content, critique, context_info, user_prompt)
        
        if not refined_content:
            print(f"第{chapter_num}章修正失败，返回初稿")
            return initial_content
        
        # 保存修订内容到单独文件
        self._save_refined_draft(chapter_num, chapter_title, refined_content, timestamp)
        
        # 保存refinement历史（不再保存完整内容，只保存摘要）
        try:
            critique_data = json.loads(critique) if isinstance(critique, str) else critique
        except:
            critique_data = {"raw_critique": critique}
        
        self._save_refinement_history(chapter_num, chapter_title, initial_content, refined_content, critique_data, timestamp)
        
        print(f"第{chapter_num}章已完成反思修正流程")
        return refined_content
    
    # 异步版本的新方法
    async def generate_novel_critique_async(self, chapter_title, chapter_num, chapter_content, context_info, user_prompt="", progress_callback=None):
        """异步生成小说章节批评"""
        prompt = self._get_prompt("novel_critique", user_prompt, 
                                  chapter_title=chapter_title,
                                  chapter_num=chapter_num,
                                  chapter_content=chapter_content,
                                  context_info=context_info)
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请对以下小说章节进行批判性分析，以JSON格式输出：

章节标题：{chapter_title}
章节号：第{chapter_num}章

{chapter_content}

请输出JSON格式：
{{
  "issues": [
    {{
      "category": "character/plot/language/experience",
      "problem": "问题描述（简洁）",
      "suggestion": "改进建议（简洁）"
    }}
  ],
  "strengths": ["优点1", "优点2"],
  "priority_fixes": ["最需要修正的问题1", "最需要修正的问题2"]
}}

要求简洁，总体控制在{GENERATION_CONFIG['novel_critique_length']}。只返回JSON，不要其他文字。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        task_name = f"第{chapter_num}章批评"
        # 使用JSON请求方法
        result = await self._make_json_request_async(
            prompt, 
            timeout=90, 
            task_name=task_name,
            progress_callback=progress_callback
        )
        if result and isinstance(result, dict):
            # 返回JSON字符串，便于后续处理
            import json
            return json.dumps(result, ensure_ascii=False, indent=2)
        else:
            # 如果JSON解析失败，返回原始文本
            return await self._make_async_request(
                prompt, 
                timeout=90, 
                task_name=task_name,
                progress_callback=progress_callback
            )
    
    async def generate_novel_refinement_async(self, chapter_title, chapter_num, original_content, critique_feedback, context_info, user_prompt="", progress_callback=None):
        """异步基于批评反馈修正小说章节"""
        prompt = self._get_prompt("novel_refinement", user_prompt, 
                                  chapter_title=chapter_title,
                                  chapter_num=chapter_num,
                                  original_content=original_content,
                                  critique_feedback=critique_feedback,
                                  context_info=context_info)
        
        if prompt is None:
            # 后备提示词
            base_prompt = f"""请基于批评反馈对以下小说章节进行修正：

章节标题：{chapter_title}
章节号：第{chapter_num}章

原始正文：
{original_content}

批评反馈：
{critique_feedback}

请根据批评反馈进行针对性修正，改善被批评的问题，同时保持原有的优点。修正后的章节应该更加流畅自然，更能吸引读者。字数控制在{GENERATION_CONFIG['novel_chapter_length']}。请直接输出修正后的完整章节正文，不要包含标题和说明。"""
            
            if user_prompt.strip():
                prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
            else:
                prompt = base_prompt
        
        task_name = f"第{chapter_num}章修正"
        return await self._make_async_request(
            prompt, 
            timeout=120, 
            task_name=task_name,
            progress_callback=progress_callback
        )
    
    async def generate_novel_chapter_with_refinement_async(self, chapter, summary_info, chapter_num, context_info, user_prompt="", progress_callback=None):
        """异步生成小说章节正文，包含反思修正流程"""
        timestamp = datetime.now().isoformat()
        chapter_title = chapter.get('title', f'第{chapter_num}章')
        
        # 首先生成初稿
        if progress_callback:
            progress_callback(f"第{chapter_num}章：生成初稿...")
        
        initial_content = await self.generate_novel_chapter_async(chapter, summary_info, chapter_num, context_info, user_prompt, progress_callback)
        
        if not initial_content:
            return None
        
        # 保存初稿内容到单独文件
        self._save_initial_draft(chapter_num, chapter_title, initial_content, timestamp)
        
        # 检查是否启用反思修正
        if not GENERATION_CONFIG.get('enable_refinement', True):
            return initial_content
        
        # 生成批评反馈
        if progress_callback:
            progress_callback(f"第{chapter_num}章：生成批评反馈...")
        
        critique = await self.generate_novel_critique_async(chapter_title, chapter_num, initial_content, context_info, "", progress_callback)
        
        if not critique:
            if progress_callback:
                progress_callback(f"第{chapter_num}章：批评生成失败，返回初稿")
            return initial_content
        
        # 保存critique数据
        try:
            critique_data = json.loads(critique) if isinstance(critique, str) else critique
            self._save_critique_data(chapter_num, chapter_title, critique_data, timestamp)
        except:
            # 如果critique不是有效的JSON，保存原始文本
            self._save_critique_data(chapter_num, chapter_title, {"raw_critique": critique}, timestamp)
        
        # 显示批评反馈（如果配置允许）
        if GENERATION_CONFIG.get('show_critique_to_user', True):
            try:
                import json
                critique_data = json.loads(critique)
                critique_msg = f"第{chapter_num}章批评: 发现{len(critique_data.get('issues', []))}个问题"
                if critique_data.get('priority_fixes'):
                    critique_msg += f", 优先修正: {critique_data['priority_fixes'][0]}"
                if progress_callback:
                    progress_callback(critique_msg)
            except:
                # 如果不是JSON格式，显示简化版本
                critique_msg = f"第{chapter_num}章批评反馈：{critique[:100]}..."
                if progress_callback:
                    progress_callback(critique_msg)
        
        # 检查修正模式
        refinement_mode = GENERATION_CONFIG.get('refinement_mode', 'auto')
        
        if refinement_mode == 'disabled':
            return initial_content
        
        # 生成修正版本
        if progress_callback:
            progress_callback(f"第{chapter_num}章：基于批评反馈修正...")
        
        refined_content = await self.generate_novel_refinement_async(chapter_title, chapter_num, initial_content, critique, context_info, user_prompt, progress_callback)
        
        if not refined_content:
            if progress_callback:
                progress_callback(f"第{chapter_num}章：修正失败，返回初稿")
            return initial_content
        
        # 保存修订内容到单独文件
        self._save_refined_draft(chapter_num, chapter_title, refined_content, timestamp)
        
        # 保存refinement历史（不再保存完整内容，只保存摘要）
        try:
            critique_data = json.loads(critique) if isinstance(critique, str) else critique
        except:
            critique_data = {"raw_critique": critique}
        
        self._save_refinement_history(chapter_num, chapter_title, initial_content, refined_content, critique_data, timestamp)
        
        if progress_callback:
            progress_callback(f"第{chapter_num}章：反思修正流程完成")
        
        return refined_content

# 创建全局LLM服务实例
llm_service = LLMService() 