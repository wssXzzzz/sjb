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
    sim = P.get_prediction(live)
    probs = P.get_probs(live, n=1000)

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
    upcoming = _build_upcoming(sim, live, played_per_team)

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


def _build_upcoming(sim, live, played_per_team, limit=16):
    """总览页高亮：所有未踢比赛的预测，按时间排序。
    返回 list，每场含预测比分+胜率。按日期分组返回便于 UI 展示。"""
    upcoming = [m for m in sim["group_matches"]
                if m.get("status") == "predicted"]
    if not upcoming:
        return []
    # 按日期+时间排序
    upcoming.sort(key=lambda m: (m["date"], m["time"]))
    items = []
    for m in upcoming[:limit]:
        h, a = m["home"], m["away"]
        wp = P.win_prob(h, a, played_per_team)
        reasons = R.generate_reasons(h, a, played_per_team, m["hg"], m["ag"])
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


# 视图缓存：5 分钟（与 live_data 缓存对齐）
_VIEW_CACHE = {"data": None, "ts": 0}
_VIEW_TTL = 300


def get_view(force=False):
    now = time.time()
    if force or not _VIEW_CACHE["data"] or (now - _VIEW_CACHE["ts"]) > _VIEW_TTL:
        _VIEW_CACHE["data"] = build_view()
        _VIEW_CACHE["ts"] = now
    return _VIEW_CACHE["data"]


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
