# -*- coding: utf-8 -*-
"""
阵容质量数据层：从 Wikipedia 2026_FIFA_World_Cup_squads 抓取每队阵容，
计算平均年龄、五大联赛球员占比、平均国脚出场、头号射手。
纯 stdlib 解析（正则提取 wikitable），缓存 1 小时（赛期阵容基本不变）。
"""
import re
import time
import urllib.request
import urllib.error
from datetime import date

import wc_data as W

SQUADS_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup_squads"
CACHE_TTL = 3600  # 1 小时

_cache = {"data": None, "ts": 0}

# ---------------------------------------------------------------------------
# 五大联赛俱乐部集合（2025-26 赛季英超/西甲/意甲/德甲/法甲）
# 用于计算"五大联赛球员占比"作为球员实力的市场化代理
# ---------------------------------------------------------------------------
TOP5_CLUBS = {
    # 英超 Premier League 2025-26
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton & Hove Albion",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Liverpool",
    "Manchester City", "Manchester United", "Newcastle United", "Nottingham Forest",
    "Tottenham Hotspur", "West Ham United", "Wolverhampton Wanderers",
    "Sunderland", "Leeds United", "Burnley",
    # 西甲 La Liga 2025-26
    "Athletic Bilbao", "Atlético Madrid", "Barcelona", "Celta Vigo", "Girona",
    "Mallorca", "Osasuna", "Rayo Vallecano", "Real Betis", "Real Madrid",
    "Real Sociedad", "Sevilla", "Valencia", "Villarreal", "Las Palmas",
    "Getafe", "Alavés", "Espanyol", "Leganes", "Elche",
    # 意甲 Serie A 2025-26
    "Atalanta", "Bologna", "Cagliari", "Como", "Fiorentina", "Genoa",
    "Inter Milan", "Juventus", "Lazio", "Lecce", "Milan", "Napoli",
    "Parma", "Roma", "Torino", "Udinese", "Verona", "Cremonese",
    "Pisa", "Sassuolo",
    # 德甲 Bundesliga 2025-26
    "Bayern Munich", "Borussia Dortmund", "Bayer Leverkusen", "RB Leipzig",
    "Eintracht Frankfurt", "VfB Stuttgart", "Freiburg", "Mainz 05",
    "Wolfsburg", "Werder Bremen", "Augsburg", "TSG Hoffenheim",
    "Borussia Mönchengladbach", "Union Berlin", "Heidenheim", "St. Pauli",
    "Cologne", "Hamburger SV", "Fortuna Düsseldorf", "Karlsruher SC",
    # 法甲 Ligue 1 2025-26
    "Paris Saint-Germain", "Marseille", "Monaco", "Lille", "Lyon",
    "Nice", "Lens", "Rennes", "Strasbourg", "Toulouse",
    "Nantes", "Brest", "Auxerre", "Angers", "Le Havre",
    "Montpellier", "Reims", "Metz", "Paris FC", "Lorient",
}

# Wikipedia h3 id → TEAMS 键的归一映射（下划线/异名）
WP_NAME_MAP = {
    "South Korea": "South Korea", "Korea Republic": "South Korea",
    "Ivory Coast": "Ivory Coast", "Côte d'Ivoire": "Ivory Coast",
    "United States": "United States", "USA": "United States",
    "Czech Republic": "Czech Republic", "Czechia": "Czech Republic",
    "DR Congo": "DR Congo", "Congo DR": "DR Congo",
    "Cape Verde": "Cape Verde", "Cabo Verde": "Cape Verde",
    "Bosnia and Herzegovina": "Bosnia and Herz.",
    "Saudi Arabia": "Saudi Arabia",
    "Curaçao": "Curacao", "Curacao": "Curacao",
}


def _age_from_dob(dob_str):
    """从 '1994-04-25' 算年龄（相对今天）"""
    try:
        y, m, d = map(int, dob_str.split("-"))
        today = date.today()
        age = today.year - y - ((today.month, today.day) < (m, d))
        return age
    except (ValueError, TypeError):
        return None


