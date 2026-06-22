#!/usr/bin/env python3
"""
生成展示用假数据 - 优化版
模拟真实场景：数据量充足、日期分布自然、平台状态合理
"""

import os
import sys
import random
from datetime import datetime, timedelta, date

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.models import init_db, SentimentPost, RiskLevel
from loguru import logger

# 展示数据库路径
DEMO_DB = os.path.join(PROJECT_ROOT, "data", "demo.db")

# 删除旧的展示数据库
if os.path.exists(DEMO_DB):
    os.remove(DEMO_DB)
    logger.info("已删除旧展示数据库")

engine, Session = init_db(f"sqlite:///{DEMO_DB}")
session = Session()

# ========== 平台配置 ==========
# 微博和知乎正常，抖音和小红书有数据，贴吧异常，快手不接入
PLATFORMS = {
    "weibo": {"weight": 35, "name": "微博"},
    "zhihu": {"weight": 40, "name": "知乎"},
    "douyin": {"weight": 15, "name": "抖音"},
    "xiaohongshu": {"weight": 8, "name": "小红书"},
    "other": {"weight": 2, "name": "其他"},
}

NICKNAMES = {
    "weibo": ["阳光下的泡沫", "宁夏小王", "银川市民张先生", "被封号的打工人", "移动用户维权", 
              "普通老百姓说两句", "反诈受害者联盟", "号卡被封求助", "打工人日记", "宁夏新闻",
              "银川生活通", "移动用户吐槽", "被停机的销售", "维权进行时"],
    "zhihu": ["匿名用户", "通信从业者老李", "法律人张三", "被误封的程序员", "运营商内部人士", 
              "反诈中心工作人员", "移动客服吐槽", "10年老用户", "技术流分析", "业内人说法",
              "通信工程师", "前移动员工", "法律援助者"],
    "douyin": ["宁夏大叔", "被停机的小妹", "维权日记", "反诈真实经历", "移动用户心声", 
               "普通用户发声", "被封号的外卖员", "银川小李", "生活记录者", "真实故事分享"],
    "xiaohongshu": ["信女愿意暴富暴瘦", "被反诈停卡的我", "移动受害者", "小红书维权达人", 
                    "宁夏姐妹", "打工人的委屈", "用户维权日记"],
    "other": ["匿名网友", "路过的打工人", "普通用户", "热心市民"],
}

CONTENTS = {
    "high_risk": [
        "我的号码13895123456被移动无故停机了，打客服没人理，投诉了三次都没有结果，这不是欺负消费者吗？我要向工信部投诉！",
        "中国移动以反诈名义把我的号封了，我做生意的号码，一天打几十个电话不是很正常吗？凭什么说我是诈骗？要求立即恢复！",
        "被移动强制停机一个月了，申诉无效，客服永远是系统判定，我要曝光这种侵权行为！",
        "宁夏移动用户13469611605称，2026年5月2日下午4:00被无故暂停部分通信功能，严重影响工作生活，要求立即恢复并赔偿损失。",
        "移动乱封号，我的号码正常使用，突然就被停机了，说是涉嫌诈骗，我连诈骗电话都没接过！这不是冤枉人吗？",
        "反诈误封！我就是接了几个外地客户的电话，移动就把我的号停了，客服说系统自动判定，人为复核都不给，太过分了！",
        "12321投诉中国移动恶意封号，我的号码用了10年了，突然被停机，没有任何通知，没有任何证据，这是侵权！",
        "中国移动真🐶！打了十多个业务电话就被强制停机了？手机号涉嫌诈骗？你们不管真正的诈骗电话，把普通用户当什么了？",
        "我是一名外卖员，靠手机号接单，被移动停机后直接失业了，你们赔我损失！",
        "移动客服态度恶劣，问什么都是系统判定，我要投诉到底！工信部投诉电话多少？",
        "被停机两周了，严重影响工作，领导都找我谈话了，移动你们能不能给个说法？",
        "反诈系统误判，把我正常号码停了，营业厅说要等7个工作日审核，我等得起吗？",
    ],
    "medium_risk": [
        "被中国移动以反诈名义频繁停机，但我从来没有过任何异常行为。客服永远只有一句话系统判定。我问判定标准是什么？触发了哪条规则？有没有人为复核？他们什么都拿不出来。",
        "反诈中心给我打电话，说我的号码有风险，让我去营业厅核实。我去了，工作人员查了半天说没问题，但号码还是被限制了，这是什么操作？",
        "手机卡被封了，去营业厅解封，工作人员说要签承诺书。我问凭什么？他说系统判定的，他也没办法。",
        "正常使用电话卡结果被反诈提醒停卡了？中国移动你是发神经了吗？怎么投诉啊？",
        "号码被停机三天了，打10086永远是排队，好不容易接通了说是系统问题，让我等，等到什么时候？",
        "移动客服不回应，申诉无效，我的号码什么时候能恢复？已经影响到工作了。",
        "被限制呼出了，打不出去电话，客服说要本人去营业厅，我在外地出差怎么去？",
        "反诈骚扰！我一天接了三个反诈中心的电话，都是问同样的问题，烦不烦啊？",
        "移动的反诈系统是不是太敏感了？我就是给客户打了几个电话，就被停机了。",
        "申诉了一个星期了，还没结果，移动的效率真让人无语。",
        "号码被停了，但移动不告诉原因，就说系统判定，这算什么解释？",
        "反诈中心说要核实身份，但营业厅说没问题，到底听谁的？",
    ],
    "low_risk": [
        "今天接到反诈中心的电话，提醒我注意防范电信诈骗，挺好的，点赞。",
        "中国移动的反诈系统确实厉害，帮我拦截了好几个诈骗电话。",
        "断卡行动效果显著，最近诈骗电话明显少了。",
        "反诈中心来电提醒我不要接听陌生电话，服务态度很好。",
        "移动的反诈APP挺有用的，能识别诈骗电话。",
        "国家反诈中心的宣传做得不错，现在大家都提高了警惕。",
        "运营商加强监管是好事，虽然有时候会误伤，但总体是保护用户的。",
        "防诈骗意识很重要，大家都要提高警惕。",
        "反诈中心的工作人员认真负责，给他们点赞。",
        "移动的反诈系统帮我拦了一个冒充公检法的电话，感谢！",
        "最近诈骗电话少了，应该是反诈行动的效果。",
        "建议大家都安装反诈APP，真的有用。",
        "运营商在反诈方面做了很多工作，值得肯定。",
        "断卡行动以来，诈骗案件明显下降，这是好事。",
    ],
}

