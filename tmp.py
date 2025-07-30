import sys
import random
import re

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

class AdvancedTextGenerator:
    """高级文本生成器，生成更丰富的内容"""
    
    def __init__(self, language='en'):
        self.language = language
        self.grammar = {}
        
        # 根据语言初始化语法规则
        if language == 'zh':
            self.set_grammar(self._get_chinese_grammar())
        else:
            self.set_grammar(self._get_english_grammar())

    def _get_chinese_grammar(self):
        """返回中文的语法规则 - 更丰富的内容"""
        return {
            "origin": "#story_start# #story_body# #story_end#",
            
            # 故事开头
            "story_start": [
                "#time_setting#，#location_setting#，#character_intro#。",
                "#weather_setting# #location_setting#，#character_intro#。",
                "#time_setting#，#character_intro#在#location_setting#。"
            ],
            
            # 故事主体
            "story_body": [
                "#character_action# #event_detail# #character_feeling#。#plot_development# #challenge_description#。",
                "#character_discovery# #event_detail# #surprise_element#。#character_reaction# #plot_twist#。",
                "#daily_activity# #unexpected_event# #character_response#。#lesson_learned# #growth_moment#。"
            ],
            
            # 故事结尾
            "story_end": [
                "#resolution# #final_thought# #future_hope#。",
                "#conclusion# #wisdom_gained# #positive_ending#。",
                "#achievement# #celebration# #new_beginning#。"
            ],
            
            # 时间设置
            "time_setting": [
                "在一个阳光明媚的早晨", "在夕阳西下的傍晚", "在星光闪烁的夜晚",
                "在春暖花开的季节", "在秋高气爽的日子", "在雪花纷飞的冬日"
            ],
            
            # 地点设置
            "location_setting": [
                "在繁华的城市中心", "在宁静的乡村小镇", "在美丽的海滨城市",
                "在古老的图书馆里", "在充满活力的校园", "在神秘的森林深处"
            ],
            
            # 角色介绍
            "character_intro": [
                "一位#character_trait#的#character_role#", 
                "有着#character_quality#品质的#character_role#",
                "充满#character_emotion#的#character_role#"
            ],
            
            # 角色特征
            "character_trait": ["勇敢", "智慧", "善良", "坚强", "乐观", "创新"],
            "character_role": ["学生", "老师", "艺术家", "科学家", "工程师", "医生"],
            "character_quality": ["诚实", "勤奋", "耐心", "热情", "专注", "友善"],
            "character_emotion": ["希望", "梦想", "好奇心", "决心", "激情", "温暖"],
            
            # 天气设置
            "weather_setting": [
                "在温暖的阳光下", "在清新的雨后", "在凉爽的微风中",
                "在金色的黄昏里", "在银色的月光下", "在晶莹的雪景中"
            ],
            
            # 角色行动
            "character_action": [
                "他决定开始一段新的旅程", "她发现了一个有趣的项目", "他们组成了一个团队",
                "她制定了一个详细的计划", "他开始学习新的技能", "她决定帮助他人"
            ],
            
            # 事件细节
            "event_detail": [
                "通过不断的努力和练习", "借助现代科技的帮助", "与志同道合的朋友合作",
                "运用创新的思维方式", "结合理论与实践", "发挥团队协作的力量"
            ],
            
            # 角色感受
            "character_feeling": [
                "感到无比的兴奋和满足", "体验到成长的喜悦", "收获了宝贵的经验",
                "感受到友谊的温暖", "获得了内心的平静", "发现了生活的美好"
            ],
            
            # 情节发展
            "plot_development": [
                "在这个过程中", "随着时间的推移", "经过深思熟虑",
                "面对各种挑战", "在朋友的支持下", "通过不懈的努力"
            ],
            
            # 挑战描述
            "challenge_description": [
                "他们遇到了技术难题，但没有放弃", "面临时间压力，却更加专注",
                "遭遇挫折，但从中学到了宝贵的经验", "碰到困难，却激发了更大的潜能"
            ],
            
            # 角色发现
            "character_discovery": [
                "在探索的过程中，他发现", "通过仔细观察，她意识到", "在研究中，他们发现"
            ],
            
            # 惊喜元素
            "surprise_element": [
                "这个发现比预期的更加重要", "结果超出了所有人的想象",
                "这个方法比传统方式更有效", "这个创意获得了广泛的认可"
            ],
            
            # 角色反应
            "character_reaction": [
                "他们兴奋地分享了这个好消息", "她立即开始制定新的计划",
                "他决定将这个经验传授给他人", "她感到前所未有的成就感"
            ],
            
            # 情节转折
            "plot_twist": [
                "这个成功为他们打开了新的机会", "这个经历让他们重新思考目标",
                "这个发现改变了他们的人生轨迹", "这个成就激励他们追求更大的梦想"
            ],
            
            # 日常活动
            "daily_activity": [
                "在日常的学习中", "在平凡的工作里", "在与朋友的交流中",
                "在解决问题的过程中", "在创作的时光里", "在思考的时刻"
            ],
            
            # 意外事件
            "unexpected_event": [
                "他们遇到了意想不到的机会", "发生了令人惊喜的变化",
                "出现了新的可能性", "碰到了有趣的挑战"
            ],
            
            # 角色回应
            "character_response": [
                "他们积极地拥抱这个变化", "她勇敢地接受了挑战",
                "他们用智慧解决了问题", "她以开放的心态面对未知"
            ],
            
            # 学到的教训
            "lesson_learned": [
                "这个经历让他们明白", "通过这次体验，他们学会了",
                "这个过程教会了他们", "这次经历让他们懂得了"
            ],
            
            # 成长时刻
            "growth_moment": [
                "坚持不懈的重要性", "团队合作的价值", "创新思维的力量",
                "学习的乐趣", "帮助他人的意义", "追求梦想的勇气"
            ],
            
            # 解决方案
            "resolution": [
                "最终，他们成功地完成了目标", "经过努力，问题得到了完美解决",
                "通过合作，他们实现了共同的愿望", "凭借智慧和勇气，他们克服了困难"
            ],
            
            # 最终思考
            "final_thought": [
                "这个经历让他们更加自信", "这次成功给了他们更多动力",
                "这个成就让他们感到自豪", "这个过程让他们更加成熟"
            ],
            
            # 未来希望
            "future_hope": [
                "他们期待着更多的冒险和挑战", "她计划将这个经验应用到更多领域",
                "他们希望能够帮助更多的人", "她决定继续追求更高的目标"
            ],
            
            # 结论
            "conclusion": [
                "这个故事告诉我们", "这个经历证明了", "这次成功展示了"
            ],
            
            # 获得的智慧
            "wisdom_gained": [
                "梦想需要行动来实现", "困难是成长的机会", "合作能创造奇迹",
                "学习是终身的旅程", "创新来自于勇于尝试", "成功源于不断努力"
            ],
            
            # 积极结局
            "positive_ending": [
                "未来充满了无限可能", "新的旅程即将开始", "更美好的明天在等待着他们",
                "这只是成功的开始", "更大的梦想正在召唤", "生活变得更加精彩"
            ],
            
            # 成就
            "achievement": [
                "他们的努力得到了认可", "这个项目获得了巨大成功",
                "他们的创新获得了奖励", "这个成果超越了预期"
            ],
            
            # 庆祝
            "celebration": [
                "整个团队一起庆祝这个胜利", "朋友们为他们感到骄傲",
                "这个成功值得纪念", "这是一个值得分享的时刻"
            ],
            
            # 新开始
            "new_beginning": [
                "这个结束也是新的开始", "更多的机会在前方等待",
                "新的冒险即将启程", "更大的舞台正在召唤他们"
            ]
        }

    def _get_english_grammar(self):
        """返回英文的语法规则 - 更丰富的内容"""
        return {
            "origin": "#story_start# #story_body# #story_end#",
            
            # Story beginnings
            "story_start": [
                "#time_setting#, #location_setting#, #character_intro#.",
                "#weather_setting# #location_setting#, #character_intro#.",
                "#time_setting#, #character_intro# found themselves #location_setting#."
            ],
            
            # Story body
            "story_body": [
                "#character_action# #event_detail# #character_feeling#. #plot_development# #challenge_description#.",
                "#character_discovery# #event_detail# #surprise_element#. #character_reaction# #plot_twist#.",
                "#daily_activity# #unexpected_event# #character_response#. #lesson_learned# #growth_moment#."
            ],
            
            # Story endings
            "story_end": [
                "#resolution# #final_thought# #future_hope#.",
                "#conclusion# #wisdom_gained# #positive_ending#.",
                "#achievement# #celebration# #new_beginning#."
            ],
            
            # Time settings
            "time_setting": [
                "On a bright sunny morning", "During a peaceful evening", "Under the starlit night",
                "In the heart of spring", "On a crisp autumn day", "During a snowy winter afternoon"
            ],
            
            # Location settings
            "location_setting": [
                "in the bustling city center", "in a quiet countryside village", "by the beautiful seaside",
                "in an ancient library", "on a vibrant campus", "deep in a mysterious forest"
            ],
            
            # Character introductions
            "character_intro": [
                "a #character_trait# #character_role#", 
                "a #character_role# with #character_quality# qualities",
                "a #character_role# filled with #character_emotion#"
            ],
            
            # Character traits
            "character_trait": ["brave", "wise", "kind", "strong", "optimistic", "innovative"],
            "character_role": ["student", "teacher", "artist", "scientist", "engineer", "doctor"],
            "character_quality": ["honest", "hardworking", "patient", "enthusiastic", "focused", "friendly"],
            "character_emotion": ["hope", "dreams", "curiosity", "determination", "passion", "warmth"],
            
            # Weather settings
            "weather_setting": [
                "Under the warm sunshine", "After a refreshing rain", "In the cool breeze",
                "During the golden sunset", "Under the silver moonlight", "In the sparkling snow"
            ],
            
            # Character actions
            "character_action": [
                "They decided to embark on a new journey", "She discovered an interesting project", "They formed a team",
                "She created a detailed plan", "He began learning new skills", "She decided to help others"
            ],
            
            # Event details
            "event_detail": [
                "through continuous effort and practice", "with the help of modern technology", "by collaborating with like-minded friends",
                "using innovative thinking", "combining theory with practice", "leveraging the power of teamwork"
            ],
            
            # Character feelings
            "character_feeling": [
                "feeling incredibly excited and satisfied", "experiencing the joy of growth", "gaining valuable experience",
                "feeling the warmth of friendship", "achieving inner peace", "discovering the beauty of life"
            ],
            
            # Plot development
            "plot_development": [
                "During this process", "As time went on", "After careful consideration",
                "Facing various challenges", "With friends' support", "Through persistent effort"
            ],
            
            # Challenge descriptions
            "challenge_description": [
                "they encountered technical difficulties but didn't give up", "faced time pressure but became more focused",
                "met setbacks but learned valuable lessons", "hit obstacles but unlocked greater potential"
            ],
            
            # Character discoveries
            "character_discovery": [
                "During exploration, he discovered", "Through careful observation, she realized", "In their research, they found"
            ],
            
            # Surprise elements
            "surprise_element": [
                "this discovery was more important than expected", "the results exceeded everyone's imagination",
                "this method was more effective than traditional approaches", "this idea gained widespread recognition"
            ],
            
            # Character reactions
            "character_reaction": [
                "They excitedly shared this good news", "She immediately began making new plans",
                "He decided to teach this experience to others", "She felt unprecedented achievement"
            ],
            
            # Plot twists
            "plot_twist": [
                "This success opened new opportunities for them", "This experience made them reconsider their goals",
                "This discovery changed their life trajectory", "This achievement inspired them to pursue bigger dreams"
            ],
            
            # Daily activities
            "daily_activity": [
                "In their daily studies", "In ordinary work", "In conversations with friends",
                "In the process of solving problems", "During creative time", "In moments of reflection"
            ],
            
            # Unexpected events
            "unexpected_event": [
                "they encountered unexpected opportunities", "surprising changes occurred",
                "new possibilities emerged", "interesting challenges appeared"
            ],
            
            # Character responses
            "character_response": [
                "they actively embraced this change", "she bravely accepted the challenge",
                "they used wisdom to solve the problem", "she faced the unknown with an open mind"
            ],
            
            # Lessons learned
            "lesson_learned": [
                "This experience taught them", "Through this experience, they learned",
                "This process taught them", "This experience made them understand"
            ],
            
            # Growth moments
            "growth_moment": [
                "the importance of persistence", "the value of teamwork", "the power of innovative thinking",
                "the joy of learning", "the meaning of helping others", "the courage to pursue dreams"
            ],
            
            # Resolutions
            "resolution": [
                "Finally, they successfully achieved their goal", "Through effort, the problem was perfectly solved",
                "Through cooperation, they realized their shared dream", "With wisdom and courage, they overcame difficulties"
            ],
            
            # Final thoughts
            "final_thought": [
                "This experience made them more confident", "This success gave them more motivation",
                "This achievement made them feel proud", "This process made them more mature"
            ],
            
            # Future hopes
            "future_hope": [
                "They look forward to more adventures and challenges", "She plans to apply this experience to more fields",
                "They hope to help more people", "She decided to continue pursuing higher goals"
            ],
            
            # Conclusions
            "conclusion": [
                "This story tells us", "This experience proves", "This success demonstrates"
            ],
            
            # Wisdom gained
            "wisdom_gained": [
                "dreams need action to be realized", "difficulties are opportunities for growth", "cooperation can create miracles",
                "learning is a lifelong journey", "innovation comes from daring to try", "success comes from continuous effort"
            ],
            
            # Positive endings
            "positive_ending": [
                "the future is full of infinite possibilities", "a new journey is about to begin", "a better tomorrow awaits them",
                "this is just the beginning of success", "bigger dreams are calling", "life becomes more exciting"
            ],
            
            # Achievements
            "achievement": [
                "Their efforts were recognized", "This project achieved great success",
                "Their innovation was rewarded", "This result exceeded expectations"
            ],
            
            # Celebrations
            "celebration": [
                "the whole team celebrated this victory together", "friends were proud of them",
                "this success was worth commemorating", "this was a moment worth sharing"
            ],
            
            # New beginnings
            "new_beginning": [
                "This ending is also a new beginning", "More opportunities await ahead",
                "A new adventure is about to start", "A bigger stage is calling them"
            ]
        }

    def set_grammar(self, grammar_rules):
        """设置语法规则"""
        self.grammar = grammar_rules

    def generate(self, rule_name="origin", count=1):
        """生成文本"""
        if rule_name not in self.grammar:
            raise ValueError(f"规则 '{rule_name}' 不存在")
        
        results = []
        for _ in range(count):
            template = self.grammar[rule_name]
            result = self._expand_template(template)
            results.append(result)
        
        return results if count > 1 else results[0]
    
    def generate_multiple_stories(self, count=3):
        """生成多个完整故事"""
        stories = []
        for i in range(count):
            story = self.generate("origin")
            stories.append(f"故事 {i+1}:\n{story}\n" if self.language == 'zh' else f"Story {i+1}:\n{story}\n")
        return stories
    
    def generate_story_collection(self, themes=None):
        """生成主题故事集合"""
        if themes is None:
            themes = ["adventure", "friendship", "discovery", "growth", "innovation"] if self.language == 'en' else ["冒险", "友谊", "发现", "成长", "创新"]
        
        collection = []
        for theme in themes:
            story = self.generate("origin")
            collection.append(f"主题: {theme}\n{story}\n" if self.language == 'zh' else f"Theme: {theme}\n{story}\n")
        
        return collection
    
    def _expand_template(self, template):
        """展开模板中的占位符"""
        if isinstance(template, list):
            template = random.choice(template)
        
        pattern = r'#(\w+)#'
        
        def replace_placeholder(match):
            rule_name = match.group(1)
            if rule_name in self.grammar:
                choices = self.grammar[rule_name]
                if isinstance(choices, list):
                    return random.choice(choices)
                else:
                    return self._expand_template(choices)
            else:
                return match.group(0)
        
        max_iterations = 20  # 增加迭代次数以支持更复杂的模板
        for _ in range(max_iterations):
            new_template = re.sub(pattern, replace_placeholder, template)
            if new_template == template:
                break
            template = new_template
        
        return template