def _parse_squads_html(html):
    """解析 Wikipedia squads 页 HTML → {team_en: {avg_age, top5_pct, avg_caps, top_scorer, squad_size}}"""
    result = {}
    # 页面结构：<h3 id="Team_Name">Team Name</h3> 或 <h3 id="X"><span...></span>Team Name</h3>
    # 正则容忍内部 span 占位：id 固定捕获，display 从整段内容提取纯文本
    headings = list(re.finditer(r'<h3[^>]*id="([^"]+)"[^>]*>(.*?)</h3>', html, re.S))

    for i, h in enumerate(headings):
        # group(1)=id(下划线), group(2)=显示文本(空格)；优先用显示文本归一
        raw_id = h.group(1).replace("_", " ")
        # display：从整段内容（可能含 span 占位）提取纯文本
        display = re.sub(r"<[^>]+>", "", h.group(2)).strip() or raw_id
        start = h.end()
        end = headings[i + 1].start() if i + 1 < len(headings) else len(html)
        seg = html[start:end]
        # 找第一个 wikitable
        m = re.search(r'<table[^>]*class="[^"]*wikitable[^"]*"[^>]*>(.*?)</table>',
                      seg, re.S)
        if not m:
            continue
        table_html = m.group(1)
        rows = re.findall(r'<tr[^>]*>(.*?)</tr>', table_html, re.S)
        players = []
        for r in rows:
            cells = re.findall(r'<t[hd][^>]*>(.*?)</t[hd]>', r, re.S)
            if len(cells) != 7:
                continue  # 表头或不规则行
            club_raw = re.sub(r"<[^>]+>", " ", cells[6])
            club = _decode_entities(club_raw).strip()
            # DOB 单元格含 ISO 日期：(1994-04-25)...
            dob_m = re.search(r"\((\d{4}-\d{2}-\d{2})\)", cells[3])
            age = _age_from_dob(dob_m.group(1)) if dob_m else _age_from_parens(cells[3])
            caps = _to_int(cells[4])
            goals = _to_int(cells[5])
            name = _clean_player_name(_decode_entities(re.sub(r"<[^>]+>", "", cells[2])).strip())
            if age is None and caps is None and goals is None:
                continue  # 跳过无效行
            players.append({
                "name": name, "age": age, "caps": caps or 0,
                "goals": goals or 0, "club": club,
            })
        if not players:
            continue
        # 归一队名到 TEAMS 键（优先用显示文本，回退用 id）
        team_key = _normalize_team_name(display)
        if not team_key:
            team_key = _normalize_team_name(raw_id)
        if not team_key:
            continue
        ages = [p["age"] for p in players if p["age"] is not None]
        caps = [p["caps"] for p in players if p["caps"] is not None]
        top5_count = sum(1 for p in players if _is_top5(p["club"]))
        # 头号射手（进球最多；并列取第一个）
        scorer = max(players, key=lambda p: p["goals"]) if players else None
        result[team_key] = {
            "avg_age": round(sum(ages) / len(ages), 1) if ages else None,
            "top5_pct": round(100 * top5_count / len(players), 0),
            "avg_caps": round(sum(caps) / len(caps), 0) if caps else 0,
            "top_scorer": scorer["name"] if scorer and scorer["goals"] > 0 else None,
            "top_scorer_goals": scorer["goals"] if scorer else 0,
            "squad_size": len(players),
        }
    return result


def _is_top5(club):
    """俱乐部是否属于五大联赛（模糊匹配：包含关系）"""
    if not club:
        return False
    c = club.strip()
    if c in TOP5_CLUBS:
        return True
    # 模糊：如 "Manchester City" 也可能写成带后缀
    for t5 in TOP5_CLUBS:
        if c == t5 or (len(t5) > 6 and (t5 in c or c in t5)):
            return True
    return False


