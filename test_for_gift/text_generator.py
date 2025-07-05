import sys
import random
import re
import json
import os
from abc import ABC, abstractmethod

def try_import_tracery():
    """尝试导入并使用tracery，如果失败则返回False"""
    try:
        import tracery
        # 测试基本功能
        test_grammar = tracery.Grammar({'test': 'hello'})
        test_result = test_grammar.flatten('#test#')
        return True, tracery
    except Exception as e:
        print(f"⚠️  tracery库不可用: {e}")
        return False, None

class BaseTextGenerator(ABC):
    """文本生成器基类，定义通用接口和共享功能"""

    def __init__(self, language='en'):
        """初始化文本生成器基类。

        Args:
            language (str, optional): 目标语言，'en'代表英文, 'zh'代表中文。 默认为 'en'。
        """
        self.language = language
        self.grammar = self._load_grammar_from_file(language)
        self.set_grammar(self.grammar)

    def _load_grammar_from_file(self, language):
        """从JSON文件加载语法规则。

        Args:
            language (str): 目标语言，用于定位对应的语法文件 (e.g., 'en_grammar.json')。

        Returns:
            dict: 从JSON文件加载的语法规则。

        Raises:
            FileNotFoundError: 如果找不到对应的语法文件。
            ValueError: 如果JSON文件格式不正确。
        """
        # 获取当前脚本所在目录
        current_dir = os.path.dirname(os.path.abspath(__file__))
        file_path = os.path.join(current_dir, 'grammars', f'{language}_grammar.json')
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise FileNotFoundError(f"错误: 找不到语法文件 '{file_path}'")
        except json.JSONDecodeError:
            raise ValueError(f"错误: 语法文件 '{file_path}' 格式不正确")

    @abstractmethod
    def set_grammar(self, grammar_rules):
        """设置语法规则。

        Args:
            grammar_rules (dict): 一个包含语法规则的字典。
        """
        pass

    @abstractmethod
    def generate(self, rule_name="origin", count=1):
        """根据给定的规则生成文本。

        Args:
            rule_name (str, optional): 起始规则的名称。 默认为 "origin"。
            count (int, optional): 生成文本的数量。 默认为 1。

        Returns:
            str or list[str]: 如果 count 为 1，则返回单个字符串；否则返回字符串列表。
        """
        pass

    def generate_multiple_stories(self, count=3):
        """生成多个完整的故事。

        Args:
            count (int, optional): 要生成的故事数量。 默认为 3。

        Returns:
            list[str]: 包含多个故事的列表，每个故事都是一个字符串。
        """
        stories = []
        for i in range(count):
            story = self.generate("origin")
            stories.append(f"故事 {i+1}:\n{story}\n" if self.language == 'zh' else f"Story {i+1}:\n{story}\n")
        return stories

    def generate_story_collection(self, themes=None):
        """生成一个围绕特定主题的故事集合。

        Args:
            themes (list[str], optional): 一个包含主题字符串的列表。
                如果为None，将使用默认的主题列表。 默认为 None。

        Returns:
            list[str]: 包含多个主题故事的列表。
        """
        if themes is None:
            themes = ["冒险", "友谊", "发现", "成长", "创新"] if self.language == 'zh' else ["adventure", "friendship", "discovery", "growth", "innovation"]
        
        collection = []
        for theme in themes:
            story = self.generate("origin")
            collection.append(f"主题: {theme}\n{story}\n" if self.language == 'zh' else f"Theme: {theme}\n{story}\n")
        
        return collection


