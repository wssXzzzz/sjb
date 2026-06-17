# -*- coding: utf-8 -*-
"""2026 世界杯比分预测 · Flask 应用（实时混合预测版）"""
import json
import os
import time
from flask import Flask, render_template, jsonify

import predictor as P
import wc_data as W
import live_data as LD
import reasons as R
import squad_data as SD
import form_data as FD

app = Flask(__name__)
app.config["TEMPLATES_AUTO_RELOAD"] = True


def team_view(name, played_per_team=None):
    """转成前端展示用的球队 dict"""
    if not name:
        return None
    t = W.TEAMS[name]
    return {"name": name, "zh": t["zh"], "code": t["code"],
            "flag": t["flag"], "rank": t["rank"],
            "elo": round(P.elo_of(name, played_per_team))}


def build_view():
    """构建完整页面数据：实时抓取真实赛果 + 动态 Elo 预测"""
    live = LD.fetch_matches()
    played_per_team = (LD.played_games_per_team(live)
                       if live.get("source") == "online" else None)
    # 多维度数据：阵容质量（Wikipedia）+ 近期战绩（OpenLigaDB 大赛）
    squads = SD.fetch_squads()
    form = FD.fetch_form()
    P.set_dimensions(squads=squads, form=form)   # 注入预测器（模块级）
    sim = P.get_prediction(live)
    probs = P.get_probs(live, n=1000)

    # ---- 开赛时间统一为北京时间 ----
    # 权威来源：OpenLigaDB 的 matchDateTimeUTC；未发布的轮次退回兜底赛程
    # （兜底里硬编码的是德国本地 CEST 时间，按 +6h 折算成北京时间）。
    sched_idx = LD.schedule_index(live)
    for m in sim["group_matches"]:
        utc = sched_idx.get(frozenset((m["home"], m["away"])))
        if utc:
            d, t = LD.to_beijing(utc)
        else:
            d, t = LD.berlin_to_beijing(m["date"], m["time"])
        if d and t:
            m["date"], m["time"] = d, t

    # ---- 小组赛视图 ----
    groups_view = {}
    for g in W.all_group_names():
        rows = sim["standings"][g]
        matches = [m for m in sim["group_matches"] if m["group"] == g]
        # 按轮次排序
        matches.sort(key=lambda m: (m["md"], m["date"]))
        groups_view[g] = {
            "table": [{
                "team": r["team"], "zh": W.TEAMS[r["team"]]["zh"],
                "flag": W.TEAMS[r["team"]]["flag"], "pos": r["pos"],
                "pts": r["pts"], "gd": r["gd"], "gf": r["gf"],
                "w": r["w"], "d": r["d"], "l": r["l"],
                "qualified": r["pos"] <= 2,
                "is_third": r["pos"] == 3,
                "third_qualified": (r["pos"] == 3 and
                                    any(qt["team"] == r["team"]
                                        for qt in sim["qualified_thirds"])),
            } for r in rows],
            "matches": [{
                "md": m["md"], "home": m["home"], "away": m["away"],
                "home_zh": W.TEAMS[m["home"]]["zh"],
                "away_zh": W.TEAMS[m["away"]]["zh"],
                "home_flag": W.TEAMS[m["home"]]["flag"],
                "away_flag": W.TEAMS[m["away"]]["flag"],
                "hg": m["hg"], "ag": m["ag"],
                "date": m["date"], "time": m["time"],
                "venue": m.get("venue", ""),
                "status": m.get("status", "predicted"),  # finished / predicted
            } for m in matches],
        }

    # ---- 淘汰赛视图 ----
    ko_view = []
    for r in sim["ko_results"]:
        ko_view.append({
            "id": r["id"], "round": r["round"],
            "round_zh": W.ROUND_NAMES[r["round"]],
            "home": team_view(r["home"], played_per_team),
            "away": team_view(r["away"], played_per_team),
            "hg": r["hg"], "ag": r["ag"],
            "pen": W.TEAMS[r["pen"]]["zh"] if r["pen"] else None,
            "winner": team_view(r["winner"], played_per_team),
            "loser": team_view(r["loser"], played_per_team),
            "date": r["date"],
            "status": "predicted",  # 淘汰赛尚未开始
        })

    # ---- 概率排行 ----
    prob_ranking = sorted(probs.items(), key=lambda x: -x[1]["title"])
    probs_view = [{
        "team": t, "zh": W.TEAMS[t]["zh"], "flag": W.TEAMS[t]["flag"],
        "rank": W.TEAMS[t]["rank"],
        "elo": round(P.elo_of(t, played_per_team)),
        "elo_base": round(P.base_elo(t)),
        "title": p["title"], "final": p["final"], "sf": p["sf"], "r16": p["r16"],
    } for t, p in prob_ranking if p["title"] > 0 or p["r16"] > 5][:24]

    # ---- 冠军路径 ----
    champion = sim["champion"]
    path = [r for r in sim["ko_results"] if r["winner"] == champion]
    champion_path = [{
        "round": r["round"], "round_zh": W.ROUND_NAMES[r["round"]],
        "opp_zh": W.TEAMS[r["home"] if r["away"] == champion else r["away"]]["zh"],
        "opp_flag": W.TEAMS[r["home"] if r["away"] == champion else r["away"]]["flag"],
        "cg": r["hg"] if r["home"] == champion else r["ag"],
        "og": r["ag"] if r["home"] == champion else r["hg"],
    } for r in path]

    # ---- 近期未踢比赛预测列表（总览页高亮）----
    upcoming = _build_upcoming(sim, live, played_per_team, squads=squads, form=form)

    # ---- 进行中/待数据：已开球但数据源未出分 ----
    live_now = _build_live_now(sim)

    # ---- 复盘：赛前预测 vs 真实赛果 准确率 ----
    accuracy = _build_accuracy(live)

    # ---- 淘汰赛阶段名单（夺冠页用）----
    # 16强 = R32 的 16 个胜者
    r16_teams = [r["winner"] for r in sim["ko_results"] if r["round"] == "R32"]
    # 8强 = R16 的 8 个胜者
    r8_teams = [r["winner"] for r in sim["ko_results"] if r["round"] == "R16"]
    # 4强 = QF 的 4 个胜者
    r4_teams = [r["winner"] for r in sim["ko_results"] if r["round"] == "QF"]

    def _team_list(teams):
        return [{"zh": W.TEAMS[t]["zh"], "flag": W.TEAMS[t]["flag"],
                 "rank": W.TEAMS[t]["rank"],
                 "elo": round(P.elo_of(t, played_per_team))} for t in teams]

    # ---- 进度统计 ----
    total_group = sum(len(W.GROUP_SCHEDULE[g]) for g in W.GROUPS)
    finished_group = sum(1 for m in sim["group_matches"] if m.get("status") == "finished")

    return {
        "champion": team_view(champion, played_per_team),
        "runner_up": team_view(sim["runner_up"], played_per_team),
        "groups": groups_view,
        "qualified_thirds": [{
            "group": qt["group"], "team": qt["team"],
            "zh": W.TEAMS[qt["team"]]["zh"], "flag": W.TEAMS[qt["team"]]["flag"],
            "pts": qt["pts"], "gd": qt["gd"],
        } for qt in sim["qualified_thirds"]],
        "knockout": ko_view,
        "probs": probs_view,
        "champion_path": champion_path,
        "upcoming": upcoming,
        "live_now": live_now,
        "accuracy": accuracy,
        "round16": _team_list(r16_teams),
        "round8": _team_list(r8_teams),
        "round4": _team_list(r4_teams),
        "progress": {
            "finished": finished_group,
            "total": total_group,
            "percent": round(100 * finished_group / total_group, 0) if total_group else 0,
        },
        "live": {
            "source": live.get("source", "offline"),
            "last_updated": live.get("last_updated", ""),
            "online": live.get("source") == "online",
        },
        "seed": P.MASTER_SEED,
        "team_count": len(W.TEAMS),
        "groups_count": len(W.GROUPS),
        "venues_count": len(W.VENUES),
    }