def _age_from_parens(cell):
    """兜底：从 '(aged 32)' 提取年龄"""
    m = re.search(r"aged\s*(\d+)", cell)
    return int(m.group(1)) if m else None


def _to_int(s):
    s = re.sub(r"<[^>]+>", "", s).strip()
    try:
        return int(s)
    except ValueError:
        return None


def _decode_entities(s):
    return (s.replace("&amp;", "&").replace("&nbsp;", " ")
             .replace("&#160;", " ").strip())


def _clean_player_name(s):
    """清洗球员名：去掉 (captain) 等括号后缀"""
    # 去 (captain) (vice-captain) 等
    s = re.sub(r"\s*\([^)]*(captain|vice)[^)]*\)", "", s, flags=re.I)
    return s.strip()


def _normalize_team_name(raw):
    """Wikipedia h3 id/display → TEAMS 键（含变音符归一）"""
    import unicodedata
    raw = raw.strip()
    # 直接匹配 / 映射表匹配（原始形式）
    if raw in W.TEAMS:
        return raw
    if raw in WP_NAME_MAP:
        return WP_NAME_MAP[raw]
    # 变音符归一（Curaçao→Curacao）后再查映射表与 TEAMS
    asc = unicodedata.normalize("NFKD", raw).encode("ascii", "ignore").decode()
    if asc in W.TEAMS:
        return asc
    if asc in WP_NAME_MAP:
        return WP_NAME_MAP[asc]
    return None


def fetch_squads(force=False):
    """抓取并缓存阵容数据。失败返回空 dict（调用方据此降级）"""
    now = time.time()
    if not force and _cache["data"] is not None and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]
    html = _fetch_html()
    if not html:
        _cache.update({"data": {}, "ts": now})
        return {}
    data = _parse_squads_html(html)
    _cache.update({"data": data, "ts": now})
    return data


def _fetch_html():
    """逐级尝试 SSL 策略；校验失败则降级"""
    import ssl
    for ctx in (_ssl_ctx_strict(), _ssl_ctx_unverified()):
        try:
            req = urllib.request.Request(SQUADS_URL, headers={
                "Accept": "text/html",
                "User-Agent": "wc2026-squad/1.0 (educational)",
            })
            with urllib.request.urlopen(req, timeout=15, context=ctx) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.URLError as e:
            # SSL 校验失败封装在 URLError.reason 里 → 降级重试
            if isinstance(e.reason, ssl.SSLError) or "CERTIFICATE" in str(e).upper():
                continue
            print(f"[squad_data] 抓取失败: {e}")
            return None
        except ssl.SSLError:
            continue  # 证书问题 → 降级重试
        except (urllib.error.HTTPError, TimeoutError, OSError) as e:
            print(f"[squad_data] 抓取失败: {e}")
            return None
    print("[squad_data] 两次 SSL 策略均失败")
    return None


def _ssl_ctx_strict():
    """严格校验：certifi → 系统证书"""
    import ssl
    try:
        import certifi
        ctx = ssl.create_default_context()
        ctx.load_verify_locations(certifi.where())
        return ctx
    except Exception:
        pass
    return ssl.create_default_context()


def _ssl_ctx_unverified():
    """降级：跳过校验（开发环境兜底）"""
    import ssl
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


if __name__ == "__main__":
    data = fetch_squads(force=True)
    print(f"解析到 {len(data)} 队阵容数据")
    print()
    # 抽样展示
    for t in ["France", "Ghana", "Panama", "Spain", "Brazil", "Argentina"]:
        s = data.get(t)
        if s:
            print(f"{W.TEAMS[t]['zh']:6} ({t}):")
            print(f"  平均年龄 {s['avg_age']}  五大联赛占比 {s['top5_pct']}%  "
                  f"场均国脚出场 {s['avg_caps']}  阵容 {s['squad_size']}人")
            if s["top_scorer"]:
                print(f"  头号射手 {s['top_scorer']} ({s['top_scorer_goals']}球)")
        else:
            print(f"{t}: 未解析到 ✗")