NINGXIA_CONTENTS = [
    "宁夏移动用户13469611605反映，被无故暂停通信功能，银川市公安局反诈中心核实后确认为误封。",
    "石嘴山市移动用户投诉反诈系统误判，要求恢复号码正常使用。",
    "宁夏联通用户反馈，收到反诈提醒短信后号码被限制，吴忠反诈中心正在核查。",
    "银川反诈中心发布通告，近期将对异常号码进行集中清理，请用户配合核实。",
    "宁夏移动反诈专项行动开展以来，已关停涉诈号码XXX个，同时也收到多起误封投诉。",
    "固原市用户反映，因频繁拨打外地号码被移动停机，中卫反诈中心表示将优化判定模型。",
    "宁夏移动用户反映，号码被停机后影响正常生活，希望运营商能优化判定机制。",
    "银川市用户投诉移动反诈系统误判，营业厅表示将加急处理。",
    "宁夏反诈中心提醒：接到陌生电话要提高警惕，如有疑问可拨打96110咨询。",
    "吴忠市移动用户反映，因工作需要频繁拨打电话被停机，希望运营商能区分正常业务和诈骗行为。",
]


def random_date_range(start_date, end_date, count):
    """在日期范围内生成随机时间点，模拟真实分布"""
    dates = []
    current = start_date
    
    while current <= end_date:
        # 工作日数据多，周末少
        if current.weekday() < 5:  # 周一到周五
            day_count = random.randint(int(count * 0.8), int(count * 1.2))
        else:  # 周末
            day_count = random.randint(int(count * 0.3), int(count * 0.6))
        
        for _ in range(day_count):
            hour = random.choices(
                range(24),
                weights=[1,1,1,1,1,2,3,5,8,10,10,8,6,5,6,8,10,10,8,6,4,3,2,1]
            )[0]
            minute = random.randint(0, 59)
            dates.append(datetime.combine(current, datetime.min.time()).replace(hour=hour, minute=minute))
        
        current += timedelta(days=1)
    
    return sorted(dates)


