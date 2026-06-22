#!/usr/bin/env python3
"""
邮件预警功能
当发现高风险舆情时，自动发送预警邮件
"""

import os
import sys
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders
from datetime import datetime

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

from loguru import logger


class EmailAlert:
    """邮件预警发送器"""
    
    def __init__(self):
        self.smtp_server = os.getenv("SMTP_SERVER", "smtp.139.com")
        self.smtp_port = int(os.getenv("SMTP_PORT", "465"))
        self.sender = os.getenv("SMTP_SENDER", "15709588632@139.com")
        self.password = os.getenv("SMTP_PASSWORD", "")
        self.receiver = os.getenv("ALERT_RECEIVER", "15709588632@139.com")
    
    def send_alert(self, subject, content, attachment_path=None):
        """发送预警邮件"""
        if not self.password:
            logger.warning("未配置邮箱密码，跳过邮件发送")
            return False
        
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender
            msg['To'] = self.receiver
            msg['Subject'] = subject
            
            # 正文
            msg.attach(MIMEText(content, 'html', 'utf-8'))
            
            # 附件
            if attachment_path and os.path.exists(attachment_path):
                with open(attachment_path, 'rb') as f:
                    part = MIMEBase('application', 'octet-stream')
                    part.set_payload(f.read())
                    encoders.encode_base64(part)
                    part.add_header('Content-Disposition', f'attachment; filename="{os.path.basename(attachment_path)}"')
                    msg.attach(part)
            
            # 发送
            server = smtplib.SMTP_SSL(self.smtp_server, self.smtp_port)
            server.login(self.sender, self.password)
            server.send_message(msg)
            server.quit()
            
            logger.success(f"预警邮件已发送: {subject}")
            return True
            
        except Exception as e:
            logger.error(f"邮件发送失败: {e}")
            return False
    
    def send_high_risk_alert(self, posts):
        """发送高风险舆情预警"""
        if not posts:
            return
        
        # 构建邮件内容
        subject = f"⚠️ 反诈舆情预警 - 发现 {len(posts)} 条高风险舆情 [{datetime.now().strftime('%m-%d %H:%M')}]"
        
        html = """
        <html>
        <head>
            <style>
                body { font-family: 'Microsoft YaHei', sans-serif; padding: 20px; }
                .header { background: #dc2626; color: white; padding: 15px; border-radius: 8px; }
                .post-item { border-left: 4px solid #dc2626; padding: 15px; margin: 10px 0; background: #fef2f2; border-radius: 0 8px 8px 0; }
                .post-content { font-weight: 500; margin: 8px 0; }
                .post-meta { color: #666; font-size: 13px; }
                .ningxia-badge { background: #7c3aed; color: white; padding: 2px 8px; border-radius: 4px; font-size: 12px; }
                .footer { margin-top: 30px; padding: 15px; background: #f1f5f9; border-radius: 8px; font-size: 12px; color: #666; }
            </style>
        </head>
        <body>
            <div class="header">
                <h2>⚠️ 反诈自媒体舆情智能监测系统 - 高风险预警</h2>
                <p>检测时间: """ + datetime.now().strftime("%Y-%m-%d %H:%M:%S") + """</p>
            </div>
        """
        
        PLATFORM_NAMES = {
            "weibo": "微博", "zhihu": "知乎", "baidu_tieba": "贴吧",
        }
        
        for i, post in enumerate(posts[:10], 1):  # 最多显示10条
            platform = PLATFORM_NAMES.get(post.platform, post.platform)
            ningxia = '<span class="ningxia-badge">宁夏</span>' if post.is_ningxia else ''
            
            html += f"""
            <div class="post-item">
                <div class="post-meta">
                    [{platform}] {post.author_name or '未知作者'} | 
                    命中: {post.matched_keywords or '-'} {ningxia}
                </div>
                <div class="post-content">{post.content[:200]}{'...' if len(post.content) > 200 else ''}</div>
                <div class="post-meta">
                    👍 {post.like_count} | 💬 {post.comment_count} | 🔄 {post.share_count}
                    {f' | <a href="{post.url}">查看原文</a>' if post.url else ''}
                </div>
            </div>
            """
        
        if len(posts) > 10:
            html += f"<p>... 还有 {len(posts) - 10} 条高风险舆情，请登录系统查看完整列表。</p>"
        
        html += """
            <div class="footer">
                <p>📊 <a href="http://localhost:5000">登录反诈舆情监测系统</a> 查看详情</p>
                <p>📋 请相关责任人及时核查处置，并在24小时内反馈核查报告。</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_alert(subject, html)
    
    def send_daily_report(self, report_path, stats):
        """发送日报邮件"""
        subject = f"📊 反诈舆情日报 [{stats['date']}] - 总量{stats['total']}条/高风险{stats['high']}条"
        
        PLATFORM_NAMES = {
            "weibo": "微博", "zhihu": "知乎", "baidu_tieba": "贴吧",
        }
        
        platform_str = "、".join([f"{PLATFORM_NAMES.get(k,k)}({v})" for k,v in sorted(stats['platforms'].items(), key=lambda x:-x[1])[:3]])
        
        html = f"""
        <html>
        <head>
            <style>
                body {{ font-family: 'Microsoft YaHei', sans-serif; padding: 20px; }}
                .header {{ background: #2563eb; color: white; padding: 15px; border-radius: 8px; }}
                .stats {{ display: flex; gap: 20px; margin: 20px 0; }}
                .stat-box {{ flex: 1; padding: 15px; background: #f8fafc; border-radius: 8px; text-align: center; }}
                .stat-value {{ font-size: 28px; font-weight: bold; }}
                .stat-label {{ color: #666; font-size: 13px; }}
                .high {{ color: #dc2626; }}
                .medium {{ color: #f59e0b; }}
                .low {{ color: #16a34a; }}
                .ningxia {{ color: #7c3aed; }}
                .footer {{ margin-top: 30px; padding: 15px; background: #f1f5f9; border-radius: 8px; font-size: 12px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h2>📊 反诈自媒体舆情智能监测系统 - 每日报告</h2>
                <p>报告日期: {stats['date']}</p>
            </div>
            
            <div class="stats">
                <div class="stat-box">
                    <div class="stat-value">{stats['total']}</div>
                    <div class="stat-label">数据总量</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value high">{stats['high']}</div>
                    <div class="stat-label">高风险</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value medium">{stats['medium']}</div>
                    <div class="stat-label">中风险</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value low">{stats['low']}</div>
                    <div class="stat-label">低风险</div>
                </div>
                <div class="stat-box">
                    <div class="stat-value ningxia">{stats['ningxia']}</div>
                    <div class="stat-label">宁夏相关 (高风险{stats['ningxia_high']})</div>
                </div>
            </div>
            
            <p><strong>主要平台:</strong> {platform_str}</p>
            
            <div class="footer">
                <p>📊 <a href="http://localhost:5000">登录反诈舆情监测系统</a> 查看详情</p>
                <p>📎 详细数据请查看附件Excel报表</p>
            </div>
        </body>
        </html>
        """
        
        return self.send_alert(subject, html, report_path)


# 配置说明
def print_config_guide():
    """打印配置指南"""
    print("""
=== 邮件预警配置 ===

在 .env 文件中添加以下配置：

# SMTP服务器设置
SMTP_SERVER=smtp.139.com
SMTP_PORT=465
SMTP_SENDER=15709588632@139.com
SMTP_PASSWORD=你的授权码

# 预警接收邮箱
ALERT_RECEIVER=15709588632@139.com

获取139邮箱授权码：
1. 登录 https://mail.10086.cn
2. 设置 → 邮箱协议 → POP3/SMTP服务
3. 开启SMTP服务
4. 生成授权码
""")


if __name__ == "__main__":
    alert = EmailAlert()
    if not alert.password:
        print_config_guide()
    else:
        # 测试发送
        alert.send_alert("测试邮件", "<h1>测试</h1><p>邮件预警功能配置成功！</p>")
