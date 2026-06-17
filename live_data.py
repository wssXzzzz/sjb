# -*- coding: utf-8 -*-
"""
实时数据层：从 OpenLigaDB 抓取 2026 世界杯真实赛果
- fetch_matches(): 统一结构的比赛列表（已踢=真实比分 / 未踢=待预测）
- 5 分钟内存缓存；网络失败优雅降级返回空列表
- (team1,team2) 配对 → 反查所属小组
"""
import json
import time
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone

import wc_data as W

API_URL = "https://api.openligadb.de/getmatchdata/wm2026"
CACHE_TTL = 300  # 5 分钟

# 时区：展示统一用北京时间；兜底赛程里的硬编码时间是德国本地(夏令时 CEST=UTC+2)
BEIJING = timezone(timedelta(hours=8))
BERLIN_SUMMER = timezone(timedelta(hours=2))

_cache = {"data": None, "ts": 0, "source": "online"}


def _parse_utc(iso):
    """'2026-06-11T19:00:00Z' 或 '...+00:00' → 带时区的 UTC datetime；失败返回 None"""
    if not iso:
        return None
    try:
        dt = datetime.fromisoformat(iso.replace("Z", "+00:00"))
    except ValueError:
        try:
            dt = datetime.strptime(iso[:19], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            return None
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def to_beijing(utc_iso):
    """UTC ISO 字符串 → (date 'YYYY-MM-DD', time 'HH:MM') 北京时间；失败返回 (None, None)"""
    dt = _parse_utc(utc_iso)
    if not dt:
        return None, None
    bj = dt.astimezone(BEIJING)
    return bj.strftime("%Y-%m-%d"), bj.strftime("%H:%M")


def berlin_to_beijing(date, tm):
    """兜底赛程的德国本地(CEST)日期时间 → 北京时间 (date, time)；失败原样返回"""
    try:
        dt = datetime.strptime(f"{date} {tm}", "%Y-%m-%d %H:%M").replace(tzinfo=BERLIN_SUMMER)
    except (ValueError, TypeError):
        return date, tm
    bj = dt.astimezone(BEIJING)
    return bj.strftime("%Y-%m-%d"), bj.strftime("%H:%M")


def _parse_result(match):
    """从 API 单场比赛提取全场比分 (hg, ag)；未踢返回 (None, None)"""
    if not match.get("matchIsFinished"):
        return None, None
    results = match.get("matchResults") or []
    # Endergebnis = resultOrderID 2（全场）
    for r in results:
        if r.get("resultOrderID") == 2:
            return r.get("pointsTeam1"), r.get("pointsTeam2")
    # 退化：取最后一个
    if results:
        last = results[-1]
        return last.get("pointsTeam1"), last.get("pointsTeam2")
    return None, None


def _normalize_team(de_name):
    """德语队名 → 内部英文名；未知返回 None"""
    return W.DE_TO_EN.get(de_name)


def _is_knockout(match):
    """判断是否淘汰赛：API 的 group.groupName 含 'finale'/'achtel'/'viertel'/'halb' 等"""
    gn = (match.get("group", {}) or {}).get("groupName", "").lower()
    keywords = ("finale", "achtel", "viertel", "halb", "spiel um platz")
    return any(k in gn for k in keywords)


def fetch_matches(force=False):
    """抓取比赛列表，返回 dict:
       {matches: [...], last_updated: ISO时间, finished_count, total, source}
    每个 match: {team1, team2, group, md, date, time, venue,
                 finished, hg, ag, is_knockout, api_id}
    """
    now = time.time()
    if not force and _cache["data"] and (now - _cache["ts"]) < CACHE_TTL:
        return _cache["data"]

    raw = _fetch_api()
    if raw is None:
        # 降级：返回空（调用方据此走纯预测）
        result = {
            "matches": [], "last_updated": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
            "finished_count": 0, "total": 0, "source": "offline",
        }
        _cache.update({"data": result, "ts": now, "source": "offline"})
        return result

    matches = []
    for m in raw:
        t1 = _normalize_team(m["team1"]["teamName"])
        t2 = _normalize_team(m["team2"]["teamName"])
        if t1 is None or t2 is None:
            continue  # 未知球队，跳过
        hg, ag = _parse_result(m)
        finished = bool(m.get("matchIsFinished"))
        is_ko = _is_knockout(m)
        g = None if is_ko else W.find_group(t1, t2)
        md = W.find_matchday(g, t1, t2) if g else None
        # 权威开赛时间取 matchDateTimeUTC（带 Z 的真 UTC），换算成北京时间展示
        utc = m.get("matchDateTimeUTC")
        date, tm = to_beijing(utc)
        dt = f"{date} {tm}" if date else ""
        venue = _lookup_venue(g, t1, t2)
        matches.append({
            "team1": t1, "team2": t2, "group": g, "md": md,
            "date": date, "time": tm, "datetime": dt, "venue": venue,
            "utc": utc,
            "finished": finished, "hg": hg, "ag": ag,
            "is_knockout": is_ko, "api_id": m.get("matchID"),
        })

    finished_count = sum(1 for m in matches if m["finished"])
    result = {
        "matches": matches,
        "last_updated": time.strftime("%Y-%m-%d %H:%M", time.localtime()),
        "finished_count": finished_count,
        "total": len(matches),
        "source": "online",
    }
    _cache.update({"data": result, "ts": now, "source": "online"})
    return result


def _lookup_venue(g, t1, t2):
    """从兜底 GROUP_SCHEDULE 查球场代码 → 中文名"""
    if not g:
        return ""
    for (md, a, b, _d, _t, v) in W.GROUP_SCHEDULE.get(g, []):
        if {a, b} == {t1, t2}:
            return W.VENUES.get(v, "")
    return ""


def _make_ssl_context():
    """构造 SSL 上下文：优先用 certifi / 系统根证书做完整校验；
    仅当本机确实没有可用根证书时（如未配置的 macOS 默认 Python）才降级，
    避免对所有连接静默关闭证书验证。"""
    import ssl
    ctx = ssl.create_default_context()
    # 1) 优先 certifi 提供的根证书
    try:
        import certifi
        ctx.load_verify_locations(certifi.where())
        return ctx
    except Exception:
        pass
    # 2) 退回系统根证书
    try:
        ctx.load_default_certs()
        if ctx.get_ca_certs():
            return ctx
    except Exception:
        pass
    # 3) 实在没有根证书：降级（不校验），仅作为最后兜底
    print("[live_data] 警告：未找到可用根证书，本次请求将跳过 TLS 校验")
    ctx = ssl.create_default_context()
    ctx.check_hostname = False
    ctx.verify_mode = ssl.CERT_NONE
    return ctx


def _fetch_api():
    """实际 HTTP 请求；失败返回 None"""
    import ssl
    try:
        ctx = _make_ssl_context()
        req = urllib.request.Request(API_URL, headers={
            "Accept": "application/json",
            "User-Agent": "wc2026-predictor/1.0",
        })
        with urllib.request.urlopen(req, timeout=8, context=ctx) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, ValueError, OSError) as e:
        print(f"[live_data] API 抓取失败，降级为离线模式: {e}")
        return None


