import os
import json
import httpx
import asyncio
from openai import OpenAI, APIStatusError, AsyncOpenAI
from openai.types.chat import ChatCompletion
from config import AI_CONFIG, GENERATION_CONFIG, PROXY_CONFIG
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
            with open('prompts.json', 'r', encoding='utf-8') as f:
                self.prompts = json.load(f)
        except FileNotFoundError:
            print("警告: 未找到prompts.json文件，将使用默认提示词")
            self.prompts = {}
        except json.JSONDecodeError as e:
            print(f"警告: prompts.json格式错误: {e}")
            self.prompts = {}
    
    def _get_prompt(self, prompt_type, user_prompt="", **kwargs):
        """获取格式化的提示词"""
        if prompt_type not in self.prompts:
            # 如果找不到配置，返回None，由调用方处理
            return None
        
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
            # 同步客户端
            self.client = OpenAI(
                base_url=AI_CONFIG["base_url"],
                api_key=AI_CONFIG["api_key"],
                http_client=httpx.Client(proxies=PROXY_CONFIG) if PROXY_CONFIG else None
            )
            
            # 异步客户端
            self.async_client = AsyncOpenAI(
                base_url=AI_CONFIG["base_url"],
                api_key=AI_CONFIG["api_key"],
                http_client=httpx.AsyncClient(proxies=PROXY_CONFIG) if PROXY_CONFIG else None
            )
        except Exception as e:
            print(f"初始化AI客户端时出错: {e}")
            self.client = None
            self.async_client = None
    
    def is_available(self):
        """检查AI服务是否可用"""
        return self.client is not None
    
    def is_async_available(self):
        """检查异步AI服务是否可用"""
        return self.async_client is not None
    
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
        prompt = self._get_prompt("theme_paragraph", user_prompt, one_line_theme=one_line_theme)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请将以下这个一句话小说主题，扩展成一段更加具体、包含更多情节可能性的段落大纲，字数在{GENERATION_CONFIG['theme_paragraph_length']}。请直接输出扩写后的段落，不要包含额外说明和标题。\n\n一句话主题：{one_line_theme}"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_character_description(self, char_name, user_prompt=""):
        """生成角色描述"""
        prompt = self._get_prompt("character_description", user_prompt, char_name=char_name)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请为小说角色 '{char_name}' 创建一个详细的角色描述，包括外貌特征、性格特点、背景故事、能力特长等方面，字数在{GENERATION_CONFIG['character_description_length']}。请直接输出角色描述，不要包含额外说明和标题。"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_location_description(self, loc_name, user_prompt=""):
        """生成场景描述"""
        prompt = self._get_prompt("location_description", user_prompt, loc_name=loc_name)
        if prompt is None:
            # 后备提示词
            base_prompt = f"请为小说场景 '{loc_name}' 创建一个详细的场景描述，包括地理位置、环境特色、建筑风格、氛围感受、历史背景、重要特征等方面，字数在{GENERATION_CONFIG['location_description_length']}。请直接输出场景描述，不要包含额外说明和标题。"
            prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}" if user_prompt.strip() else base_prompt
        
        return self._make_request(prompt)
    
    def generate_item_description(self, item_name, user_prompt=""):
        """生成道具描述"""
        prompt = self._get_prompt("item_description", user_prompt, item_name=item_name)
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
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        return self._make_request(full_prompt)
    
    def generate_chapter_summary(self, chapter, chapter_num, context_info, user_prompt=""):
        """生成章节概要"""
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
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        return self._make_request(full_prompt)
    
    def generate_novel_chapter(self, chapter, summary_info, chapter_num, context_info, user_prompt=""):
        """生成小说章节正文"""
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
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        # 小说正文生成需要更长时间
        return self._make_request(full_prompt, timeout=120)

    # 新增异步方法
    async def generate_chapter_summary_async(self, chapter, chapter_num, context_info, user_prompt="", progress_callback=None):
        """异步生成章节概要"""
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
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        task_name = f"第{chapter_num}章概要"
        return await self._make_async_request(
            full_prompt, 
            task_name=task_name,
            progress_callback=progress_callback
        )
    
    async def generate_novel_chapter_async(self, chapter, summary_info, chapter_num, context_info, user_prompt="", progress_callback=None):
        """异步生成小说章节正文"""
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
            full_prompt = f"{base_prompt}\n\n用户额外要求：{user_prompt.strip()}"
        else:
            full_prompt = base_prompt
        
        task_name = f"第{chapter_num}章正文"
        # 小说正文生成需要更长时间
        return await self._make_async_request(
            full_prompt, 
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

# 创建全局LLM服务实例
llm_service = LLMService() 