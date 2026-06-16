# -*- coding: utf-8 -*-
"""
预测理由生成器
为每场预测比赛生成结构化、有数据支撑的理由（要点 + 总评）。
诚实原则：只用排名、Elo、已踢战绩、足联等可查证数据，不编造历史交锋细节。
"""
import wc_data as W
import predictor as P


def _team_zh(team):
    return W.TEAMS[team]["zh"]


def _form_text(team, played):
    """从已踢真实比赛生成近期状态描述；无数据返回 None"""
    games = played.get(team) if played else None
    if not games:
        return None
    w = d = l = gf = ga = 0
    for m in games:
        is_home = (m["team1"] == team)
        gh = m["hg"] if is_home else m["ag"]
        go = m["ag"] if is_home else m["hg"]
        gf += gh; ga += go
        if gh > go: w += 1
        elif gh < go: l += 1
        else: d += 1
    n = w + d + l
    return f"{n}战{w}胜{d}平{l}负，场均进{gf/n:.1f}球失{ga/n:.1f}球"


def _elo_change_text(team, played):
    """已踢后 Elo 变化描述；无变化返回 None"""
    if not played or team not in played:
        return None
    base = P.base_elo(team)
    now = P.live_elo(team, played)
    diff = round(now - base)
    if abs(diff) < 8:
        return None
    sign = "升" if diff > 0 else "降"
    return f"实力分{sign}{abs(diff)}（基础{round(base)}→{round(now)}）"


def _gap_level(rank_diff):
    """把排名差转为口语化的实力档位描述"""
    if rank_diff <= 3:
        return "实力接近"
    if rank_diff <= 10:
        return "略有优势"
    if rank_diff <= 25:
        return "明显占优"
    if rank_diff <= 50:
        return "实力悬殊"
    return "实力碾压"


def generate_reasons(home, away, played_per_team, pred_hg, pred_ag):
    """生成一场比赛的预测理由。
    返回 {favorite, points:[...], summary}
    所有数据来自 predictor.py 的真实计算，不编造。"""
    h_meta = W.TEAMS[home]
    a_meta = W.TEAMS[away]
    h_elo = round(P.elo_of(home, played_per_team))
    a_elo = round(P.elo_of(away, played_per_team))
    elo_diff = h_elo - a_elo
    wp = P.win_prob(home, away, played_per_team)
    fav = home if wp >= 0.5 else away
    fav_zh = _team_zh(fav)
    fav_pct = round(100 * max(wp, 1 - wp))
    opp_pct = 100 - fav_pct

    points = []
    summary = ""

    # ---- 要点1：FIFA 排名对比 ----
    h_rank, a_rank = h_meta["rank"], a_meta["rank"]
    rank_diff = abs(h_rank - a_rank)
    opp_zh = _team_zh(away if fav == home else home)
    points.append(f"FIFA排名：{fav_zh}第{min(h_rank,a_rank)}位 vs {opp_zh}第{max(h_rank,a_rank)}位")

    # ---- 要点2：实力推导（Elo→胜率因果链）----
    points.append(f"实力分：{fav_zh} {max(h_elo,a_elo)} vs {_team_zh(away if fav==home else home)} {min(h_elo,a_elo)}（差{abs(elo_diff)}→胜率{fav_pct}%）")

    # ---- 要点3：近期状态（有已踢数据时）----
    h_form = _form_text(home, played_per_team)
    a_form = _form_text(away, played_per_team)
    fav_form = h_form if fav == home else a_form
    if fav_form:
        points.append(f"近期状态：{fav_zh}{fav_form}")

    # ---- 要点4：情境因素 ----
    situ = []
    if h_meta.get("host") or a_meta.get("host"):
        host_team = home if h_meta.get("host") else away
        situ.append(f"{_team_zh(host_team)}为东道主，享主场加成(+80)")
    if h_meta["conf"] != a_meta["conf"]:
        # 跨足联对阵，标注
        situ.append(f"跨洲对阵：{fav_zh}({h_meta['conf'] if fav==home else a_meta['conf']}) vs {_team_zh(away if fav==home else home)}({a_meta['conf'] if fav==home else h_meta['conf']})")
    # Elo 变化（已踢后动态调整）
    fav_change = _elo_change_text(fav, played_per_team)
    if fav_change:
        situ.append(fav_change)
    if situ:
        points.append(" · ".join(situ))

    # ---- 总评（综合实力差距给出一句结论）----
    gap = _gap_level(rank_diff)
    is_draw = (pred_hg == pred_ag)
    score_str = f"{pred_hg}-{pred_ag}"
    if is_draw:
        if abs(elo_diff) < 120:
            summary = f"两队实力接近，预测 {score_str} 平局合理，胜负看临场。"
        else:
            summary = f"虽 {fav_zh}{gap}（胜率{fav_pct}%），但本场预测 {score_str} 平局，或有冷门空间。"
    elif abs(elo_diff) < 80:
        summary = f"两队{_gap_level(1)}，胜负五五开，预测 {score_str}，不排除平局甚至冷门。"
    elif abs(elo_diff) < 200:
        summary = f"{fav_zh}{gap}，但并非铁板一块，预测 {score_str} 小胜可期。"
    else:
        summary = f"{fav_zh}{gap}（胜率{fav_pct}%），预测 {score_str} 合理拿下。"

    return {"favorite": fav_zh, "favorite_pct": fav_pct, "opponent_pct": opp_pct,
            "points": points, "summary": summary}


if __name__ == "__main__":
    # 测试
    import live_data as LD
    live = LD.fetch_matches(force=True)
    played = LD.played_games_per_team(live)
    cases = [("France", "Senegal"), ("Argentina", "Algeria"),
             ("England", "Croatia"), ("Turkey", "Paraguay")]
    for h, a in cases:
        r = generate_reasons(h, a, played, 2, 0)
        print(f"\n=== {_team_zh(h)} vs {_team_zh(a)} ===")
        print(f"看好: {r['favorite']} ({r['favorite_pct']}%)")
        for p in r["points"]:
            print(f"  • {p}")
        print(f"  → {r['summary']}")
