"""
情感分析与风险评级模块
基于关键词匹配 + 情感分值对舆情进行分级
"""

import re
from dataclasses import dataclass, field
from typing import List, Tuple

import jieba
from snownlp import SnowNLP
from loguru import logger


# -------------------------------------------------------
# 风险评级规则
# -------------------------------------------------------

# 高风险关键词（必须完整匹配短语）
HIGH_RISK_KEYWORDS = [
    "中国移动封号", "移动乱封号", "移动侵权", "恶意封号",
    "反诈误封", "反诈误伤", "号码被封", "恶意关停",
    "强制停机", "无故停机", "12321投诉", "工信部投诉",
    "欺负消费者", "曝光运营商", "集体投诉",
]

# 中风险关键词
MEDIUM_RISK_KEYWORDS = [
    "反诈", "号码关停", "中国移动投诉", "移动服务差",
    "12381", "国家反诈", "运营商监管", "停机原因",
    "移动客服不回应", "申诉无效", "号码异常", "被限制",
    "打不了电话", "反诈骚扰",
]

# 核心主题词（内容必须包含以下至少一个，才视为反诈相关）
CORE_TOPIC_KEYWORDS = [
    "反诈", "封号", "停机", "关停", "运营商", "中国移动",
    "号码", "电话卡", "手机卡", "SIM卡", "实名", "认证",
    "诈骗", "诈骗电话", "诈骗短信", "断卡",
]

# 排除词（包含以下任意一个，直接排除，不计入风险）
EXCLUDE_KEYWORDS = [
    "游戏封号", "微信封号", "支付宝", "银行卡", "信用卡",
    "交通违章", "违章", "罚款", "扣分", "12123", "交管",
    "淘宝", "京东", "拼多多", "外卖", "快递",
    "游戏", "账号被封", "QQ封号", "抖音封号",
]

# -------------------------------------------------------
# 疑似诈骗用户施压特征词（此类用户可能在用舆论对抗监管）
# -------------------------------------------------------
SUSPECTED_FRAUD_PATTERNS = [
    r"号码正常.*被封",
    r"没有诈骗.*停机",
    r"冤枉.*中国移动",
    r"你们凭什么",
    r"施压",
    r"联合抵制",
    r"曝光.*运营商",
    r"集体.*投诉",
]

# -------------------------------------------------------
# 宁夏区域特征关键词
# -------------------------------------------------------
NINGXIA_IDENTIFIER_KEYWORDS = [
    # 省级标识
    "宁夏移动", "宁夏联通", "宁夏电信",
    "宁夏反诈中心", "宁夏自治区反诈中心", "宁夏公安反诈中心",
    # 地市反诈中心关键词（按实际辖区填写）
    "银川反诈", "石嘴山反诈", "吴忠反诈", "固原反诈", "中卫反诈",
]

# 宁夏手机号段前缀（09结尾为宁夏）- 精确匹配5位
NINGXIA_PHONE_PREFIXES = [
    "13469", "13519", "13619", "13709", "13895", "13995",
    "14709", "15009", "15109", "15209", "15709", "15809", "15909",
    "17809", "18209", "18309", "18409", "18709", "18809", "19509", "19809",
]

# -------------------------------------------------------
# 反诈核验链接特征（用户贴出短信截图时常见）
# -------------------------------------------------------
VERIFICATION_LINK_PATTERNS = [
    # 按实际使用的二次实名核验链接填写，避免提交内部域名
    r"your-verify-domain\.example\.com",
    r"/capability/secondaryCertification",
    r"videorealname",
    r"realNameVerify",
    r"sc-enter\.html",
    r"sc-center\.html",
]

# 传播量阈值（超过此值视为高传播）
HIGH_SPREAD_THRESHOLD = {
    "view_count": 10000,
    "like_count": 500,
    "share_count": 200,
    "comment_count": 100,
}


@dataclass
class AnalysisResult:
    """单条舆情分析结果"""
    post_id: str
    platform: str

    # 关键词命中
    matched_high: List[str] = field(default_factory=list)
    matched_medium: List[str] = field(default_factory=list)

    # 情感分值 0~1，越低越负面（SnowNLP输出范围）
    sentiment_score: float = 0.5

    # 是否符合疑似诈骗用户施压模式
    suspected_fraud_flag: bool = False
    suspected_fraud_reason: str = ""

    # 宁夏区域识别
    is_ningxia: bool = False
    ningxia_identifiers: List[str] = field(default_factory=list)
    ningxia_phones: List[str] = field(default_factory=list)

    # 反诈核验链接检测
    has_verification_link: bool = False
    verification_links_found: List[str] = field(default_factory=list)

    # 最终风险等级
    risk_level: str = "low"   # high / medium / low

    # 传播风险（高传播=True）
    high_spread: bool = False

    # 提取的手机号（从内容中）
    mentioned_phones: List[str] = field(default_factory=list)


