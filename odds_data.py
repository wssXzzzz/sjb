# -*- coding: utf-8 -*-
"""
赔率数据层：The Odds API → 去水(vig removal) → 跨家均值 → 隐含 1X2 概率。

数据源：The Odds API（https://the-odds-api.com/）
- 免费 500 请求/月；返回多家博彩公司十进制 1X2 三路赔率，JSON
- key 走环境变量 ODDS_API_KEY（.gitignore 已忽略 .env）
- 无 key/超额/失败 → 返回 {} → predictor 全程回退纯模型（与现状完全一致）

设计（ODDS_PLAN.md §1 §2 §6）：
- 一次请求返回所有已开盘 WC 比赛 → 配 2h 长缓存控配额（每天~12次 < 500）
- 去水：p_i = (1/o_i) / Σ(1/o_j)
- 多家先各自去水再跨家取均值，记 books_n
- 输出 {(api_home,api_away): {pH(=api_home胜),pD,pA(=api_away胜),books_n,updated}}
"""
import json
import os
import ssl
import time
import urllib.request
import urllib.error

import wc_data as W

# The Odds API 配置
SPORT_KEY = "soccer_fifa_world_cup"
REGIONS = "eu,uk"          # 欧洲市场博彩公司多、赔率 sharp
MARKETS = "h2h"            # 1X2 三路（含平局）
ODDS_FORMAT = "decimal"
API_BASE = "https://api.the-odds-api.com/v4/sports"
CACHE_TTL = 7200           # 2 小时（控配额：每天~12次 < 500/月）

_cache = {"data": None, "ts": 0, "source": "online"}

# The Odds API 队名 → 内部英文键映射
# The Odds API 用英文国家队全称，内部用 FIFA 短称
ODDSAPI_TO_EN = {
    "Mexico": "Mexico", "South Korea": "South Korea", "Czech Republic": "Czech Republic",
    "South Africa": "South Africa", "Canada": "Canada", "Switzerland": "Switzerland",
    "Qatar": "Qatar", "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Brazil": "Brazil", "Morocco": "Morocco", "Scotland": "Scotland", "Haiti": "Haiti",
    "United States": "United States", "USA": "United States", "Australia": "Australia",
    "Turkey": "Turkey", "Paraguay": "Paraguay", "Germany": "Germany",
    "Ecuador": "Ecuador", "Ivory Coast": "Ivory Coast", "Cote d'Ivoire": "Ivory Coast",
    "Curacao": "Curacao", "Curaçao": "Curacao",
    "Netherlands": "Netherlands", "Japan": "Japan", "Sweden": "Sweden", "Tunisia": "Tunisia",
    "Belgium": "Belgium", "Iran": "Iran", "Egypt": "Egypt", "New Zealand": "New Zealand",
    "Spain": "Spain", "Uruguay": "Uruguay", "Saudi Arabia": "Saudi Arabia",
    "Cape Verde": "Cape Verde", "Cabo Verde": "Cape Verde",
    "France": "France", "Norway": "Norway", "Senegal": "Senegal", "Iraq": "Iraq",
    "Argentina": "Argentina", "Algeria": "Algeria", "Austria": "Austria", "Jordan": "Jordan",
    "Portugal": "Portugal", "Colombia": "Colombia", "Uzbekistan": "Uzbekistan",
    "DR Congo": "DR Congo", "Democratic Republic of the Congo": "DR Congo",
    "Congo DR": "DR Congo",
    "England": "England", "Croatia": "Croatia", "Panama": "Panama", "Ghana": "Ghana",
}


def implied_probs(odds_h, odds_d, odds_a):
    """十进制赔率 (主胜,平,客胜) → 去水归一隐含概率 + overround。
    返回 (pH, pD, pA, overround)；赔率无效返回 None"""
    try:
        h, d, a = float(odds_h), float(odds_d), float(odds_a)
    except (TypeError, ValueError):
        return None
    if min(h, d, a) <= 1.0:
        return None
    rh, rd, ra = 1 / h, 1 / d, 1 / a
    over = rh + rd + ra          # overround，通常 1.05~1.12
    return (rh / over, rd / over, ra / over, over)


def fetch_odds(force=False):
    """获取赔率 → {frozenset(home,away): {pH,pD,pA,books_n,updated}}。
    自动降级：API → 空 dict。无 key 返回 {}（predictor 回退纯模型）。"""
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    key = os.environ.get("ODDS_API_KEY")
    if not key:
        print("[odds_data] 无 ODDS_API_KEY，赔率功能关闭，回退纯模型")
        _cache.update({"data": {}, "ts": now, "source": "no_key"})
        return {}

    raw = _fetch_api(key)
    if not raw:
        _cache.update({"data": {}, "ts": now, "source": "failed"})
        return {}

    data = _parse_api(raw)
    _cache.update({"data": data, "ts": now, "source": "online"})
    return data


