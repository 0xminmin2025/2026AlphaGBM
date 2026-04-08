"""
飞书自定义机器人 Webhook 推送服务

每日推送运营数据报告：用户数据、付费数据、收入数据
"""

import os
import logging
from datetime import datetime, date
from sqlalchemy import func

import requests

from ..models import db, User, Subscription, Transaction

logger = logging.getLogger(__name__)

FEISHU_WEBHOOK_URL = os.environ.get('FEISHU_WEBHOOK_URL', '')


def get_daily_stats():
    """查询今日及累计运营数据"""
    today = date.today()
    today_start = datetime(today.year, today.month, today.day, 0, 0, 0)
    today_end = datetime(today.year, today.month, today.day, 23, 59, 59)

    # 用户数据
    new_users_today = User.query.filter(
        User.created_at >= today_start,
        User.created_at <= today_end,
    ).count()
    total_users = User.query.count()

    # 付费数据
    new_paid_today = Subscription.query.filter(
        Subscription.created_at >= today_start,
        Subscription.created_at <= today_end,
        Subscription.status == 'active',
    ).count()
    total_paid_users = db.session.query(
        func.count(func.distinct(Subscription.user_id))
    ).filter(Subscription.status == 'active').scalar() or 0

    # 收入数据（统计所有成功交易，amount 存储为分，除以 100 转为美元）
    today_revenue_cents = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.status == 'succeeded',
        Transaction.created_at >= today_start,
        Transaction.created_at <= today_end,
    ).scalar()

    total_revenue_cents = db.session.query(
        func.coalesce(func.sum(Transaction.amount), 0)
    ).filter(
        Transaction.status == 'succeeded',
    ).scalar()

    return {
        'date': today.isoformat(),
        'new_users_today': new_users_today,
        'total_users': total_users,
        'new_paid_today': new_paid_today,
        'total_paid_users': total_paid_users,
        'today_revenue': today_revenue_cents / 100,
        'total_revenue': total_revenue_cents / 100,
    }


def build_card_message(stats):
    """构建飞书交互式卡片消息"""
    return {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": "📊 AlphaGBM 每日运营报告",
                },
                "template": "blue",
            },
            "elements": [
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": f"📅 **日期：{stats['date']}**",
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "👥 **用户数据**\n"
                            f"今日新注册：**{stats['new_users_today']}**\n"
                            f"累计用户：**{stats['total_users']:,}**"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "💰 **付费数据**\n"
                            f"今日新付费：**{stats['new_paid_today']}**\n"
                            f"累计付费用户：**{stats['total_paid_users']:,}**"
                        ),
                    },
                },
                {"tag": "hr"},
                {
                    "tag": "div",
                    "text": {
                        "tag": "lark_md",
                        "content": (
                            "💵 **收入数据**\n"
                            f"今日收入：**${stats['today_revenue']:,.2f}**\n"
                            f"累计总收入：**${stats['total_revenue']:,.2f}**"
                        ),
                    },
                },
            ],
        },
    }


def send_daily_report():
    """查询运营数据并推送到飞书群"""
    webhook_url = FEISHU_WEBHOOK_URL or os.environ.get('FEISHU_WEBHOOK_URL', '')
    if not webhook_url:
        logger.warning("FEISHU_WEBHOOK_URL not configured, skipping report")
        return False

    try:
        stats = get_daily_stats()
        payload = build_card_message(stats)

        resp = requests.post(webhook_url, json=payload, timeout=10)
        resp.raise_for_status()

        result = resp.json()
        if result.get('code') == 0:
            logger.info(f"Feishu daily report sent successfully: {stats}")
            return True
        else:
            logger.error(f"Feishu API error: {result}")
            return False

    except Exception as e:
        logger.error(f"Failed to send Feishu daily report: {e}")
        return False