def _build_upcoming(sim, live, played_per_team, squads=None, form=None, limit=16):
    """总览页高亮：所有未踢比赛的预测，按时间排序。
    返回 list，每场含预测比分+胜率+多维度理由。按日期分组返回便于 UI 展示。"""
    # 只保留"尚未开赛"的预测场：已过开球时间的（即便数据源还没标记完赛）不再算下一场
    upcoming = [m for m in sim["group_matches"]
                if m.get("status") == "predicted"
                and not LD.is_past_beijing(m.get("date"), m.get("time"))]
    if not upcoming:
        return []
    # 按日期+时间排序
    upcoming.sort(key=lambda m: (m["date"], m["time"]))
    items = []
    for m in upcoming[:limit]:
        h, a = m["home"], m["away"]
        wp = P.win_prob(h, a, played_per_team)
        # 直接用 sim 里的比分（确定性=最可能比分），保证与小组赛页同场一致
        reasons = R.generate_reasons(h, a, played_per_team, m["hg"], m["ag"],
                                      squads=squads, form=form)
        items.append({
            "group": m["group"], "md": m["md"],
            "home": h, "away": a,
            "home_zh": W.TEAMS[h]["zh"], "away_zh": W.TEAMS[a]["zh"],
            "home_flag": W.TEAMS[h]["flag"], "away_flag": W.TEAMS[a]["flag"],
            "hg": m["hg"], "ag": m["ag"],
            "home_win": round(100 * wp, 0),
            "away_win": round(100 * (1 - wp), 0),
            "date": m["date"], "time": m["time"], "venue": m.get("venue", ""),
            "reasons": reasons,
        })
    return items