def generate_posts():
    """生成舆情数据"""
    posts = []
    
    # 日期范围：过去90天
    end_date = date.today()
    start_date = end_date - timedelta(days=90)
    
    # 生成时间点（每天约20-30条，总计约2000-2500条）
    timestamps = random_date_range(start_date, end_date, 25)
    
    logger.info(f"生成 {len(timestamps)} 条数据，时间范围: {start_date} ~ {end_date}")
    
    for i, ts in enumerate(timestamps):
        # 随机选择风险等级
        risk = random.choices(
            ["high", "medium", "low"],
            weights=[12, 28, 60]
        )[0]
        
        # 随机选择平台
        platform = random.choices(
            list(PLATFORMS.keys()),
            weights=[p["weight"] for p in PLATFORMS.values()]
        )[0]
        
        # 获取内容
        content = random.choice(CONTENTS[f"{risk}_risk"])
        
        # 宁夏相关内容 (约12%)
        is_ningxia = False
        if random.random() < 0.12:
            content = random.choice(NINGXIA_CONTENTS)
            is_ningxia = True
        
        # 互动数据
        if risk == "high":
            likes = random.randint(10, 800)
            comments = random.randint(5, 150)
            shares = random.randint(2, 80)
        elif risk == "medium":
            likes = random.randint(2, 200)
            comments = random.randint(1, 50)
            shares = random.randint(0, 20)
        else:
            likes = random.randint(0, 80)
            comments = random.randint(0, 15)
            shares = random.randint(0, 8)
        
        # 关键词
        keywords_map = {
            "high": ["无故停机", "恶意封号", "工信部投诉", "强制停机", "反诈误封", "欺负消费者", "侵权", "曝光"],
            "medium": ["反诈", "号码关停", "停机原因", "申诉无效", "反诈骚扰", "客服不回应", "被限制"],
            "low": ["反诈中心", "防诈骗", "断卡行动", "反诈提醒"],
        }
        keywords = random.choice(keywords_map[risk])
        
        # 作者
        author = random.choice(NICKNAMES.get(platform, NICKNAMES["other"]))
        
        # 手机号（30%概率）
        phone = None
        if random.random() < 0.3:
            prefixes = ["13895", "13469", "15009", "18209", "19509", "13519", "15109", "18709"]
            prefix = random.choice(prefixes)
            suffix = "".join([str(random.randint(0, 9)) for _ in range(5)])
            phone = prefix + suffix
        
        # URL
        if platform == "weibo":
            url = f"https://weibo.com/{random.randint(1000000, 9999999)}/{random.randint(100000, 999999)}"
        elif platform == "zhihu":
            url = f"https://www.zhihu.com/question/{random.randint(1000000, 9999999)}/answer/{random.randint(10000000, 99999999)}"
        elif platform == "douyin":
            url = f"https://www.douyin.com/video/{random.randint(7000000000000000000, 7999999999999999999)}"
        elif platform == "xiaohongshu":
            url = f"https://www.xiaohongshu.com/explore/{random.randint(10000000000000000000, 19999999999999999999)}"
        else:
            url = None
        
        post = SentimentPost(
            platform=platform,
            post_id=f"demo_{i}_{random.randint(10000, 99999)}",
            title=content[:50] if len(content) > 50 else content,
            content=content,
            url=url,
            author_name=author,
            author_id=f"user_{random.randint(10000, 99999)}",
            author_followers=random.randint(10, 50000),
            author_verified=random.random() < 0.15,
            view_count=random.randint(100, 100000),
            like_count=likes,
            comment_count=comments,
            share_count=shares,
            risk_level=RiskLevel(risk),
            sentiment_score=round(random.uniform(0.1, 0.9), 2),
            matched_keywords=keywords,
            phone_number=phone,
            is_ningxia=is_ningxia,
            published_at=ts,
            crawled_at=ts + timedelta(minutes=random.randint(5, 180)),
        )
        posts.append(post)
    
    return posts


def main():
    """生成并保存数据"""
    logger.info("开始生成展示数据...")
    
    posts = generate_posts()
    
    for post in posts:
        session.add(post)
    
    session.commit()
    
    # 统计
    total = len(posts)
    high = sum(1 for p in posts if p.risk_level == RiskLevel.HIGH)
    medium = sum(1 for p in posts if p.risk_level == RiskLevel.MEDIUM)
    low = sum(1 for p in posts if p.risk_level == RiskLevel.LOW)
    ningxia = sum(1 for p in posts if p.is_ningxia)
    
    platform_counts = {}
    for p in posts:
        platform_counts[p.platform] = platform_counts.get(p.platform, 0) + 1
    
    # 按时间排序
    posts_sorted = sorted(posts, key=lambda p: p.published_at or datetime.min, reverse=True)
    
    logger.success(f"展示数据生成完成！")
    logger.info(f"数据库路径: {DEMO_DB}")
    logger.info(f"总数: {total}")
    logger.info(f"风险分布: 高={high} ({high*100//total}%), 中={medium} ({medium*100//total}%), 低={low} ({low*100//total}%)")
    logger.info(f"宁夏相关: {ningxia} ({ningxia*100//total}%)")
    logger.info(f"平台分布: {platform_counts}")
    logger.info(f"时间范围: {posts_sorted[-1].published_at} ~ {posts_sorted[0].published_at}")
    
    session.close()


if __name__ == "__main__":
    main()
