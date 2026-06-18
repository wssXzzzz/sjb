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


def _squad_point(fav, opp, squads):
    """阵容质量对比要点；数据缺失返回 None"""
    fs, os_ = squads.get(fav), squads.get(opp)
    if not fs or not os_:
        return None
    parts = []
    if fs.get("top5_pct") is not None and os_.get("top5_pct") is not None:
        parts.append(f"五大联赛球员 {fs['top5_pct']:.0f}% vs {os_['top5_pct']:.0f}%")
    if fs.get("avg_age") and os_.get("avg_age"):
        parts.append(f"平均年龄 {fs['avg_age']} vs {os_['avg_age']}岁")
    if fs.get("avg_caps") is not None and os_.get("avg_caps") is not None:
        parts.append(f"场均国脚出场 {fs['avg_caps']:.0f} vs {os_['avg_caps']:.0f}次")
    if fs.get("top_scorer") and fs["top_scorer_goals"] > 0:
        parts.append(f"头号射手 {fs['top_scorer']}({fs['top_scorer_goals']}球)")
    if not parts:
        return None
    return f"阵容：{_team_zh(fav)} vs {_team_zh(opp)} — " + " · ".join(parts)


def _form_point(fav, opp, form):
    """近期战绩要点；样本不足如实标注，无数据返回 None"""
    ff = form.get(fav)
    if not ff or ff["sample_n"] == 0:
        return None
    n = ff["sample_n"]
    comps = "/".join(ff["comps"]) if ff.get("comps") else "大赛"
    if n < 3:
        return f"近期：{_team_zh(fav)}大赛样本不足({n}场{comps})，仅供参考"
    return (f"近期：{_team_zh(fav)}近{n}场{comps} {ff['w']}胜{ff['d']}平{ff['l']}负，"
            f"场均进{ff['gf_avg']}失{ff['ga_avg']}")


def _h2h_point(home, away, form):
    """历史交锋要点；无交锋或样本不足返回 None（不编造）"""
    try:
        import form_data as FD
        h = FD.h2h(home, away, form)
    except Exception:
        return None
    if not h or h["sample_n"] < 2:
        return None
    n = h["sample_n"]
    hzh, azh = _team_zh(home), _team_zh(away)
    if h["w1"] > h["w2"]:
        verdict = f"{hzh}占优({h['w1']}胜{h['d']}平{h['w2']}负)"
    elif h["w2"] > h["w1"]:
        verdict = f"{azh}占优({h['w2']}胜{h['d']}平{h['w1']}负)"
    else:
        verdict = f"势均力敌(各{h['w1']}胜{h['d']}平)"
    return f"交锋：{hzh} vs {azh} 近{n}次相遇，{verdict}"


def _odds_point(fav, opp, home, away, odds):
    """市场赔率要点：隐含胜平负 + 模型与市场一致/分歧标注（ODDS_PLAN.md §4）。"""
    try:
        import odds_data as OD
    except Exception:
        return None
    ov = OD.odds_for(home, away, odds)
    if not ov:
        return None
    fav_is_home = (fav == home)
    fav_pct = round(100 * (ov["pH"] if fav_is_home else ov["pA"]))
    try:
        import predictor as P
        b = P.model_1x2(home, away)
        model_fav_pct = round(100 * (b[0] if fav_is_home else b[2]))
    except Exception:
        model_fav_pct = None
    diff = abs(fav_pct - model_fav_pct) if model_fav_pct is not None else 0
    note = f"（市场与模型分歧{diff}%）" if diff > 20 else "（市场与模型基本一致）"
    return (f"赔率：市场隐含 主胜{ov['pH']*100:.0f}% / 平{ov['pD']*100:.0f}% / "
            f"客胜{ov['pA']*100:.0f}%（{ov.get('books_n',0)}家均值）{note}")