def _fetch_api(key):
    """请求 The Odds API；失败返回 None"""
    url = (f"{API_BASE}/{SPORT_KEY}/odds/?regions={REGIONS}&markets={MARKETS}"
           f"&oddsFormat={ODDS_FORMAT}&apiKey={key}")
    try:
        ctx = _ssl_ctx()
        req = urllib.request.Request(url, headers={
            "User-Agent": "wc2026-odds/1.0 (educational)",
            "Accept": "application/json",
        })
        with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8", errors="replace"))
    except (urllib.error.URLError, urllib.error.HTTPError, ssl.SSLError,
            json.JSONDecodeError, TimeoutError, OSError) as e:
        print(f"[odds_data] API 抓取失败: {type(e).__name__}: {str(e)[:100]}")
        return None


def _parse_api(raw):
    """解析 The Odds API 响应 → {frozenset: {pH,pD,pA,books_n,updated}}。
    响应结构：list of matches, 每个含 home_team/away_team/bookmakers[]/markets[]/outcomes[]"""
    result = {}
    for m in raw:
        home_en = ODDSAPI_TO_EN.get(m.get("home_team"))
        away_en = ODDSAPI_TO_EN.get(m.get("away_team"))
        if not home_en or not away_en:
            continue
        # 收集各 bookmaker 的 h2h 三路赔率
        book_probs = []  # [(pH,pD,pA),...]
        for book in (m.get("bookmakers") or []):
            for mk in (book.get("markets") or []):
                if mk.get("key") != "h2h":
                    continue
                outcomes = {o.get("name"): o.get("price") for o in (mk.get("outcomes") or [])}
                # outcomes 含 home_team/draw/away_team 三个 key 的 price
                oh = outcomes.get(m.get("home_team"))
                od = outcomes.get("Draw")
                oa = outcomes.get(m.get("away_team"))
                if not (oh and od and oa):
                    continue
                ip = implied_probs(oh, od, oa)
                if ip:
                    book_probs.append((ip[0], ip[1], ip[2]))
        if not book_probs:
            continue
        # 跨家取均值（已各自去水）
        n = len(book_probs)
        pH = sum(b[0] for b in book_probs) / n
        pD = sum(b[1] for b in book_probs) / n
        pA = sum(b[2] for b in book_probs) / n
        # 归一（均值后可能略偏 1，再归一次）
        s = pH + pD + pA
        # 用有序 key 存储：(api_home, api_away)；pH=api_home胜率，pA=api_away胜率
        result[(home_en, away_en)] = {
            "pH": pH / s, "pD": pD / s, "pA": pA / s,
            "books_n": n,
            "updated": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
        }
    return result


def odds_for(home, away, odds):
    """查 home vs away 的市场隐含 1X2（方向感知）。
    返回 {pH(=home胜),pD,pA(=away胜),books_n} 或 None。
    内部按 (api_home,api_away) 有序存储，查询时对齐方向。"""
    if not odds:
        return None
    # 正向：(home,away) 即 api 存储顺序
    rec = odds.get((home, away))
    if rec:
        return rec
    # 反向：(away,home) → 交换 pH/pA
    rec = odds.get((away, home))
    if rec:
        return {"pH": rec["pA"], "pD": rec["pD"], "pA": rec["pH"],
                "books_n": rec["books_n"], "updated": rec.get("updated")}
    return None


def _ssl_ctx():
    """SSL 降级（certifi → 系统 → 跳过）"""
    try:
        import certifi
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(certifi.where())
        return ctx
    except Exception:
        pass
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


if __name__ == "__main__":
    print("=== 赔率数据测试 ===")
    o = fetch_odds(force=True)
    print(f"来源: {_cache['source']} | {len(o)} 场赔率")
    print()
    if o:
        for key, rec in list(o.items())[:5]:
            teams = list(key)
            print(f"  {teams[0]} vs {teams[1]}: 主{rec['pH']*100:.0f}% 平{rec['pD']*100:.0f}% "
                  f"客{rec['pA']*100:.0f}% ({rec['books_n']}家)")
    else:
        print("无数据（无 key 或抓取失败）。设置 ODDS_API_KEY 环境变量后重试。")
    print()
    print("=== 去水计算验证 ===")
    ip = implied_probs(1.85, 3.40, 4.20)
    print(f"赔率 1.85/3.40/4.20 → 主{ip[0]*100:.1f}% 平{ip[1]*100:.1f}% 客{ip[2]*100:.1f}% "
          f"(overround {(ip[3]-1)*100:.1f}%)")
