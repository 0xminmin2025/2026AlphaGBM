"""
波动率微笑 & 3D 曲面分析模块

功能：
- 2D 波动率微笑：单个到期日的 strike vs IV 曲线
- 3D 波动率曲面：strike × expiry × IV 网格
- 偏斜指标（25-Delta Skew, Put-Call Ratio）
- ATM 快照
- IV Rank / IV Percentile
- 历史 IV 趋势
"""

import logging
import math
from dataclasses import dataclass, asdict, field
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import numpy as np

logger = logging.getLogger(__name__)


@dataclass
class VolSmileData:
    """2D 波动率微笑数据"""
    symbol: str
    expiry: str
    underlying_price: float
    atm_strike: float

    # 微笑曲线数据点
    strikes: List[float] = field(default_factory=list)
    call_ivs: List[Optional[float]] = field(default_factory=list)
    put_ivs: List[Optional[float]] = field(default_factory=list)
    call_volumes: List[int] = field(default_factory=list)
    put_volumes: List[int] = field(default_factory=list)
    call_oi: List[int] = field(default_factory=list)
    put_oi: List[int] = field(default_factory=list)
    call_deltas: List[Optional[float]] = field(default_factory=list)
    put_deltas: List[Optional[float]] = field(default_factory=list)

    # 偏斜指标
    skew_metrics: Dict[str, Any] = field(default_factory=dict)

    # ATM 快照
    atm_snapshot: Dict[str, Any] = field(default_factory=dict)

    # IV Rank & Percentile
    iv_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class VolSurfaceData:
    """3D 波动率曲面数据"""
    symbol: str
    underlying_price: float

    # 网格数据
    strikes: List[float] = field(default_factory=list)      # X 轴
    expiries: List[str] = field(default_factory=list)        # Y 轴（日期标签）
    expiry_days: List[int] = field(default_factory=list)     # Y 轴（天数）
    iv_grid: List[List[Optional[float]]] = field(default_factory=list)  # Z 轴 [expiry][strike]

    # 曲面统计
    surface_stats: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class VolatilitySurfaceAnalyzer:
    """波动率曲面分析器"""

    def __init__(self):
        pass

    # ─────────────────────────────────────
    # 2D 波动率微笑
    # ─────────────────────────────────────

    def build_vol_smile(
        self,
        symbol: str,
        underlying_price: float,
        calls_data: List[Dict[str, Any]],
        puts_data: List[Dict[str, Any]],
        expiry: str,
        historical_ivs: Optional[List[Dict[str, Any]]] = None
    ) -> VolSmileData:
        """
        构建 2D 波动率微笑

        Args:
            symbol: 标的代码
            underlying_price: 标的价格
            calls_data: Call 链数据 [{'strike': 150, 'impliedVolatility': 0.25, ...}]
            puts_data: Put 链数据
            expiry: 到期日 YYYY-MM-DD
            historical_ivs: 历史 IV 数据（可选）

        Returns:
            VolSmileData
        """
        # 合并 strikes
        call_map = {c['strike']: c for c in calls_data if c.get('strike')}
        put_map = {p['strike']: p for p in puts_data if p.get('strike')}

        all_strikes = sorted(set(list(call_map.keys()) + list(put_map.keys())))

        # 找 ATM
        atm_strike = min(all_strikes, key=lambda s: abs(s - underlying_price))

        # 过滤有效范围（ATM ± 30%）
        lower = underlying_price * 0.7
        upper = underlying_price * 1.3
        filtered_strikes = [s for s in all_strikes if lower <= s <= upper]

        smile = VolSmileData(
            symbol=symbol,
            expiry=expiry,
            underlying_price=underlying_price,
            atm_strike=atm_strike,
        )

        for strike in filtered_strikes:
            smile.strikes.append(strike)

            call = call_map.get(strike, {})
            put = put_map.get(strike, {})

            call_iv = self._extract_iv(call)
            put_iv = self._extract_iv(put)

            smile.call_ivs.append(call_iv)
            smile.put_ivs.append(put_iv)
            smile.call_volumes.append(int(call.get('volume', 0) or 0))
            smile.put_volumes.append(int(put.get('volume', 0) or 0))
            smile.call_oi.append(int(call.get('openInterest', call.get('open_interest', 0)) or 0))
            smile.put_oi.append(int(put.get('openInterest', put.get('open_interest', 0)) or 0))

            # Delta
            smile.call_deltas.append(self._safe_float(call.get('delta')))
            smile.put_deltas.append(self._safe_float(put.get('delta')))

        # 计算偏斜指标
        smile.skew_metrics = self._calculate_skew_metrics(
            filtered_strikes, smile.call_ivs, smile.put_ivs,
            smile.call_deltas, smile.put_deltas, underlying_price
        )

        # ATM 快照
        smile.atm_snapshot = self._build_atm_snapshot(
            atm_strike, call_map, put_map
        )

        # IV 统计
        smile.iv_stats = self._calculate_iv_stats(
            smile.call_ivs, smile.put_ivs, historical_ivs
        )

        return smile

    # ─────────────────────────────────────
    # 3D 波动率曲面
    # ─────────────────────────────────────

    def build_vol_surface(
        self,
        symbol: str,
        underlying_price: float,
        chain_by_expiry: Dict[str, Dict[str, List[Dict[str, Any]]]],
    ) -> VolSurfaceData:
        """
        构建 3D 波动率曲面

        Args:
            symbol: 标的代码
            underlying_price: 标的价格
            chain_by_expiry: {
                '2024-12-20': {'calls': [...], 'puts': [...]},
                '2025-01-17': {'calls': [...], 'puts': [...]},
                ...
            }

        Returns:
            VolSurfaceData
        """
        today = datetime.now().date()

        # 收集所有 strikes 和 expiries
        all_strikes_set = set()
        expiry_entries = []

        for expiry_str, data in sorted(chain_by_expiry.items()):
            try:
                exp_date = datetime.strptime(expiry_str, '%Y-%m-%d').date()
            except ValueError:
                continue

            days = (exp_date - today).days
            if days <= 0:
                continue

            calls = data.get('calls', [])
            puts = data.get('puts', [])

            # 合并 IV 数据
            iv_by_strike = {}
            for c in calls:
                s = c.get('strike')
                iv = self._extract_iv(c)
                if s and iv:
                    iv_by_strike[s] = iv

            for p in puts:
                s = p.get('strike')
                iv = self._extract_iv(p)
                if s and iv and s not in iv_by_strike:
                    iv_by_strike[s] = iv

            if iv_by_strike:
                all_strikes_set.update(iv_by_strike.keys())
                expiry_entries.append({
                    'expiry': expiry_str,
                    'days': days,
                    'iv_map': iv_by_strike
                })

        if not expiry_entries:
            return VolSurfaceData(symbol=symbol, underlying_price=underlying_price)

        # 过滤 strikes 范围
        lower = underlying_price * 0.75
        upper = underlying_price * 1.25
        all_strikes = sorted([s for s in all_strikes_set if lower <= s <= upper])

        # 构建网格
        surface = VolSurfaceData(
            symbol=symbol,
            underlying_price=underlying_price,
            strikes=all_strikes,
        )

        all_ivs = []
        atm_ivs_by_expiry = []

        for entry in expiry_entries:
            surface.expiries.append(entry['expiry'])
            surface.expiry_days.append(entry['days'])

            row = []
            for strike in all_strikes:
                iv = entry['iv_map'].get(strike)
                row.append(round(iv * 100, 2) if iv else None)
                if iv:
                    all_ivs.append(iv)

            surface.iv_grid.append(row)

            # ATM IV for this expiry
            atm_strike = min(all_strikes, key=lambda s: abs(s - underlying_price))
            atm_iv = entry['iv_map'].get(atm_strike)
            if atm_iv:
                atm_ivs_by_expiry.append({
                    'expiry': entry['expiry'],
                    'days': entry['days'],
                    'iv': round(atm_iv * 100, 2)
                })

        # 曲面统计
        if all_ivs:
            all_ivs_pct = [iv * 100 for iv in all_ivs]
            surface.surface_stats = {
                'atm_iv_30d': self._find_atm_iv_near_days(atm_ivs_by_expiry, 30),
                'iv_range': {
                    'min': round(min(all_ivs_pct), 2),
                    'max': round(max(all_ivs_pct), 2),
                    'mean': round(float(np.mean(all_ivs_pct)), 2),
                },
                'term_structure': self._classify_term_structure(atm_ivs_by_expiry),
                'atm_by_expiry': atm_ivs_by_expiry,
            }

            # 25-Delta Skew（使用最近到期）
            if expiry_entries:
                nearest = expiry_entries[0]
                skew = self._calc_25d_skew_from_map(
                    nearest['iv_map'], all_strikes, underlying_price
                )
                if skew is not None:
                    surface.surface_stats['skew_25d'] = round(skew * 100, 2)

        return surface

    # ─────────────────────────────────────
    # 辅助方法
    # ─────────────────────────────────────

    def _extract_iv(self, option_data: Dict[str, Any]) -> Optional[float]:
        """从期权数据中提取 IV"""
        for key in ['impliedVolatility', 'iv', 'implied_volatility', 'implied_vol']:
            val = option_data.get(key)
            if val is not None:
                try:
                    v = float(val)
                    # 如果 IV > 10，可能是百分比格式（如 25 而不是 0.25）
                    if v > 10:
                        v = v / 100
                    if 0.001 < v < 5.0:
                        return v
                except (ValueError, TypeError):
                    pass
        return None

    def _safe_float(self, val: Any) -> Optional[float]:
        """安全转换为 float"""
        if val is None:
            return None
        try:
            return round(float(val), 4)
        except (ValueError, TypeError):
            return None

    def _calculate_skew_metrics(
        self,
        strikes: List[float],
        call_ivs: List[Optional[float]],
        put_ivs: List[Optional[float]],
        call_deltas: List[Optional[float]],
        put_deltas: List[Optional[float]],
        spot: float
    ) -> Dict[str, Any]:
        """计算偏斜指标"""
        metrics = {}

        # 25-Delta Put Skew
        # 找到最接近 25 Delta 的 Put IV 和 ATM IV
        valid_puts = [(s, iv, d) for s, iv, d in zip(strikes, put_ivs, put_deltas)
                      if iv is not None and d is not None]
        valid_calls = [(s, iv, d) for s, iv, d in zip(strikes, call_ivs, call_deltas)
                       if iv is not None and d is not None]

        atm_call_iv = None
        atm_put_iv = None
        d25_put_iv = None

        # ATM IV (delta 最接近 0.5)
        if valid_calls:
            atm_call = min(valid_calls, key=lambda x: abs((x[2] or 0) - 0.5))
            atm_call_iv = atm_call[1]

        if valid_puts:
            atm_put = min(valid_puts, key=lambda x: abs((x[2] or 0) + 0.5))
            atm_put_iv = atm_put[1]

            # 25-Delta Put
            d25 = min(valid_puts, key=lambda x: abs((x[2] or 0) + 0.25))
            d25_put_iv = d25[1]

        if d25_put_iv and atm_call_iv:
            metrics['put_skew_25d'] = round((d25_put_iv - atm_call_iv) * 100, 2)

        # Put-Call IV Ratio
        avg_call_iv = np.mean([iv for iv in call_ivs if iv]) if any(iv for iv in call_ivs) else None
        avg_put_iv = np.mean([iv for iv in put_ivs if iv]) if any(iv for iv in put_ivs) else None

        if avg_call_iv and avg_put_iv and avg_call_iv > 0:
            metrics['put_call_iv_ratio'] = round(float(avg_put_iv / avg_call_iv), 2)

        # Skew percentile（简化版：用当前 skew 值 / 历史范围）
        if 'put_skew_25d' in metrics:
            # 经验值：正常偏斜范围约 2-8%
            skew_val = abs(metrics['put_skew_25d'])
            percentile = min(100, max(0, (skew_val / 15) * 100))
            metrics['skew_percentile_1y'] = round(percentile)

        return metrics

    def _build_atm_snapshot(
        self,
        atm_strike: float,
        call_map: Dict[float, Dict],
        put_map: Dict[float, Dict]
    ) -> Dict[str, Any]:
        """构建 ATM 快照"""
        snapshot = {'strike': atm_strike}

        call = call_map.get(atm_strike, {})
        put = put_map.get(atm_strike, {})

        call_iv = self._extract_iv(call)
        put_iv = self._extract_iv(put)

        if call_iv:
            snapshot['atm_iv'] = round(call_iv * 100, 2)

        # Call/Put 价格
        call_mid = self._calc_mid(call)
        put_mid = self._calc_mid(put)

        if call_mid:
            snapshot['call_price'] = round(call_mid, 2)
        if put_mid:
            snapshot['put_price'] = round(put_mid, 2)
        if call_mid and put_mid:
            snapshot['straddle_price'] = round(call_mid + put_mid, 2)

        return snapshot

    def _calc_mid(self, option: Dict) -> Optional[float]:
        """计算中间价"""
        bid = self._safe_float(option.get('bid', option.get('bid_price')))
        ask = self._safe_float(option.get('ask', option.get('ask_price')))
        if bid is not None and ask is not None and bid > 0 and ask > 0:
            return (bid + ask) / 2
        last = self._safe_float(option.get('lastPrice', option.get('last', option.get('latest_price'))))
        return last

    def _calculate_iv_stats(
        self,
        call_ivs: List[Optional[float]],
        put_ivs: List[Optional[float]],
        historical_ivs: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """计算 IV Rank 和 Percentile"""
        stats = {}

        # 当前 ATM IV（用 call 和 put 的中间 IV 中位数近似）
        valid_ivs = [iv for iv in (call_ivs + put_ivs) if iv is not None]
        if not valid_ivs:
            return stats

        current_iv = float(np.median(valid_ivs))
        stats['current_iv'] = round(current_iv * 100, 2)

        if historical_ivs:
            hist_vals = [h['iv'] for h in historical_ivs if 'iv' in h]
            if hist_vals:
                iv_min = min(hist_vals)
                iv_max = max(hist_vals)

                # IV Rank
                if iv_max > iv_min:
                    iv_rank = (current_iv - iv_min) / (iv_max - iv_min) * 100
                    stats['iv_rank'] = round(iv_rank, 1)

                # IV Percentile
                below = sum(1 for v in hist_vals if v <= current_iv)
                stats['iv_percentile'] = round(below / len(hist_vals) * 100, 1)

                stats['iv_high_52w'] = round(iv_max * 100, 2)
                stats['iv_low_52w'] = round(iv_min * 100, 2)

        return stats

    def _find_atm_iv_near_days(
        self, atm_ivs: List[Dict], target_days: int
    ) -> Optional[float]:
        """找最接近目标天数的 ATM IV"""
        if not atm_ivs:
            return None
        nearest = min(atm_ivs, key=lambda x: abs(x['days'] - target_days))
        return nearest['iv']

    def _classify_term_structure(self, atm_ivs: List[Dict]) -> str:
        """分类期限结构：Contango / Backwardation / Flat"""
        if len(atm_ivs) < 2:
            return 'insufficient_data'

        sorted_ivs = sorted(atm_ivs, key=lambda x: x['days'])
        short_iv = sorted_ivs[0]['iv']
        long_iv = sorted_ivs[-1]['iv']

        diff_pct = (long_iv - short_iv) / short_iv * 100 if short_iv > 0 else 0

        if diff_pct > 5:
            return 'contango'       # 远月 IV > 近月（正常）
        elif diff_pct < -5:
            return 'backwardation'  # 近月 IV > 远月（恐慌/事件驱动）
        else:
            return 'flat'

    def _calc_25d_skew_from_map(
        self,
        iv_map: Dict[float, float],
        strikes: List[float],
        spot: float
    ) -> Optional[float]:
        """从 IV map 计算 25-Delta Skew（近似）"""
        if not iv_map or not strikes:
            return None

        # 近似：25-delta put ≈ spot * 0.93, ATM ≈ spot
        target_25d = spot * 0.93
        atm = spot

        nearest_25d = min(strikes, key=lambda s: abs(s - target_25d))
        nearest_atm = min(strikes, key=lambda s: abs(s - atm))

        iv_25d = iv_map.get(nearest_25d)
        iv_atm = iv_map.get(nearest_atm)

        if iv_25d and iv_atm:
            return iv_25d - iv_atm
        return None