def generate_reasons(home, away, played_per_team, pred_hg, pred_ag, squads=None, form=None, odds=None):
    """生成一场比赛的预测理由。
    返回 {favorite, points:[...], summary}
    所有数据来自 predictor.py 的真实计算，不编造。
    squads: 阵容数据 dict（来自 squad_data）；form: 近期战绩 dict（来自 form_data）"""
    h_meta = W.TEAMS[home]
    a_meta = W.TEAMS[away]
    h_elo = round(P.elo_of(home, played_per_team))
    a_elo = round(P.elo_of(away, played_per_team))
    elo_diff = h_elo - a_elo
    # 看好方用融合 1X2 判断（与 predicted_scoreline 口径一致，避免方向矛盾）
    b1x2 = None
    try:
        b1x2 = P.blend_1x2(home, away)
    except Exception:
        pass
    if b1x2:
        fav = home if b1x2[0] >= b1x2[2] else away
    else:
        wp = P.win_prob(home, away, played_per_team)
        fav = home if wp >= 0.5 else away
    fav_zh = _team_zh(fav)
    fav_pct = round(100 * max(b1x2[0], b1x2[2])) if b1x2 else round(100 * max(wp, 1 - wp))
    opp = away if fav == home else home
    opp_zh = _team_zh(opp)
    opp_pct = (round(100 * (b1x2[2] if fav == home else b1x2[0]))
               if b1x2 else 100 - fav_pct)

    points = []
    summary = ""

    # ---- 要点1：FIFA 排名对比 ----
    h_rank, a_rank = h_meta["rank"], a_meta["rank"]
    fav_rank = h_rank if fav == home else a_rank
    opp_rank = a_rank if fav == home else h_rank
    points.append(f"FIFA排名：{fav_zh}第{fav_rank}位 vs {opp_zh}第{opp_rank}位")

    # ---- 要点2：实力推导（Elo→胜率因果链，含阵容修正；胜率用融合值）----
    # 融合 1X2（含赔率）的方向和胜率，保证与预测比分口径一致
    b1x2 = None
    try:
        b1x2 = P.blend_1x2(home, away)
    except Exception:
        pass
    if b1x2:
        # 看好方可能是 home 或 away
        fav_is_home = (fav == home)
        blend_fav_pct = round(100 * (b1x2[0] if fav_is_home else b1x2[2]))
        fav_elo = h_elo if fav == home else a_elo
        opp_elo = a_elo if fav == home else h_elo
        points.append(f"实力分：{fav_zh} {fav_elo} vs {opp_zh} {opp_elo}（差{abs(elo_diff)}）→ 融合胜率{blend_fav_pct}%")
        # 更新 fav_pct 为融合值（供总评用）
        fav_pct = blend_fav_pct
        opp_pct = round(100 * (b1x2[2] if fav_is_home else b1x2[0]))
    else:
        points.append(f"实力分：{fav_zh} {max(h_elo,a_elo)} vs {opp_zh} {min(h_elo,a_elo)}（差{abs(elo_diff)}→胜率{fav_pct}%）")

    # ---- 要点3：市场赔率（隐含概率，强信号）----
    if odds:
        odds_pt = _odds_point(fav, opp, home, away, odds)
        if odds_pt:
            points.append(odds_pt)

    # ---- 要点4：阵容质量（五大联赛占比/年龄/国脚底蕴）----
    if squads:
        squad_pt = _squad_point(fav, opp, squads)
        if squad_pt:
            points.append(squad_pt)

    # ---- 要点4：近期战绩（大赛）----
    if form:
        form_pt = _form_point(fav, opp, form)
        if form_pt:
            points.append(form_pt)

    # ---- 要点5：历史交锋 ----
    if form:
        h2h_pt = _h2h_point(home, away, form)
        if h2h_pt:
            points.append(h2h_pt)

    # ---- 要点6：近期状态（有已踢世界杯数据时）----
    h_form = _form_text(home, played_per_team)
    a_form = _form_text(away, played_per_team)
    fav_form = h_form if fav == home else a_form
    if fav_form:
        points.append(f"近期状态：{fav_zh}{fav_form}")

    # ---- 要点7：情境因素 ----
    situ = []
    if h_meta.get("host") or a_meta.get("host"):
        host_team = home if h_meta.get("host") else away
        situ.append(f"{_team_zh(host_team)}为东道主，享主场加成(+{P.HOST_BONUS})")
    if h_meta["conf"] != a_meta["conf"]:
        # 跨足联对阵，标注
        situ.append(f"跨洲对阵：{fav_zh}({h_meta['conf'] if fav==home else a_meta['conf']}) vs {_team_zh(away if fav==home else home)}({a_meta['conf'] if fav==home else h_meta['conf']})")
    # Elo 变化（已踢后动态调整）
    fav_change = _elo_change_text(fav, played_per_team)
    if fav_change:
        situ.append(fav_change)
    if situ:
        points.append(" · ".join(situ))

    # ---- 总评（基于融合胜率 fav_pct 给出结论）----
    is_draw = (pred_hg == pred_ag)
    score_str = f"{_team_zh(home)} {pred_hg}-{pred_ag} {_team_zh(away)}"
    if is_draw:
        if fav_pct < 45:
            summary = f"两队势均力敌，预测 {score_str}，平局合理，胜负看临场。"
        else:
            summary = f"虽 {fav_zh} 略占优(胜率{fav_pct}%)，但本场预测 {score_str}，或有冷门空间。"
    elif fav_pct < 45:
        summary = f"两队势均力敌，预测 {score_str}，但随时可能翻盘。"
    elif fav_pct < 60:
        summary = f"{fav_zh} 略占优(胜率{fav_pct}%)，预测 {score_str}，但并非稳赢。"
    elif fav_pct < 75:
        summary = f"{fav_zh} 明显占优(胜率{fav_pct}%)，预测 {score_str} 可期。"
    else:
        summary = f"{fav_zh} 实力碾压(胜率{fav_pct}%)，预测 {score_str} 合理拿下。"

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
