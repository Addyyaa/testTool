import sys
import random
import re

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
                "#weather_setting# #location_setting#，#character_intro#。"
            ],
            
            # 故事主体
            "story_body": [
                "#character_action# #event_detail# #character_feeling#。#plot_development# #challenge_description#。",
                "#character_discovery# #event_detail# #surprise_element#。#character_reaction# #plot_twist#。"
            ],
            
            # 故事结尾
            "story_end": [
                "#resolution# #final_thought# #future_hope#。",
                "#conclusion# #wisdom_gained# #positive_ending#。"
            ],
            
            # 时间设置
            "time_setting": [
                "在一个阳光明媚的早晨", "在夕阳西下的傍晚", "在星光闪烁的夜晚"
            ],
            
            # 地点设置
            "location_setting": [
                "在繁华的城市中心", "在宁静的乡村小镇", "在美丽的海滨城市"
            ],
            
            # 角色介绍
            "character_intro": [
                "一位#character_trait#的#character_role#", 
                "有着#character_quality#品质的#character_role#"
            ],
            
            # 角色特征
            "character_trait": ["勇敢", "智慧", "善良", "坚强", "乐观"],
            "character_role": ["学生", "老师", "艺术家", "科学家", "工程师"],
            "character_quality": ["诚实", "勤奋", "耐心", "热情", "专注"],
            
            # 天气设置
            "weather_setting": [
                "在温暖的阳光下", "在清新的雨后", "在凉爽的微风中"
            ],
            
            # 角色行动
            "character_action": [
                "他决定开始一段新的旅程", "她发现了一个有趣的项目", "他们组成了一个团队"
            ],
            
            # 事件细节
            "event_detail": [
                "通过不断的努力和练习", "借助现代科技的帮助", "与志同道合的朋友合作"
            ],
            
            # 角色感受
            "character_feeling": [
                "感到无比的兴奋和满足", "体验到成长的喜悦", "收获了宝贵的经验"
            ],
            
            # 情节发展
            "plot_development": [
                "在这个过程中", "随着时间的推移", "经过深思熟虑"
            ],
            
            # 挑战描述
            "challenge_description": [
                "他们遇到了技术难题，但没有放弃", "面临时间压力，却更加专注", "遭遇挫折，但从中学到了宝贵的经验"
            ],
            
            # 角色发现
            "character_discovery": [
                "在探索的过程中，他发现", "通过仔细观察，她意识到"
            ],
            
            # 惊喜元素
            "surprise_element": [
                "这个发现比预期的更加重要", "结果超出了所有人的想象", "这个方法比传统方式更有效"
            ],
            
            # 角色反应
            "character_reaction": [
                "他们兴奋地分享了这个好消息", "她立即开始制定新的计划", "他决定将这个经验传授给他人"
            ],
            
            # 情节转折
            "plot_twist": [
                "这个成功为他们打开了新的机会", "这个经历让他们重新思考目标", "这个发现改变了他们的人生轨迹"
            ],
            
            # 解决方案
            "resolution": [
                "最终，他们成功地完成了目标", "经过努力，问题得到了完美解决", "通过合作，他们实现了共同的愿望"
            ],
            
            # 最终思考
            "final_thought": [
                "这个经历让他们更加自信", "这次成功给了他们更多动力", "这个成就让他们感到自豪"
            ],
            
            # 未来希望
            "future_hope": [
                "他们期待着更多的冒险和挑战", "她计划将这个经验应用到更多领域", "他们希望能够帮助更多的人"
            ],
            
            # 结论
            "conclusion": [
                "这个故事告诉我们", "这个经历证明了", "这次成功展示了"
            ],
            
            # 获得的智慧
            "wisdom_gained": [
                "梦想需要行动来实现", "困难是成长的机会", "合作能创造奇迹"
            ],
            
            # 积极结局
            "positive_ending": [
                "未来充满了无限可能", "新的旅程即将开始", "更美好的明天在等待着他们"
            ]
        }

    def _get_english_grammar(self):
        """返回英文的语法规则 - 更丰富的内容"""
        return {
            "origin": "#story_start# #story_body# #story_end#",
            
            # Story beginnings
            "story_start": [
                "#time_setting#, #location_setting#, #character_intro#.",
                "#weather_setting# #location_setting#, #character_intro#."
            ],
            
            # Story body
            "story_body": [
                "#character_action# #event_detail# #character_feeling#. #plot_development# #challenge_description#.",
                "#character_discovery# #event_detail# #surprise_element#. #character_reaction# #plot_twist#."
            ],
            
            # Story endings
            "story_end": [
                "#resolution# #final_thought# #future_hope#.",
                "#conclusion# #wisdom_gained# #positive_ending#."
            ],
            
            # Time settings
            "time_setting": [
                "On a bright sunny morning", "During a peaceful evening", "Under the starlit night"
            ],
            
            # Location settings
            "location_setting": [
                "in the bustling city center", "in a quiet countryside village", "by the beautiful seaside"
            ],
            
            # Character introductions
            "character_intro": [
                "a #character_trait# #character_role#", 
                "a #character_role# with #character_quality# qualities"
            ],
            
            # Character traits
            "character_trait": ["brave", "wise", "kind", "strong", "optimistic"],
            "character_role": ["student", "teacher", "artist", "scientist", "engineer"],
            "character_quality": ["honest", "hardworking", "patient", "enthusiastic", "focused"],
            
            # Weather settings
            "weather_setting": [
                "Under the warm sunshine", "After a refreshing rain", "In the cool breeze"
            ],
            
            # Character actions
            "character_action": [
                "They decided to embark on a new journey", "She discovered an interesting project", "They formed a team"
            ],
            
            # Event details
            "event_detail": [
                "through continuous effort and practice", "with the help of modern technology", "by collaborating with like-minded friends"
            ],
            
            # Character feelings
            "character_feeling": [
                "feeling incredibly excited and satisfied", "experiencing the joy of growth", "gaining valuable experience"
            ],
            
            # Plot development
            "plot_development": [
                "During this process", "As time went on", "After careful consideration"
            ],
            
            # Challenge descriptions
            "challenge_description": [
                "they encountered technical difficulties but didn't give up", "faced time pressure but became more focused", "met setbacks but learned valuable lessons"
            ],
            
            # Character discoveries
            "character_discovery": [
                "During exploration, he discovered", "Through careful observation, she realized"
            ],
            
            # Surprise elements
            "surprise_element": [
                "this discovery was more important than expected", "the results exceeded everyone's imagination", "this method was more effective than traditional approaches"
            ],
            
            # Character reactions
            "character_reaction": [
                "They excitedly shared this good news", "She immediately began making new plans", "He decided to teach this experience to others"
            ],
            
            # Plot twists
            "plot_twist": [
                "This success opened new opportunities for them", "This experience made them reconsider their goals", "This discovery changed their life trajectory"
            ],
            
            # Resolutions
            "resolution": [
                "Finally, they successfully achieved their goal", "Through effort, the problem was perfectly solved", "Through cooperation, they realized their shared dream"
            ],
            
            # Final thoughts
            "final_thought": [
                "This experience made them more confident", "This success gave them more motivation", "This achievement made them feel proud"
            ],
            
            # Future hopes
            "future_hope": [
                "They look forward to more adventures and challenges", "She plans to apply this experience to more fields", "They hope to help more people"
            ],
            
            # Conclusions
            "conclusion": [
                "This story tells us", "This experience proves", "This success demonstrates"
            ],
            
            # Wisdom gained
            "wisdom_gained": [
                "dreams need action to be realized", "difficulties are opportunities for growth", "cooperation can create miracles"
            ],
            
            # Positive endings
            "positive_ending": [
                "the future is full of infinite possibilities", "a new journey is about to begin", "a better tomorrow awaits them"
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
        
        max_iterations = 20
        for _ in range(max_iterations):
            new_template = re.sub(pattern, replace_placeholder, template)
            if new_template == template:
                break
            template = new_template
        
        return template

# 使用示例
if __name__ == "__main__":
    print("🔧 高级文本生成器测试")
    print("=" * 60)
    
    try:
        # 生成中文长故事
        print("\n📖 中文长故事生成:")
        print("-" * 40)
        generator_zh = AdvancedTextGenerator(language='zh')
        stories_zh = generator_zh.generate_multiple_stories(2)
        for story in stories_zh:
            print(story)
            print("-" * 40)

        # 生成英文长故事
        print("\n📖 英文长故事生成:")
        print("-" * 40)
        generator_en = AdvancedTextGenerator(language='en')
        stories_en = generator_en.generate_multiple_stories(2)
        for story in stories_en:
            print(story)
            print("-" * 40)
            
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        import traceback
        traceback.print_exc() 