class AdvancedTextGenerator(BaseTextGenerator):
    """高级文本生成器，使用自定义逻辑实现，支持短期记忆以避免重复。"""
    
    def set_grammar(self, grammar_rules):
        """设置语法规则。

        Args:
            grammar_rules (dict): 一个包含语法规则的字典。
        """
        self.grammar = grammar_rules

    def generate(self, rule_name="origin", count=1):
        """根据给定的规则生成文本，并为每个生成过程使用独立的短期记忆。

        Args:
            rule_name (str, optional): 起始规则的名称。 默认为 "origin"。
            count (int, optional): 生成文本的数量。 默认为 1。

        Returns:
            str or list[str]: 如果 count 为 1，则返回单个字符串；否则返回字符串列表。
            
        Raises:
            ValueError: 如果指定的 'rule_name' 在语法中不存在。
        """
        if rule_name not in self.grammar:
            raise ValueError(f"规则 '{rule_name}' 不存在")
        
        results = []
        for _ in range(count):
            # 为每个故事生成一个独立的短期记忆库
            used_phrases = {}
            template = self.grammar[rule_name]
            result = self._expand_template(template, used_phrases)
            results.append(result)
        
        return results if count > 1 else results[0]
    
    def _expand_template(self, template, used_phrases):
        """递归展开模板中的占位符，并使用短期记忆来避免重复。

        Args:
            template (str or list): 要展开的模板字符串或列表。
            used_phrases (dict): 用于存储当前生成会话中已使用词组的字典。

        Returns:
            str: 完全展开后的字符串。
        """
        if isinstance(template, list):
            # 对于模板列表，我们依然随机选择一个作为起点
            template = random.choice(template)
        
        pattern = r'#(\w+)#'
        
        def replace_placeholder(match):
            rule_name = match.group(1)
            if rule_name in self.grammar:
                choices = self.grammar[rule_name]
                if isinstance(choices, list):
                    # 初始化当前规则的记忆
                    if rule_name not in used_phrases:
                        used_phrases[rule_name] = set()

                    # 找出尚未使用的选项
                    available_choices = [c for c in choices if c not in used_phrases[rule_name]]
                    
                    # 如果所有选项都用过了，就重置记忆
                    if not available_choices:
                        used_phrases[rule_name] = set()
                        available_choices = choices

                    # 从可用选项中随机选择
                    chosen = random.choice(available_choices)
                    used_phrases[rule_name].add(chosen)
                    return chosen
                else:
                    # 对于嵌套规则，继续递归展开
                    return self._expand_template(choices, used_phrases)
            else:
                return match.group(0)
        
        max_iterations = 20
        for _ in range(max_iterations):
            new_template = re.sub(pattern, replace_placeholder, template)
            if new_template == template:
                break
            template = new_template
        
        return template

class TraceryTextGenerator(BaseTextGenerator):
    """使用tracery库的文本生成器。"""
    
    def __init__(self, language='en'):
        """初始化 TraceryTextGenerator。

        Args:
            language (str, optional): 目标语言, 'en'或'zh'。 默认为 'en'。

        Raises:
            ImportError: 如果 tracery 库未能成功导入。
        """
        # 导入tracery
        success, self.tracery = try_import_tracery()
        if not success:
            raise ImportError("tracery库不可用")
        
        # 调用基类初始化
        super().__init__(language)

    def set_grammar(self, grammar_rules):
        """使用 tracery 库设置语法规则。

        Args:
            grammar_rules (dict): 一个包含语法规则的字典。
        """
        self.grammar = self.tracery.Grammar(grammar_rules)

    def generate(self, rule_name="origin", count=1):
        """使用 tracery 库根据规则生成文本。

        Args:
            rule_name (str, optional): 起始规则的名称。 默认为 "origin"。
            count (int, optional): 生成文本的数量。 默认为 1。

        Returns:
            str or list[str]: 如果 count 为 1，则返回单个字符串；否则返回字符串列表。

        Raises:
            ValueError: 如果语法规则未设置。
        """
        if self.grammar is None:
            raise ValueError("Grammar rules are not set.")
        
        results = []
        for _ in range(count):
            result = self.grammar.flatten(f"#{rule_name}#")
            results.append(result)
        
        return results if count > 1 else results[0]

def create_text_generator(language='en'):
    """智能文本生成器工厂函数，优先使用Tracery，失败则回退到自定义生成器。

    Args:
        language (str, optional): 目标语言, 'en'或'zh'。 默认为 'en'。

    Returns:
        BaseTextGenerator: 一个文本生成器实例 (TraceryTextGenerator 或 AdvancedTextGenerator)。
    """
    # 首先尝试使用tracery
    success, _ = try_import_tracery()
    
    if success:
        print("✅ 使用tracery库 + 高级语法规则")
        try:
            return TraceryTextGenerator(language)
        except Exception as e:
            print(f"❌ tracery初始化失败: {e}")
            print("🔄 切换到高级自定义生成器")
    else:
        print("🔧 使用高级自定义文本生成器")
    
    return AdvancedTextGenerator(language)

# 使用示例
if __name__ == "__main__":
    print(f"Python版本: {sys.version}")
    print("=" * 80)
    
    try:
        # 生成英文长故事
        print("\n📖 英文长故事生成:")
        print("-" * 50)
        generator_en = create_text_generator(language='en')
        stories_en = generator_en.generate_multiple_stories(3)
        for story in stories_en:
            print(story)
            print("-" * 50)

        # 生成中文长故事
        print("\n📖 中文长故事生成:")
        print("-" * 50)
        generator_zh = create_text_generator(language='zh')
        stories_zh = generator_zh.generate_multiple_stories(3)
        for story in stories_zh:
            print(story)
            print("-" * 50)

        # 生成主题故事集合
        print("\n🎭 主题故事集合 (中文):")
        print("-" * 50)
        theme_stories = generator_zh.generate_story_collection()
        for story in theme_stories:
            print(story)
            print("-" * 50)
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc()