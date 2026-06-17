# -*- coding: utf-8 -*-
"""
近期战绩数据层：从 OpenLigaDB 大赛（欧洲杯/美洲杯/欧国联/世界杯）抓取每队近期战绩，
计算胜率、场均进球失球，并派生历史交锋（h2h）。
缓存 1 小时：语料里欧洲杯/美洲杯/欧国联 2024 是静态历史，世界杯部分对 h2h 几乎无影响
（h2h 需 sample_n≥3，两队在 WC 只碰一次触发不了），故无需 5 分钟高频重抓 4 个端点。
诚实标注：友谊赛/小赛事不在源里，CAF/AFC 队可能样本不足。
"""
import json
import time
import urllib.request
import urllib.error

import wc_data as W

# 大赛端点（必须带 season 才能拿全；裸 URL 只返回当前轮）
TOURNAMENTS = [
    ("em2024/2024", "欧洲杯"),
    ("CA2024/2024", "美洲杯"),
    ("unl2024/2024", "欧国联"),
    ("wm2026/2026", "世界杯"),
]
API_BASE = "https://api.openligadb.de/getmatchdata/"
CACHE_TTL = 3600  # 1 小时（语料基本静态，详见模块说明）

_cache = {"data": None, "ts": 0}

# 垃圾占位队（OpenLigaDB 测试数据）
JUNK_TEAMS = {"SV Großefehn"}


def _normalize(de_name):
    """德名 → 英文显示名（优先 WC 队，再查非 WC 对手表）"""
    if de_name in JUNK_TEAMS:
        return None
    en = W.DE_TO_EN.get(de_name)
    if en:
        return en
    return W.DE_TO_EN_OPP.get(de_name)  # 非 WC 对手，可能 None


def _parse_score(match):
    """从 API 比赛取全场比分；未完赛返回 None"""
    if not match.get("matchIsFinished"):
        return None
    for r in (match.get("matchResults") or []):
        if r.get("resultOrderID") == 2:  # Endergebnis
            return r.get("pointsTeam1"), r.get("pointsTeam2")
    rs = match.get("matchResults") or []
    if rs:
        return rs[-1].get("pointsTeam1"), rs[-1].get("pointsTeam2")
    return None


def _fetch_tournament(shortcut):
    """抓单个大赛全部比赛；失败返回 []"""
    import ssl
    url = API_BASE + shortcut
    # SSL 降级（复用 squad_data 思路）
    for ctx in (_strict_ctx(), _unverified_ctx()):
        try:
            req = urllib.request.Request(url, headers={
                "Accept": "application/json",
                "User-Agent": "wc2026-form/1.0 (educational)",
            })
            with urllib.request.urlopen(req, timeout=12, context=ctx) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.URLError as e:
            if isinstance(getattr(e, "reason", None), ssl.SSLError) or "CERTIFICATE" in str(e).upper():
                continue
            print(f"[form_data] {shortcut} 抓取失败: {e}")
            return []
        except (ssl.SSLError, json.JSONDecodeError, TimeoutError, OSError) as e:
            continue
    print(f"[form_data] {shortcut} 两次 SSL 策略均失败")
    return []


def _strict_ctx():
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(certifi.where())
        return ctx
    except Exception:
        return ssl.create_default_context()


def _unverified_ctx():
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def fetch_form(force=False):
    """抓取并缓存近期战绩。
    返回 {team: {games:[{opp, sf, sa, comp, date}], wr, gf_avg, ga_avg, sample_n, comps}}
    失败返回空 dict（调用方降级）"""
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    # {team: [game,...]}
    per_team = {}
    for shortcut, comp_zh in TOURNAMENTS:
        matches = _fetch_tournament(shortcut)
        for m in matches:
            score = _parse_score(m)
            if not score or score[0] is None:
                continue
            hg, ag = score
            t1 = _normalize(m["team1"]["teamName"])
            t2 = _normalize(m["team2"]["teamName"])
            if not t1 or not t2:
                continue
            date = (m.get("matchDateTime") or "")[:10]
            # 双向记录
            per_team.setdefault(t1, []).append(
                {"opp": t2, "sf": hg, "sa": ag, "comp": comp_zh, "date": date})
            per_team.setdefault(t2, []).append(
                {"opp": t1, "sf": ag, "sa": hg, "comp": comp_zh, "date": date})

    # 聚合每队指标
    result = {}
    for team, games in per_team.items():
        w = d = l = gf = ga = 0
        comps = set()
        for g in games:
            comps.add(g["comp"])
            gf += g["sf"]; ga += g["sa"]
            if g["sf"] > g["sa"]: w += 1
            elif g["sf"] < g["sa"]: l += 1
            else: d += 1
        n = len(games)
        result[team] = {
            "games": games,
            "w": w, "d": d, "l": l,
            "wr": round(100 * (w + 0.5 * d) / n, 0) if n else 0,  # 胜率(平局计0.5)
            "gf_avg": round(gf / n, 1) if n else 0,
            "ga_avg": round(ga / n, 1) if n else 0,
            "sample_n": n,
            "comps": sorted(comps),
        }
    _cache.update({"data": result, "ts": now})
    return result


def h2h(t1, t2, form=None):
    """从战绩语料派生两队历史交锋。
    返回 {sample_n, w1, w2, d, wr1(队1胜率%)} 或 None（无交锋记录）"""
    form = form if form is not None else fetch_form()
    games_t1 = (form.get(t1) or {}).get("games", [])
    # 筛两队共现
    meetings = [g for g in games_t1 if g["opp"] == t2]
    if not meetings:
        return None
    w1 = d = w2 = 0
    for g in meetings:
        if g["sf"] > g["sa"]: w1 += 1
        elif g["sf"] < g["sa"]: w2 += 1
        else: d += 1
    n = len(meetings)
    return {
        "sample_n": n, "w1": w1, "w2": w2, "d": d,
        "wr1": round(100 * (w1 + 0.5 * d) / n, 0),
    }


if __name__ == "__main__":
    form = fetch_form(force=True)
    print(f"抓到 {len(form)} 队近期战绩")
    print()
    import wc_data as W
    for t in ["France", "Spain", "Ghana", "Panama", "Germany", "Argentina"]:
        f = form.get(t)
        if f:
            print(f"{W.TEAMS[t]['zh']:4} ({t}): {f['sample_n']}场 {f['w']}-{f['d']}-{f['l']} "
                  f"胜率{f['wr']}% 场均进{f['gf_avg']}失{f['ga_avg']}  赛事:{f['comps']}")
        else:
            print(f"{W.TEAMS[t]['zh']:4} ({t}): 无大赛战绩数据（样本不足）")
    print()
    print("=== 加纳 vs 巴拿马 历史交锋 ===")
    h = h2h("Ghana", "Panama", form)
    print(h if h else "无交锋记录")
    print()
    print("=== 法国 vs 德国 历史交锋 ===")
    h = h2h("France", "Germany", form)
    print(h if h else "无交锋记录")