class TraceryTextGenerator:
    """使用tracery库的文本生成器"""
    
    def __init__(self, language='en'):
        self.language = language
        self.grammar = None
        
        # 导入tracery
        success, self.tracery = try_import_tracery()
        if not success:
            raise ImportError("tracery库不可用")
        
        # 使用高级语法规则
        generator = AdvancedTextGenerator(language)
        self.set_grammar(generator.grammar)

    def set_grammar(self, grammar_rules):
        self.grammar = self.tracery.Grammar(grammar_rules)

    def generate(self, rule_name="origin", count=1):
        if self.grammar is None:
            raise ValueError("Grammar rules are not set.")
        
        results = []
        for _ in range(count):
            result = self.grammar.flatten(f"#{rule_name}#")
            results.append(result)
        
        return results if count > 1 else results[0]
    
    def generate_multiple_stories(self, count=3):
        """生成多个完整故事"""
        stories = []
        for i in range(count):
            story = self.generate("origin")
            stories.append(f"故事 {i+1}:\n{story}\n" if self.language == 'zh' else f"Story {i+1}:\n{story}\n")
        return stories
    
    def generate_story_collection(self, themes=None):
        """生成主题故事集合"""
        if themes is None:
            themes = ["adventure", "friendship", "discovery", "growth", "innovation"] if self.language == 'en' else ["冒险", "友谊", "发现", "成长", "创新"]
        
        collection = []
        for theme in themes:
            story = self.generate("origin")
            collection.append(f"主题: {theme}\n{story}\n" if self.language == 'zh' else f"Theme: {theme}\n{story}\n")
        
        return collection

def TextGenerator(language='en'):
    """智能文本生成器工厂函数"""
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
        generator_en = TextGenerator(language='en')
        stories_en = generator_en.generate_multiple_stories(3)
        for story in stories_en:
            print(story)
            print("-" * 50)

        # 生成中文长故事
        print("\n📖 中文长故事生成:")
        print("-" * 50)
        generator_zh = TextGenerator(language='zh')
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