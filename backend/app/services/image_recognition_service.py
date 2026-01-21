"""
期权截图识别服务
使用 Google Gemini Vision API 识别期权截图中的参数
"""

import logging
import base64
import json
import re
from typing import Dict, Any, Optional
import requests
from ..config import Config

logger = logging.getLogger(__name__)


class ImageRecognitionService:
    """期权截图识别服务"""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent"

    # 识别提示词
    RECOGNITION_PROMPT = """请仔细分析这张期权交易截图，提取以下信息：

1. 股票代码 (symbol) - 如 AAPL, NVDA, TSLA 等
2. 期权类型 (option_type) - CALL（看涨）或 PUT（看跌）
3. 执行价 (strike) - 期权的行权价格
4. 到期日 (expiry_date) - 格式为 YYYY-MM-DD
5. 期权价格 (option_price) - 当前期权的价格（可以是 bid/ask 的中间价或最新成交价）
6. 隐含波动率 (implied_volatility) - 如果图中有显示（可选）

请以 JSON 格式返回结果，例如：
{
    "symbol": "AAPL",
    "option_type": "CALL",
    "strike": 230,
    "expiry_date": "2025-02-21",
    "option_price": 5.50,
    "implied_volatility": 0.28,
    "confidence": "high",
    "notes": "识别备注"
}

注意事项：
- 如果无法识别某个字段，设为 null
- confidence 可以是 "high", "medium", "low"
- 在 notes 中说明任何不确定的地方
- 隐含波动率如果是百分比形式（如28%），请转换为小数（0.28）
- 如果是期权链截图，请识别用户可能感兴趣的那个期权（通常是高亮的或光标所在位置）

只返回 JSON，不要其他文字。"""

    @classmethod
    def recognize_option_from_image(cls, image_data: bytes, mime_type: str = "image/png") -> Dict[str, Any]:
        """
        从图片识别期权参数

        Args:
            image_data: 图片二进制数据
            mime_type: 图片 MIME 类型

        Returns:
            识别结果字典
        """
        api_key = Config.GOOGLE_API_KEY
        if not api_key:
            return {
                'success': False,
                'error': 'Google API Key not configured'
            }

        try:
            # 将图片转换为 base64
            image_base64 = base64.b64encode(image_data).decode('utf-8')

            # 构建请求
            payload = {
                "contents": [{
                    "parts": [
                        {"text": cls.RECOGNITION_PROMPT},
                        {
                            "inline_data": {
                                "mime_type": mime_type,
                                "data": image_base64
                            }
                        }
                    ]
                }],
                "generationConfig": {
                    "temperature": 0.1,
                    "topK": 1,
                    "topP": 1,
                    "maxOutputTokens": 1024,
                }
            }

            # 发送请求
            response = requests.post(
                f"{cls.GEMINI_API_URL}?key={api_key}",
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=30
            )

            if response.status_code != 200:
                logger.error(f"Gemini API error: {response.status_code} - {response.text}")
                return {
                    'success': False,
                    'error': f'AI 识别服务暂时不可用 (HTTP {response.status_code})'
                }

            result = response.json()

            # 解析响应
            if 'candidates' not in result or not result['candidates']:
                return {
                    'success': False,
                    'error': '无法识别图片内容'
                }

            text_response = result['candidates'][0]['content']['parts'][0]['text']

            # 清理响应文本，提取 JSON
            json_text = cls._extract_json(text_response)
            if not json_text:
                logger.error(f"Failed to extract JSON from response: {text_response}")
                return {
                    'success': False,
                    'error': '无法解析识别结果'
                }

            # 解析 JSON
            parsed = json.loads(json_text)

            # 验证必要字段
            required_fields = ['symbol', 'option_type', 'strike', 'expiry_date', 'option_price']
            missing_fields = [f for f in required_fields if not parsed.get(f)]

            if missing_fields:
                return {
                    'success': False,
                    'error': f'无法识别以下信息: {", ".join(missing_fields)}',
                    'partial_result': parsed
                }

            # 标准化数据
            recognized_data = {
                'symbol': str(parsed['symbol']).upper(),
                'option_type': str(parsed['option_type']).upper(),
                'strike': float(parsed['strike']),
                'expiry_date': str(parsed['expiry_date']),
                'option_price': float(parsed['option_price']),
                'implied_volatility': float(parsed['implied_volatility']) if parsed.get('implied_volatility') else None,
                'confidence': parsed.get('confidence', 'medium'),
                'notes': parsed.get('notes', '')
            }

            # 验证期权类型
            if recognized_data['option_type'] not in ['CALL', 'PUT']:
                # 尝试修正
                if '看涨' in str(parsed.get('option_type', '')):
                    recognized_data['option_type'] = 'CALL'
                elif '看跌' in str(parsed.get('option_type', '')):
                    recognized_data['option_type'] = 'PUT'
                else:
                    return {
                        'success': False,
                        'error': f'无法识别期权类型: {parsed.get("option_type")}'
                    }

            return {
                'success': True,
                'data': recognized_data
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON parse error: {e}")
            return {
                'success': False,
                'error': '识别结果格式错误'
            }
        except requests.RequestException as e:
            logger.error(f"Request error: {e}")
            return {
                'success': False,
                'error': 'AI 服务请求失败，请稍后重试'
            }
        except Exception as e:
            logger.error(f"Recognition error: {e}")
            return {
                'success': False,
                'error': f'识别过程出错: {str(e)}'
            }

    @staticmethod
    def _extract_json(text: str) -> Optional[str]:
        """从文本中提取 JSON 字符串"""
        # 尝试直接解析
        text = text.strip()
        if text.startswith('{') and text.endswith('}'):
            return text

        # 尝试找到 JSON 块
        json_match = re.search(r'\{[^{}]*\}', text, re.DOTALL)
        if json_match:
            return json_match.group()

        # 尝试找到 markdown 代码块中的 JSON
        code_match = re.search(r'```(?:json)?\s*(\{[^`]*\})\s*```', text, re.DOTALL)
        if code_match:
            return code_match.group(1)

        return None


# 单例实例
image_recognition_service = ImageRecognitionService()