class SentimentAnalyzer:
    """舆情分析器"""

    def __init__(
        self,
        high_risk_kws: List[str] = None,
        medium_risk_kws: List[str] = None,
        core_topic_kws: List[str] = None,
        exclude_kws: List[str] = None,
    ):
        self.high_risk_kws = high_risk_kws or HIGH_RISK_KEYWORDS
        self.medium_risk_kws = medium_risk_kws or MEDIUM_RISK_KEYWORDS
        self.core_topic_kws = core_topic_kws or CORE_TOPIC_KEYWORDS
        self.exclude_kws = exclude_kws or EXCLUDE_KEYWORDS

    def analyze(self, post) -> AnalysisResult:
        """
        对单条帖子进行分析
        :param post: RawPost 或包含 platform/post_id/content/title/... 的对象
        :return: AnalysisResult
        """
        text = f"{getattr(post, 'title', '')} {getattr(post, 'content', '')}".strip()

        result = AnalysisResult(
            post_id=getattr(post, "post_id", ""),
            platform=getattr(post, "platform", ""),
        )

        # 0. 排除词检查 - 如果命中排除词，直接标记为无关
        excluded = [kw for kw in self.exclude_kws if kw in text]
        if excluded:
            result.risk_level = "low"
            result.matched_high = []
            result.matched_medium = []
            return result

        # 1. 核心主题检查 - 必须涉及反诈相关主题
        has_core_topic = any(kw in text for kw in self.core_topic_kws)
        
        # 2. 关键词匹配（只在有核心主题时才匹配）
        if has_core_topic:
            result.matched_high = [kw for kw in self.high_risk_kws if kw in text]
            result.matched_medium = [kw for kw in self.medium_risk_kws if kw in text]
        else:
            # 没有核心主题，即使有关键词也不算
            result.matched_high = []
            result.matched_medium = []

        # 2. 情感分析
        try:
            if text:
                result.sentiment_score = SnowNLP(text).sentiments
        except Exception as e:
            logger.debug(f"情感分析失败: {e}")
            result.sentiment_score = 0.5

        # 3. 疑似诈骗用户施压检测
        for pattern in SUSPECTED_FRAUD_PATTERNS:
            if re.search(pattern, text):
                result.suspected_fraud_flag = True
                result.suspected_fraud_reason = pattern
                break

        # 4. 宁夏区域识别
        result.ningxia_identifiers = [kw for kw in NINGXIA_IDENTIFIER_KEYWORDS if kw in text]
        
        # 检查手机号段是否为宁夏号段
        phones = re.findall(r"1[3-9]\d{9}", text)
        result.ningxia_phones = [p for p in phones if any(p.startswith(prefix) for prefix in NINGXIA_PHONE_PREFIXES)]
        
        # 判断是否为宁夏舆情：有宁夏关键词 或 有宁夏号段
        result.is_ningxia = bool(result.ningxia_identifiers) or bool(result.ningxia_phones)

        # 5. 反诈核验链接检测
        for pattern in VERIFICATION_LINK_PATTERNS:
            matches = re.findall(pattern, text, re.IGNORECASE)
            if matches:
                result.verification_links_found.extend(matches)
        result.has_verification_link = bool(result.verification_links_found)

        # 6. 传播量风险判断
        for field_name, threshold in HIGH_SPREAD_THRESHOLD.items():
            val = getattr(post, field_name, 0) or 0
            if val >= threshold:
                result.high_spread = True
                break

        # 7. 综合风险评级
        result.risk_level = self._calc_risk_level(result)

        # 8. 提取手机号
        result.mentioned_phones = phones

        return result

    def _calc_risk_level(self, r: AnalysisResult) -> str:
        """综合评分，确定风险等级"""
        # 如果没有命中任何关键词，直接低风险
        if not r.matched_high and not r.matched_medium:
            return "low"
        
        score = 0

        # 高风险关键词 +4分/个（短语匹配，权重更高）
        score += len(r.matched_high) * 3
        # 中风险关键词 +2分/个
        score += len(r.matched_medium) * 1
        # 情感极负面（<0.2）+2分
        if r.sentiment_score < 0.2:
            score += 2
        elif r.sentiment_score < 0.4:
            score += 1
        # 疑似诈骗施压 +3分
        if r.suspected_fraud_flag:
            score += 3
        # 高传播 +2分
        if r.high_spread:
            score += 2

        if score >= 4:
            return "high"
        elif score >= 2:
            return "medium"
        else:
            return "low"
