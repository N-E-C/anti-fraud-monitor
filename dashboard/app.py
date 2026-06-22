#!/usr/bin/env python3
"""
反诈舆情监测可视化 Dashboard
基于 Flask + Bootstrap 构建
"""

import os
import sys
import io
import csv
import json
from datetime import datetime, timedelta
from collections import defaultdict

from flask import Flask, render_template, request, jsonify, Response
from flask_cors import CORS
from loguru import logger

# 项目根目录
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from src.models import init_db, SentimentPost, RiskLevel, CrawlLog, CrawlStatus
from sqlalchemy import func, desc, extract

app = Flask(__name__)
CORS(app)

# 数据库连接
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{PROJECT_ROOT}/data/monitor.db")
engine, Session = init_db(DATABASE_URL)

# 平台配置
DEMO_MODE = os.getenv("DATABASE_URL", "").endswith("demo.db")

# 平台配置 - 根据模式调整状态
def get_platforms():
    """获取平台配置，根据是否展示模式返回不同状态"""
    if DEMO_MODE:
        # 展示模式：快手不接入，贴吧异常，其他正常
        return {
            "weibo": {"name": "微博", "icon": "📱", "bg_color": "#fef2f2", "text_color": "#dc2626", "status": "normal", "desc": "正常运行，每日自动爬取"},
            "zhihu": {"name": "知乎", "icon": "💡", "bg_color": "#eff6ff", "text_color": "#2563eb", "status": "normal", "desc": "正常运行，每日自动爬取"},
            "baidu_tieba": {"name": "贴吧", "icon": "💬", "bg_color": "#f0fdf4", "text_color": "#16a34a", "status": "error", "desc": "百度贴吧反爬机制，返回403"},
            "douyin": {"name": "抖音", "icon": "🎵", "bg_color": "#fdf4ff", "text_color": "#9333ea", "status": "normal", "desc": "正常运行，每日自动爬取"},
            "kuaishou": {"name": "快手", "icon": "🎬", "bg_color": "#fffbeb", "text_color": "#d97706", "status": "disabled", "desc": "暂未接入数据源"},
            "xiaohongshu": {"name": "小红书", "icon": "📕", "bg_color": "#fef2f2", "text_color": "#e11d48", "status": "normal", "desc": "正常运行，每日自动爬取"},
        }
    else:
        # 正式模式
        return {
            "weibo": {"name": "微博", "icon": "📱", "bg_color": "#fef2f2", "text_color": "#dc2626", "status": "normal", "desc": "正常运行，每日自动爬取"},
            "zhihu": {"name": "知乎", "icon": "💡", "bg_color": "#eff6ff", "text_color": "#2563eb", "status": "normal", "desc": "正常运行，每日自动爬取"},
            "baidu_tieba": {"name": "贴吧", "icon": "💬", "bg_color": "#f0fdf4", "text_color": "#16a34a", "status": "error", "desc": "百度贴吧反爬机制，返回403"},
            "douyin": {"name": "抖音", "icon": "🎵", "bg_color": "#fdf4ff", "text_color": "#9333ea", "status": "disabled", "desc": "暂未接入数据源"},
            "kuaishou": {"name": "快手", "icon": "🎬", "bg_color": "#fffbeb", "text_color": "#d97706", "status": "disabled", "desc": "暂未接入数据源"},
            "xiaohongshu": {"name": "小红书", "icon": "📕", "bg_color": "#fef2f2", "text_color": "#e11d48", "status": "disabled", "desc": "暂未接入数据源"},
        }


def get_session():
    return Session()


def format_datetime(dt):
    """格式化日期时间"""
    if dt:
        return dt.strftime("%Y-%m-%d %H:%M")
    return "-"


def risk_level_display(level):
    """风险等级显示"""
    if not level:
        return "未知"
    mapping = {
        "high": "🔴 高风险",
        "medium": "🟡 中风险",
        "low": "🟢 低风险",
    }
    return mapping.get(level.value if hasattr(level, 'value') else str(level), "未知")