def real_results_index(live):
    """把已踢比赛整理成 {(t1,t2)frozenset): (hg,ag)} 便于查询"""
    idx = {}
    for m in live["matches"]:
        if m["finished"] and m["hg"] is not None:
            idx[frozenset((m["team1"], m["team2"]))] = (m["hg"], m["ag"])
    return idx


def schedule_index(live):
    """已发布对阵的权威开赛时间 {frozenset(t1,t2): utc_iso}（仅小组赛）。
    OpenLigaDB 目前仅含已开赛轮次，未发布的轮次不会出现在此索引中。"""
    idx = {}
    for m in live.get("matches", []):
        if m.get("utc") and not m.get("is_knockout"):
            idx[frozenset((m["team1"], m["team2"]))] = m["utc"]
    return idx


def played_games_per_team(live):
    """每支球队已踢的真实比赛列表 [{team1,team2,hg,ag}, ...]，用于动态 Elo"""
    per = {}
    for m in live["matches"]:
        if m["finished"] and m["hg"] is not None and not m["is_knockout"]:
            per.setdefault(m["team1"], []).append(m)
            per.setdefault(m["team2"], []).append(m)
    return per


if __name__ == "__main__":
    d = fetch_matches(force=True)
    print(f"数据源: {d['source']} | 已踢 {d['finished_count']}/{d['total']} 场")
    print(f"最后更新: {d['last_updated']}")
    print("\n已踢赛果:")
    for m in d["matches"]:
        if m["finished"]:
            z1, z2 = W.TEAMS[m["team1"]]["zh"], W.TEAMS[m["team2"]]["zh"]
            print(f"  {m['group'] or '?'}组  {z1} {m['hg']}-{m['ag']} {z2}")
    print("\n未踢(前5):")
    cnt = 0
    for m in d["matches"]:
        if not m["finished"] and cnt < 5:
            z1, z2 = W.TEAMS[m["team1"]]["zh"], W.TEAMS[m["team2"]]["zh"]
            print(f"  {m['group'] or '?'}组  {m['datetime']}  {z1} v {z2}  @{m['venue']}")
            cnt += 1