def _build_live_now(sim, limit=6):
    """已过开球时间但数据源仍未出比分的小组赛（"进行中/待数据"）。
    与 _build_upcoming 互补：那边按同一 is_past_beijing 把这些场过滤掉了，
    这里把它们单独捞出来给前端做"进行中"提示，避免比赛从界面凭空消失。"""
    now_playing = [m for m in sim["group_matches"]
                   if m.get("status") == "predicted"
                   and LD.is_past_beijing(m.get("date"), m.get("time"))]
    now_playing.sort(key=lambda m: (m.get("date") or "", m.get("time") or ""), reverse=True)
    items = []
    for m in now_playing[:limit]:
        h, a = m["home"], m["away"]
        items.append({
            "group": m["group"], "md": m["md"],
            "home_zh": W.TEAMS[h]["zh"], "away_zh": W.TEAMS[a]["zh"],
            "home_flag": W.TEAMS[h]["flag"], "away_flag": W.TEAMS[a]["flag"],
            "hg": m["hg"], "ag": m["ag"],
            "date": m["date"], "time": m["time"],
        })
    return items


def _build_accuracy(live):
    """复盘：把已踢真实赛果与「赛前实力预测」逐场对比，给出准确率指标。
    预测仅用赛前基础 Elo（predicted_scoreline，不看结果）→ 诚实、无信息泄漏。
    返回 {summary, matches}；离线或暂无完赛时 matches 为空。"""
    rows = []
    n = outcome_ok = exact_ok = goal_err = points = 0
    for m in (live.get("matches") or []):
        if not m.get("finished") or m.get("is_knockout") or m.get("hg") is None:
            continue
        t1, t2 = m["team1"], m["team2"]
        rhg, rag = m["hg"], m["ag"]
        phg, pag = P.predicted_scoreline(t1, t2)
        real_sign = (rhg > rag) - (rhg < rag)
        pred_sign = (phg > pag) - (phg < pag)
        o_ok = (real_sign == pred_sign)
        e_ok = (phg == rhg and pag == rag)
        n += 1
        outcome_ok += o_ok
        exact_ok += e_ok
        goal_err += abs(phg - rhg) + abs(pag - rag)
        points += 3 if e_ok else (1 if o_ok else 0)
        rows.append({
            "group": m.get("group"), "date": m.get("date"),
            "home": t1, "away": t2,
            "home_zh": W.TEAMS[t1]["zh"], "away_zh": W.TEAMS[t2]["zh"],
            "home_flag": W.TEAMS[t1]["flag"], "away_flag": W.TEAMS[t2]["flag"],
            "real_hg": rhg, "real_ag": rag, "pred_hg": phg, "pred_ag": pag,
            "outcome_correct": bool(o_ok), "exact_correct": bool(e_ok),
        })
    rows.sort(key=lambda x: (x["date"] or "", x["group"] or ""))
    return {
        "summary": {
            "finished": n,
            "outcome_correct": int(outcome_ok),
            "exact_correct": int(exact_ok),
            "outcome_pct": round(100 * outcome_ok / n) if n else 0,
            "exact_pct": round(100 * exact_ok / n) if n else 0,
            "goal_mae": round(goal_err / n, 2) if n else 0,
            "points": points,
            "max_points": n * 3,
        },
        "matches": rows,
    }


# 视图缓存：5 分钟（与 live_data 缓存对齐）
_VIEW_CACHE = {"data": None, "ts": 0}
_VIEW_TTL = 300


def get_view(force=False):
    now = time.time()
    if force or not _VIEW_CACHE["data"] or (now - _VIEW_CACHE["ts"]) > _VIEW_TTL:
        _VIEW_CACHE["data"] = build_view()
        _VIEW_CACHE["ts"] = now
    return _VIEW_CACHE["data"]


# 生产环境（gunicorn --preload）下在导入时预热缓存：
# 主进程构建一次，fork 出的 worker 通过写时复制继承，首个请求即命中缓存。
# 设 WARMUP=1 时启用；普通 import（如测试）不触发网络请求。
if os.environ.get("WARMUP") == "1":
    try:
        print("预热预测缓存中...")
        get_view()
    except Exception as e:
        print(f"预热失败（将在首个请求时重试）: {e}")


@app.route("/")
def index():
    return render_template("index.html",
                           view=json.dumps(get_view(), ensure_ascii=False))


@app.route("/api/data")
def api_data():
    return jsonify(get_view())


@app.route("/api/refresh")
def api_refresh():
    """强制刷新（重新抓 API + 重建预测）"""
    LD.fetch_matches(force=True)
    return jsonify(get_view(force=True))


if __name__ == "__main__":
    print("正在抓取实时赛果并生成预测（首次稍慢）...")
    get_view()
    port = int(os.environ.get("PORT", 8000))
    print(f"就绪 → http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