def get_trend_data(session):
    """获取趋势数据（按天统计）"""
    now = datetime.utcnow()
    
    # 近30天数据
    trend = {"week": {"labels": [], "high": [], "medium": [], "low": []},
             "month": {"labels": [], "high": [], "medium": [], "low": []}}
    
    for days_ago in range(30, -1, -1):
        date = now - timedelta(days=days_ago)
        date_str = date.strftime("%m-%d")
        
        # 当天开始和结束
        day_start = date.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(days=1)
        
        # 统计当天各风险等级数量
        high = session.query(SentimentPost).filter(
            SentimentPost.crawled_at >= day_start,
            SentimentPost.crawled_at < day_end,
            SentimentPost.risk_level == RiskLevel.HIGH
        ).count()
        
        medium = session.query(SentimentPost).filter(
            SentimentPost.crawled_at >= day_start,
            SentimentPost.crawled_at < day_end,
            SentimentPost.risk_level == RiskLevel.MEDIUM
        ).count()
        
        low = session.query(SentimentPost).filter(
            SentimentPost.crawled_at >= day_start,
            SentimentPost.crawled_at < day_end,
            SentimentPost.risk_level == RiskLevel.LOW
        ).count()
        
        trend["month"]["labels"].append(date_str)
        trend["month"]["high"].append(high)
        trend["month"]["medium"].append(medium)
        trend["month"]["low"].append(low)
    
    # 近7天
    trend["week"]["labels"] = trend["month"]["labels"][-7:]
    trend["week"]["high"] = trend["month"]["high"][-7:]
    trend["week"]["medium"] = trend["month"]["medium"][-7:]
    trend["week"]["low"] = trend["month"]["low"][-7:]
    
    return trend


# ========== 路由 ==========
@app.route("/")
def index():
    """首页 - 数据概览"""
    session = get_session()
    try:
        # 统计数据
        total = session.query(SentimentPost).count()
        high = session.query(SentimentPost).filter_by(risk_level=RiskLevel.HIGH).count()
        medium = session.query(SentimentPost).filter_by(risk_level=RiskLevel.MEDIUM).count()
        low = session.query(SentimentPost).filter_by(risk_level=RiskLevel.LOW).count()
        
        # 平台分布
        platform_counts = dict(session.query(
            SentimentPost.platform, func.count()
        ).group_by(SentimentPost.platform).all())
        
        # 构建平台信息列表
        all_platforms = []
        for pid, pinfo in get_platforms().items():
            all_platforms.append({
                "id": pid,
                "name": pinfo["name"],
                "icon": pinfo["icon"],
                "bg_color": pinfo["bg_color"],
                "text_color": pinfo["text_color"],
                "status": pinfo["status"],
                "count": platform_counts.get(pid, 0),
            })
        
        # 平台图表数据
        platform_names = json.dumps([p["name"] for p in all_platforms])
        platform_counts_list = [p["count"] for p in all_platforms]
        platform_colors = json.dumps([
            p["text_color"] if p["count"] > 0 else "#cbd5e1" 
            for p in all_platforms
        ])
        
        # 最近爬取时间
        latest = session.query(SentimentPost).order_by(desc(SentimentPost.crawled_at)).first()
        latest_crawl = latest.crawled_at if latest else None
        
        # 宁夏相关数量
        ningxia_count = session.query(SentimentPost).filter_by(is_ningxia=True).count()
        ningxia_high = session.query(SentimentPost).filter_by(is_ningxia=True, risk_level=RiskLevel.HIGH).count()
        ningxia_medium = session.query(SentimentPost).filter_by(is_ningxia=True, risk_level=RiskLevel.MEDIUM).count()
        ningxia_low = session.query(SentimentPost).filter_by(is_ningxia=True, risk_level=RiskLevel.LOW).count()
        
        # 趋势数据
        trend_data = get_trend_data(session)
        
        return render_template("index.html",
            total=total,
            high=high,
            medium=medium,
            low=low,
            all_platforms=all_platforms,
            platform_names=platform_names,
            platform_counts=json.dumps(platform_counts_list),
            platform_colors=platform_colors,
            latest_crawl=latest_crawl,
            ningxia_count=ningxia_count,
            ningxia_high=ningxia_high,
            ningxia_medium=ningxia_medium,
            ningxia_low=ningxia_low,
            trend_data=json.dumps(trend_data),
            format_datetime=format_datetime,
        )
    finally:
        session.close()


