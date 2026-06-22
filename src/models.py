"""
数据模型定义
定义舆情数据、用户画像、报警记录的数据库结构
"""

from datetime import datetime
from sqlalchemy import (
    create_engine, Column, Integer, String, Text,
    DateTime, Float, Boolean, Enum
)
from sqlalchemy.orm import declarative_base, sessionmaker
import enum

Base = declarative_base()


class RiskLevel(enum.Enum):
    """风险等级"""
    HIGH = "high"       # 高风险：明确投诉/施压
    MEDIUM = "medium"   # 中风险：质疑/不满
    LOW = "low"         # 低风险：中性提及
    UNKNOWN = "unknown" # 待判断


class CrawlStatus(enum.Enum):
    """爬取状态"""
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"  # 部分成功


class UserType(enum.Enum):
    """用户类型判断"""
    NORMAL_COMPLAINT = "normal_complaint"   # 正常误伤投诉
    SUSPECTED_FRAUD = "suspected_fraud"     # 疑似诈骗用户施压
    UNKNOWN = "unknown"                     # 待核查


class SentimentPost(Base):
    """
    舆情帖子/内容记录
    对应自媒体上的一条帖子、评论或文章
    """
    __tablename__ = "sentiment_posts"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 内容信息
    platform = Column(String(50), nullable=False, comment="平台：weibo/douyin/xiaohongshu等")
    post_id = Column(String(200), unique=True, comment="平台原始ID（防重复）")
    title = Column(String(500), comment="标题（文章/视频标题）")
    content = Column(Text, comment="正文内容")
    url = Column(String(1000), comment="原文链接")

    # 作者信息
    author_name = Column(String(200), comment="作者昵称")
    author_id = Column(String(200), comment="平台作者ID")
    author_followers = Column(Integer, default=0, comment="粉丝数")
    author_verified = Column(Boolean, default=False, comment="是否认证账号")

    # 传播数据
    view_count = Column(Integer, default=0, comment="浏览量")
    like_count = Column(Integer, default=0, comment="点赞数")
    comment_count = Column(Integer, default=0, comment="评论数")
    share_count = Column(Integer, default=0, comment="转发/分享数")

    # 分析结果
    risk_level = Column(Enum(RiskLevel), default=RiskLevel.UNKNOWN, comment="风险等级")
    sentiment_score = Column(Float, default=0.0, comment="情感分值 -1(负面)~1(正面)")
    matched_keywords = Column(Text, comment="命中关键词（逗号分隔）")
    user_type = Column(Enum(UserType), default=UserType.UNKNOWN, comment="用户类型判断")

    # 关联信息（如能关联到具体用户）
    phone_number = Column(String(20), comment="关联手机号（如帖子中提及）")
    shutdown_time = Column(DateTime, comment="疑似关停时间（从内容推断）")

    # 系统信息
    crawled_at = Column(DateTime, default=datetime.utcnow, comment="抓取时间")
    published_at = Column(DateTime, comment="原文发布时间")
    is_processed = Column(Boolean, default=False, comment="是否已人工处理")
    operator_note = Column(Text, comment="运营人员备注")
    is_ningxia = Column(Boolean, default=False, comment="是否宁夏相关")
    image_urls = Column(Text, comment="帖子中的图片链接（逗号分隔）")

    def __repr__(self):
        return f"<SentimentPost {self.platform}:{self.post_id} risk={self.risk_level}>"


class UserProfile(Base):
    """
    用户核查档案
    汇聚同一用户在多平台的投诉/舆情记录
    """
    __tablename__ = "user_profiles"

    id = Column(Integer, primary_key=True, autoincrement=True)

    # 身份信息
    phone_number = Column(String(20), unique=True, comment="手机号")
    real_name = Column(String(100), comment="实名（内部系统核查后填入）")
    id_card_hash = Column(String(100), comment="身份证号哈希（脱敏存储）")

    # 关停信息
    shutdown_date = Column(DateTime, comment="关停日期")
    shutdown_reason = Column(String(500), comment="关停原因代码/描述")
    model_score = Column(Float, comment="反诈模型评分")
    is_confirmed_fraud = Column(Boolean, default=False, comment="是否已确认为诈骗用户")
    is_confirmed_normal = Column(Boolean, default=False, comment="是否已确认为误伤用户")

    # 舆情统计
    post_count = Column(Integer, default=0, comment="发帖数量")
    total_exposure = Column(Integer, default=0, comment="累计曝光量")
    highest_risk = Column(Enum(RiskLevel), default=RiskLevel.UNKNOWN, comment="最高风险等级")
    last_active = Column(DateTime, comment="最近舆情时间")

    # 处置信息
    is_restored = Column(Boolean, default=False, comment="是否已恢复号码")
    restored_at = Column(DateTime, comment="恢复时间")
    handle_note = Column(Text, comment="处置备注")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<UserProfile {self.phone_number}>"


class AlertRecord(Base):
    """
    告警记录
    高风险舆情触发的告警
    """
    __tablename__ = "alert_records"

    id = Column(Integer, primary_key=True, autoincrement=True)
    post_id = Column(Integer, comment="关联帖子ID")
    alert_type = Column(String(100), comment="告警类型")
    alert_message = Column(Text, comment="告警内容")
    is_handled = Column(Boolean, default=False, comment="是否已处理")
    handled_by = Column(String(100), comment="处理人")
    handled_at = Column(DateTime, comment="处理时间")
    created_at = Column(DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<AlertRecord {self.alert_type} handled={self.is_handled}>"


class CrawlLog(Base):
    """
    爬取日志
    记录每次爬取的执行情况
    """
    __tablename__ = "crawl_logs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    platform = Column(String(50), nullable=False, comment="平台名称")
    status = Column(Enum(CrawlStatus), default=CrawlStatus.SUCCESS, comment="爬取状态")
    keywords_count = Column(Integer, default=0, comment="关键词数量")
    new_posts_count = Column(Integer, default=0, comment="新增记录数")
    error_message = Column(Text, comment="错误信息")
    started_at = Column(DateTime, default=datetime.utcnow, comment="开始时间")
    finished_at = Column(DateTime, comment="结束时间")
    duration_seconds = Column(Integer, comment="耗时（秒）")

    def __repr__(self):
        return f"<CrawlLog {self.platform} {self.status} at {self.started_at}>"


def init_db(db_url: str = "sqlite:///data/monitor.db"):
    """初始化数据库"""
    engine = create_engine(db_url, echo=False)
    Base.metadata.create_all(engine)
    Session = sessionmaker(bind=engine)
    return engine, Session


if __name__ == "__main__":
    engine, Session = init_db()
    print("数据库初始化完成")
