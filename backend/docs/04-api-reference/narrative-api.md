# Narrative API -- 叙事雷达接口

**Blueprint 前缀**: `/api/narrative` | **源文件**: `app/api/narrative_routes.py` | **Auth**: 全部无需认证

叙事雷达提供基于投资叙事的股票发现功能。支持预设叙事和自定义概念分析。

---

## 1. GET /api/narrative/presets

获取所有预设叙事列表，按类型分组。

**Response:**
```json
{
  "person": [
    {"key": "buffett", "type": "person", "name": "巴菲特持仓", "description": "..."}
  ],
  "institution": [
    {"key": "ark_innovation", "type": "institution", "name": "ARK 创新基金", "description": "..."}
  ],
  "theme": [
    {"key": "ai_infrastructure", "type": "theme", "name": "AI 基础设施", "description": "..."}
  ]
}
```

| 分组类型 | 说明 |
|---------|------|
| `person` | 知名投资人相关叙事 |
| `institution` | 机构投资主题 |
| `theme` | 行业/概念主题叙事 |

---

## 2. POST /api/narrative/analyze

分析叙事关联的股票和期权策略。

**Request Body:**
```json
{
  "concept": "人工智能芯片",
  "narrative_key": null,
  "market": "US",
  "lang": "zh"
}
```

| 字段 | 类型 | 必填 | 默认 | 说明 |
|------|------|------|------|------|
| `concept` | string | 二选一 | `""` | 自定义概念文本 |
| `narrative_key` | string | 二选一 | `null` | 预设叙事 key |
| `market` | string | 否 | `"US"` | `US`/`HK`/`CN` |
| `lang` | string | 否 | `"zh"` | `zh`(中文)/`en`(英文) |

`concept` 和 `narrative_key` 至少提供一个。

**Response:**
```json
{
  "narrative": "人工智能芯片",
  "stocks": [
    {"ticker": "NVDA", "name": "NVIDIA", "relevance": 0.95, "reason": "全球最大AI芯片供应商"}
  ],
  "options_strategies": [...]
}
```

**Error (400):** `{"error": "Concept or narrative_key is required"}`