@app.route("/posts")
def posts_page():
    """全部舆情页面"""
    session = get_session()
    try:
        platform = request.args.get("platform", "")
        risk_level = request.args.get("risk_level", "")
        keyword = request.args.get("keyword", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        
        query = session.query(SentimentPost)
        
        if platform:
            query = query.filter(SentimentPost.platform == platform)
        if risk_level:
            risk_map = {"high": RiskLevel.HIGH, "medium": RiskLevel.MEDIUM, "low": RiskLevel.LOW}
            if risk_level in risk_map:
                query = query.filter(SentimentPost.risk_level == risk_map[risk_level])
        if keyword:
            query = query.filter(
                SentimentPost.content.contains(keyword) |
                SentimentPost.matched_keywords.contains(keyword)
            )
        if start_date:
            query = query.filter(SentimentPost.published_at >= start_date)
        if end_date:
            query = query.filter(SentimentPost.published_at <= end_date + " 23:59:59")
        
        total = query.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        
        posts = query.order_by(desc(SentimentPost.crawled_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return render_template("posts.html",
            posts=posts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            platform=platform,
            risk_level=risk_level,
            keyword=keyword,
            start_date=start_date,
            end_date=end_date,
            platforms=get_platforms(),
            format_datetime=format_datetime,
            risk_level_display=risk_level_display,
        )
    finally:
        session.close()


@app.route("/ningxia")
def ningxia_page():
    """宁夏舆情页面"""
    session = get_session()
    try:
        platform = request.args.get("platform", "")
        risk_level = request.args.get("risk_level", "")
        page = int(request.args.get("page", 1))
        page_size = int(request.args.get("page_size", 50))
        
        query = session.query(SentimentPost).filter_by(is_ningxia=True)
        
        if platform:
            query = query.filter(SentimentPost.platform == platform)
        if risk_level:
            risk_map = {"high": RiskLevel.HIGH, "medium": RiskLevel.MEDIUM, "low": RiskLevel.LOW}
            if risk_level in risk_map:
                query = query.filter(SentimentPost.risk_level == risk_map[risk_level])
        
        total = query.count()
        total_pages = max(1, (total + page_size - 1) // page_size)
        
        posts = query.order_by(desc(SentimentPost.crawled_at)).offset(
            (page - 1) * page_size
        ).limit(page_size).all()
        
        return render_template("ningxia.html",
            posts=posts,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages,
            platform=platform,
            risk_level=risk_level,
            platforms=get_platforms(),
            format_datetime=format_datetime,
            risk_level_display=risk_level_display,
        )
    finally:
        session.close()


@app.route("/post/<int:post_id>")
def post_detail(post_id):
    """舆情详情页面"""
    session = get_session()
    try:
        post = session.query(SentimentPost).get(post_id)
        if not post:
            return "记录不存在", 404
        
        ref = request.args.get("ref", "posts")
        back_url = f"/{ref}" if ref in ["posts", "ningxia"] else "/posts"
        
        return render_template("detail.html",
            post=post,
            back_url=back_url,
            platforms=get_platforms(),
            format_datetime=format_datetime,
            risk_level_display=risk_level_display,
        )
    finally:
        session.close()


@app.route("/status")
def status_page():
    """爬取状态页面"""
    session = get_session()
    try:
        total = session.query(SentimentPost).count()
        latest = session.query(SentimentPost).order_by(desc(SentimentPost.crawled_at)).first()
        latest_crawl = latest.crawled_at if latest else None
        
        # 获取各平台数据量
        platform_counts = dict(session.query(
            SentimentPost.platform, func.count()
        ).group_by(SentimentPost.platform).all())
        
        # 使用动态平台配置
        platforms_config = get_platforms()
        platform_status = {}
        for pid, pinfo in platforms_config.items():
            platform_status[pid] = {
                "name": pinfo["name"],
                "status": "正常" if pinfo["status"] == "normal" else ("异常" if pinfo["status"] == "error" else "未接入"),
                "status_class": pinfo["status"],
                "desc": pinfo.get("desc", ""),
            }
        
        crawl_logs = session.query(CrawlLog).order_by(desc(CrawlLog.started_at)).limit(50).all()
        
        return render_template("status.html",
            total=total,
            latest_crawl=latest_crawl,
            platform_status=platform_status,
            platform_counts=platform_counts,
            crawl_logs=crawl_logs,
            format_datetime=format_datetime,
        )
    finally:
        session.close()


# ========== API 接口 ==========
@app.route("/api/export")
def api_export():
    """导出数据 API"""
    session = get_session()
    try:
        platform = request.args.get("platform", "")
        risk_level = request.args.get("risk_level", "")
        keyword = request.args.get("keyword", "")
        is_ningxia = request.args.get("is_ningxia", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")
        limit = int(request.args.get("limit", 1000))
        fmt = request.args.get("format", "csv")
        
        query = session.query(SentimentPost)
        
        if platform:
            query = query.filter(SentimentPost.platform == platform)
        if risk_level:
            risk_map = {"high": RiskLevel.HIGH, "medium": RiskLevel.MEDIUM, "low": RiskLevel.LOW}
            if risk_level in risk_map:
                query = query.filter(SentimentPost.risk_level == risk_map[risk_level])
        if keyword:
            query = query.filter(
                SentimentPost.content.contains(keyword) |
                SentimentPost.matched_keywords.contains(keyword)
            )
        if is_ningxia == "true":
            query = query.filter(SentimentPost.is_ningxia == True)
        if start_date:
            query = query.filter(SentimentPost.published_at >= start_date)
        if end_date:
            query = query.filter(SentimentPost.published_at <= end_date + " 23:59:59")
        
        posts = query.order_by(desc(SentimentPost.crawled_at)).limit(limit).all()
        
        if fmt == "csv":
            output = io.StringIO()
            writer = csv.writer(output)
            writer.writerow([
                "ID", "平台", "内容", "作者", "风险等级", "命中关键词",
                "手机号", "宁夏", "点赞", "评论", "转发", "发布时间", "爬取时间", "链接"
            ])
            
            for post in posts:
                writer.writerow([
                    post.id,
                    get_platforms().get(post.platform, {}).get("name", post.platform),
                    post.content,
                    post.author_name,
                    post.risk_level.value if post.risk_level else "未知",
                    post.matched_keywords,
                    post.phone_number or "",
                    "是" if post.is_ningxia else "",
                    post.like_count,
                    post.comment_count,
                    post.share_count,
                    format_datetime(post.published_at),
                    format_datetime(post.crawled_at),
                    post.url or "",
                ])
            
            output.seek(0)
            # 添加BOM头，让Excel正确识别UTF-8编码
            csv_content = '\ufeff' + output.getvalue()
            return Response(
                csv_content,
                mimetype="text/csv; charset=utf-8",
                headers={"Content-Disposition": f"attachment; filename=sentiment_{datetime.now().strftime('%Y%m%d_%H%M')}.csv"}
            )
        else:
            data = []
            for post in posts:
                data.append({
                    "ID": post.id,
                    "平台": get_platforms().get(post.platform, {}).get("name", post.platform),
                    "内容": post.content,
                    "作者": post.author_name,
                    "风险等级": post.risk_level.value if post.risk_level else "未知",
                    "命中关键词": post.matched_keywords,
                    "手机号": post.phone_number or "",
                    "宁夏": "是" if post.is_ningxia else "",
                    "点赞": post.like_count,
                    "评论": post.comment_count,
                    "转发": post.share_count,
                    "发布时间": format_datetime(post.published_at),
                    "爬取时间": format_datetime(post.crawled_at),
                    "链接": post.url or "",
                })
            return jsonify(data)
    finally:
        session.close()


@app.route("/api/stats")
def api_stats():
    """统计数据 API"""
    session = get_session()
    try:
        total = session.query(SentimentPost).count()
        high = session.query(SentimentPost).filter_by(risk_level=RiskLevel.HIGH).count()
        medium = session.query(SentimentPost).filter_by(risk_level=RiskLevel.MEDIUM).count()
        low = session.query(SentimentPost).filter_by(risk_level=RiskLevel.LOW).count()
        
        platforms = session.query(
            SentimentPost.platform, func.count()
        ).group_by(SentimentPost.platform).all()
        
        latest = session.query(SentimentPost).order_by(desc(SentimentPost.crawled_at)).first()
        
        return jsonify({
            "total": total,
            "high": high,
            "medium": medium,
            "low": low,
            "platforms": {get_platforms().get(p, {}).get("name", p): c for p, c in platforms},
            "latest_crawl": format_datetime(latest.crawled_at) if latest else None,
        })
    finally:
        session.close()


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=5000)
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--debug", action="store_true", default=False)
    args = parser.parse_args()
    
    print(f"Dashboard 启动: http://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=args.debug)
