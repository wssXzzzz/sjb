# -*- coding: utf-8 -*-
"""
2026 世界杯比分预测引擎
- 固定随机种子 → 确定性预测（刷新结果一致，体现权威性）
- 实力模型：FIFA 排名 → Elo → 泊松进球采样
- 小组赛积分 → 12 名第三名取前 8 → 二分匹配分配到 R32 槽位
- 完整淘汰赛推进至决赛
- 蒙特卡洛 2000 次 → 夺冠/进决赛/四强/十六强概率
"""
import math
import random
from collections import defaultdict
import wc_data as W


# ---------------------------------------------------------------------------
# 实力模型
# ---------------------------------------------------------------------------
# 动态 Elo 缓存：{team: (elo_value, played_key)}，played_key 用于失效判断
_elo_cache = {}


# 基础实力标定：斜率不宜过陡，否则强弱差被放大、几乎场场一边倒、不出平局。
# ×8 使强队仍明显占优(西班牙vs加纳≈95%)，但中上游对话回到合理区间(法国vs塞内加尔≈66%)，
# 最可能比分里自然出现约 20% 的平局，贴近真实小组赛平局率。
ELO_BASE = 2050
ELO_SLOPE = 8
HOST_BONUS = 60


def base_elo(team):
    """FIFA 排名位次 → 基础 Elo 分（rank1≈2042，rank86≈1362；东道主另加）"""
    rank = W.TEAMS[team]["rank"]
    elo = ELO_BASE - rank * ELO_SLOPE
    if W.TEAMS[team].get("host"):
        elo += HOST_BONUS  # 东道主主场加成
    return elo


def _expected_gd(team, opp):
    """基于 Elo 的期望净胜球（用于吸收真实表现）"""
    diff = base_elo(team) - base_elo(opp)
    # 每 100 Elo 差约 0.55 球净胜
    return diff / 180.0


def live_elo(team, played_per_team=None):
    """动态实力：基础 Elo + 已踢真实表现的修正。
    played_per_team: {team: [match,...]} 来自 live_data.played_games_per_team
    每场修正 Δ = K × (实际净胜 − 期望净胜)，K=16"""
    if not played_per_team or team not in played_per_team:
        return base_elo(team)

    games = played_per_team[team]
    key = (len(games), id(games[-1]) if games else 0)
    if team in _elo_cache and _elo_cache[team][1] == key:
        return _elo_cache[team][0]

    elo = base_elo(team)
    K = 16
    for m in games:
        is_home = (m["team1"] == team)
        opp = m["team2"] if is_home else m["team1"]
        hg, ag = m["hg"], m["ag"]
        actual_gd = (hg - ag) if is_home else (ag - hg)
        exp_gd = _expected_gd(team, opp)
        elo += K * (actual_gd - exp_gd)
    _elo_cache[team] = (elo, key)
    return elo


def elo_of(team, played_per_team=None):
    """对外统一入口：有动态数据用动态 Elo，否则用基础 Elo"""
    return live_elo(team, played_per_team)


def win_prob(a, b, played_per_team=None):
    """A 队胜率期望 (0~1)"""
    ea = 1.0 / (1.0 + 10 ** ((elo_of(b, played_per_team) - elo_of(a, played_per_team)) / 400.0))
    return ea


def _poisson_pmf(k, lam):
    """泊松概率质量 P(X=k)"""
    return math.exp(-lam) * lam ** k / math.factorial(k)


def _likely_scoreline(ea, total, max_goals=8):
    """最可能比分 = 双方独立泊松联合分布中概率最高的那个比分。
    用「众数(mode≈⌊λ⌋)」而非「期望四舍五入」——后者会把强队进球数高估、
    抹掉本应出现的 1-1 平局。实力接近(ea≈0.5)时自然给出平局，符合真实平局率。"""
    lam_h = max(0.15, total * ea)
    lam_a = max(0.15, total * (1 - ea))
    ph = [_poisson_pmf(i, lam_h) for i in range(max_goals + 1)]
    pa = [_poisson_pmf(j, lam_a) for j in range(max_goals + 1)]
    best_p, best = -1.0, (0, 0)
    for i in range(max_goals + 1):
        for j in range(max_goals + 1):
            p = ph[i] * pa[j]
            if p > best_p:
                best_p, best = p, (i, j)
    return best


def predicted_scoreline(home, away, played_per_team=None):
    """最可能比分（整数）：取双方泊松联合分布的众数比分。
    - played_per_team=None（默认）：仅用赛前基础 Elo。复盘准确率用此口径，
      刻意不看赛事内结果 → 无信息泄漏。
    - 传入 played_per_team：用动态 Elo（含已踢真实表现），用于首页未踢比赛展示。
    返回 (home_goals, away_goals)。"""
    ea = win_prob(home, away, played_per_team)
    return _likely_scoreline(ea, total=2.7)   # 2.7：小组赛场均总进球，与 play_match 一致


def sample_goals(rng, lam):
    """泊松采样进球数"""
    # Knuth 算法
    L = math.exp(-lam)
    k, p = 0, 1.0
    while True:
        k += 1
        p *= rng.random()
        if p <= L:
            return k - 1


def play_match(rng, home, away, ko=False, played_per_team=None, deterministic=False):
    """模拟一场比赛，返回 (主队进球, 客队进球, 点球胜者)
    ko=True 时淘汰赛平局需加时/点球决出胜者。
    deterministic=True：输出最可能比分（期望进球四舍五入），与 predicted_scoreline
    口径一致，用于"单一确定性预测场景"（首页/小组赛/签表统一展示）；平局淘汰赛
    由实力较强一方晋级。deterministic=False：泊松随机采样，用于蒙特卡洛概率统计。"""
    ea = win_prob(home, away, played_per_team)
    # 场均进球：小组赛略高，淘汰赛更保守
    total = 2.2 if ko else 2.7
    if deterministic:
        # 最可能比分（众数），与 predicted_scoreline 同口径
        ga, gb = _likely_scoreline(ea, total)
    else:
        # 按 Elo 期望瓜分总进球后泊松随机采样
        lam_a = max(0.15, total * ea)
        lam_b = max(0.15, total * (1 - ea))
        ga, gb = sample_goals(rng, lam_a), sample_goals(rng, lam_b)

    pen_winner = None
    if ko and ga == gb:
        if deterministic:
            # 确定性：实力较强一方晋级（不引入随机加时/点球）
            pen_winner = home if ea >= 0.5 else away
        else:
            # 加时赛：再各加 30 分钟强度的泊松
            ot_total = 0.8
            lam_a_ot = max(0.05, ot_total * ea)
            lam_b_ot = max(0.05, ot_total * (1 - ea))
            ga += sample_goals(rng, lam_a_ot)
            gb += sample_goals(rng, lam_b_ot)
            # 仍平 → 点球（按 Elo 加权掷硬币，稍带随机）
            if ga == gb:
                p_home = 0.5 + (elo_of(home, played_per_team) - elo_of(away, played_per_team)) / 800.0
                p_home = max(0.35, min(0.65, p_home))
                pen_winner = home if rng.random() < p_home else away
    return ga, gb, pen_winner


def match_winner(ga, gb, pen_winner, home, away):
    """返回 (胜者, 负者)；平局时用 pen_winner"""
    if ga > gb:
        return home, away
    if gb > ga:
        return away, home
    return (pen_winner, away if pen_winner == home else home)


# ---------------------------------------------------------------------------
# 小组赛
# ---------------------------------------------------------------------------
def simulate_groups(rng, played_per_team=None, real_index=None, deterministic=False):
    """模拟全部 72 场小组赛。
    - real_index: {frozenset(t1,t2): (hg,ag)} 已踢真实比分；命中则用真实
    - played_per_team: 动态 Elo 依据
    - deterministic: True 时未踢场用最可能比分（确定性，前端统一展示用）
    返回:
      standings, all_matches(含 status 标记), third_teams
    """
    real_index = real_index or {}
    group_results = {g: {t: {"pts": 0, "gd": 0, "gf": 0, "w": 0, "d": 0, "l": 0}
                         for t in teams} for g, teams in W.GROUPS.items()}
    all_matches = []

    for g, teams in W.GROUPS.items():
        for (md, home, away, date, tm, venue) in W.GROUP_SCHEDULE[g]:
            key = frozenset((home, away))
            if key in real_index:
                # 已踢：用真实比分
                ga, gb = real_index[key]
                status = "finished"
            else:
                # 未踢：模型预测
                ga, gb, _ = play_match(rng, home, away, ko=False,
                                       played_per_team=played_per_team,
                                       deterministic=deterministic)
                status = "predicted"
            all_matches.append({
                "group": g, "md": md, "home": home, "away": away,
                "hg": ga, "ag": gb, "date": date, "time": tm,
                "venue": W.VENUES.get(venue, ""), "status": status,
            })
            hr = group_results[g][home]
            ar = group_results[g][away]
            hr["gf"] += ga; ar["gf"] += gb
            hr["gd"] += ga - gb; ar["gd"] += gb - ga
            if ga > gb:
                hr["pts"] += 3; hr["w"] += 1; ar["l"] += 1
            elif gb > ga:
                ar["pts"] += 3; ar["w"] += 1; hr["l"] += 1
            else:
                hr["pts"] += 1; ar["pts"] += 1; hr["d"] += 1; ar["d"] += 1

    # 排序：积分 → 净胜球 → 进球 → FIFA 排名（排名数值小者前）
    standings = {}
    third_teams = {}
    for g, res in group_results.items():
        ordered = sorted(
            res.items(),
            key=lambda kv: (-kv[1]["pts"], -kv[1]["gd"], -kv[1]["gf"],
                            W.TEAMS[kv[0]]["rank"])
        )
        standings[g] = []
        for pos, (team, r) in enumerate(ordered, 1):
            standings[g].append({
                "team": team, "pos": pos, "pts": r["pts"], "gd": r["gd"],
                "gf": r["gf"], "w": r["w"], "d": r["d"], "l": r["l"],
                "rank": W.TEAMS[team]["rank"],
            })
        third_teams[g] = ordered[2][0]  # 第三名球队
    return standings, all_matches, third_teams


# ---------------------------------------------------------------------------
# 最佳第三名 + 二分匹配分配到 R32 槽位
# ---------------------------------------------------------------------------
def best_thirds(third_teams, standings_index):
    """从 12 名第三名中选 8 名最佳。
    standings_index: {组: {队: 积分/净胜球/进球/排名 dict}}"""
    thirds = []
    for g, team in third_teams.items():
        s = standings_index[g][team]
        thirds.append({
            "group": g, "team": team,
            "pts": s["pts"], "gd": s["gd"], "gf": s["gf"],
            "rank": W.TEAMS[team]["rank"],
        })
    thirds.sort(key=lambda x: (-x["pts"], -x["gd"], -x["gf"], x["rank"]))
    return thirds[:8]


def assign_thirds(qualified_thirds):
    """把 8 名第三名分配到 8 个 R32 槽位（M1-M8 中含 3? 者）。
    约束：第三名不能遇到同组小组第一（即不能分配到排除其本组的槽位）。
    用带回溯的最大匹配求解。"""
    slots = list(W.THIRD_PLACE_SLOTS_EXCLUDE.keys())  # M1..M8
    exclude = W.THIRD_PLACE_SLOTS_EXCLUDE
    # 每个 slot 可接受的小组 = 全部 12 组 - 其排除组（但要排除该 slot 已确定的同组第一）
    # 已在 THIRD_PLACE_SLOTS_EXCLUDE 中给出排除组
    allowed = {s: set(W.GROUPS.keys()) - {exclude[s]} for s in slots}

    # 回溯匹配
    assignment = {}
    used = set()

    def backtrack(i):
        if i == len(slots):
            return True
        slot = slots[i]
        for t in qualified_thirds:
            key = t["group"]
            if key in used:
                continue
            if key in allowed[slot]:
                assignment[slot] = t["team"]
                used.add(key)
                if backtrack(i + 1):
                    return True
                used.discard(key)
                del assignment[slot]
        return False

    ok = backtrack(0)
    return assignment if ok else {}


# ---------------------------------------------------------------------------
# 淘汰赛推进
# ---------------------------------------------------------------------------
def resolve_seed(seed, group_winners, group_runners, third_assignment, winners):
    """把签表里的 seed 字符串解析为具体球队"""
    if seed.startswith("1"):   # 小组第一 1A
        return group_winners[seed[1:]]
    if seed.startswith("2"):   # 小组第二 2A
        return group_runners[seed[1:]]
    if seed.startswith("3?"):  # 第三名（不可能出现在 M1-M8 之外）
        return None
    if seed.startswith("W"):   # 某场胜者 W3
        return winners.get(seed[1:])
    return None


def simulate_knockout(rng, standings, third_assignment, played_per_team=None, deterministic=False):
    """推进完整淘汰赛，返回 (matches_list, champion)
    matches_list: 每场比赛 {id, round, home, away, hg, ag, pen, winner, date, venue}
    deterministic: True 时用最可能比分、平局由强者晋级（确定性签表）。
    """
    # 抽取每组 1/2 名
    group_winners = {g: s[0]["team"] for g, s in standings.items()}
    group_runners = {g: s[1]["team"] for g, s in standings.items()}

    winners = {}  # "1".."31" → 球队
    results = []

    for m in W.KNOCKOUT:
        # 计算日期：取该轮日期区间的首日 + 比赛在该轮的序号偏移
        round_dates = W.KNOCKOUT_DATES[m["round"]]
        # 简化：用 round 首日，决赛用末日
        if m["round"] == "F":
            date = round_dates[1]
        else:
            date = round_dates[0]

        # 解析对阵
        home_seed = m["home"]
        away_seed = m["away"]
        home = resolve_seed(home_seed, group_winners, group_runners, third_assignment, winners)
        away = resolve_seed(away_seed, group_winners, group_runners, third_assignment, winners)

        # 第三名槽位
        if home_seed.startswith("3?"):
            home = third_assignment.get(m["id"])
        if away_seed.startswith("3?"):
            away = third_assignment.get(m["id"])

        # 所有淘汰赛都需决出胜者（平局加时/点球）
        ga, gb, pen_winner = play_match(rng, home, away, ko=True,
                                        played_per_team=played_per_team,
                                        deterministic=deterministic)
        winner, loser = match_winner(ga, gb, pen_winner, home, away)

        winners[m["id"][1:]] = winner  # "M17" → "17"

        results.append({
            "id": m["id"], "round": m["round"], "home": home, "away": away,
            "hg": ga, "ag": gb, "pen": pen_winner, "winner": winner, "loser": loser,
            "date": date,
        })

    champion = winners["31"]
    return results, champion


# ---------------------------------------------------------------------------
# 一次完整模拟
# ---------------------------------------------------------------------------
def simulate_tournament(rng, played_per_team=None, real_index=None, deterministic=False):
    """完整模拟一届赛事，返回 dict。
    - played_per_team: 已踢真实比赛（动态 Elo 依据）
    - real_index: 已踢真实比分（命中用真实，否则预测）
    - deterministic: True 时整届用最可能比分推演（首页/小组赛/签表一致的单一预测场景）
    """
    standings, group_matches, third_teams = simulate_groups(
        rng, played_per_team=played_per_team, real_index=real_index,
        deterministic=deterministic)

    # 建立 standings 索引便于查第三名
    sindex = {}
    for g, rows in standings.items():
        sindex[g] = {r["team"]: r for r in rows}

    qualified_thirds = best_thirds(third_teams, sindex)
    third_assignment = assign_thirds(qualified_thirds)

    ko_results, champion = simulate_knockout(
        rng, standings, third_assignment, played_per_team=played_per_team,
        deterministic=deterministic)

    # 决赛两队 & 半决赛败者（用于亚军/四强）
    final = next(r for r in ko_results if r["round"] == "F")
    sf = [r for r in ko_results if r["round"] == "SF"]

    return {
        "standings": standings,
        "group_matches": group_matches,
        "qualified_thirds": qualified_thirds,
        "third_assignment": third_assignment,
        "ko_results": ko_results,
        "champion": champion,
        "runner_up": final["loser"],
        "semifinalists": [s["loser"] for s in sf],
        "finalists": [final["home"], final["away"]],
    }


# ---------------------------------------------------------------------------
# 蒙特卡洛概率统计
# ---------------------------------------------------------------------------
def monte_carlo(n=1000, base_seed=20260616, played_per_team=None, real_index=None):
    """跑 n 次完整模拟，统计各队夺冠/进决赛/四强/十六强概率。
    主预测用固定 seed；蒙特卡洛用不同 seed 独立采样。
    已踢场次始终用真实比分（确定性）；未踢场次随机。"""
    counts = defaultdict(lambda: {"title": 0, "final": 0, "sf": 0, "r16": 0})
    for i in range(n):
        rng = random.Random(base_seed + i + 1)
        sim = simulate_tournament(rng, played_per_team=played_per_team, real_index=real_index)
        counts[sim["champion"]]["title"] += 1
        for t in sim["finalists"]:
            counts[t]["final"] += 1
        for t in sim["semifinalists"]:
            counts[t]["sf"] += 1
        # 十六强 = 进入 R32 的 32 队（小组前2 + 8第三名）
        r16 = set()
        for g, rows in sim["standings"].items():
            for r in rows[:2]:
                r16.add(r["team"])
        for qt in sim["qualified_thirds"]:
            r16.add(qt["team"])
        for t in r16:
            counts[t]["r16"] += 1

    probs = {}
    for team, c in counts.items():
        probs[team] = {
            "title": round(100 * c["title"] / n, 1),
            "final": round(100 * c["final"] / n, 1),
            "sf": round(100 * c["sf"] / n, 1),
            "r16": round(100 * c["r16"] / n, 1),
        }
    return probs


# ---------------------------------------------------------------------------
# 对外主入口：实时混合预测
# ---------------------------------------------------------------------------
MASTER_SEED = 20260616


def get_prediction(live=None):
    """生成"单一确定性预测场景"：未踢场一律用最可能比分推演，
    保证首页/小组赛/积分榜/签表展示的同一场比分完全一致。
    live 为 live_data.fetch_matches() 的返回；为空或离线时退化为纯预测。
    （夺冠等概率另由 get_probs 的蒙特卡洛随机统计给出，两者用途不同。）"""
    played_per_team = None
    real_index = {}
    if live and live.get("source") == "online" and live.get("matches"):
        import live_data as LD
        played_per_team = LD.played_games_per_team(live)
        real_index = LD.real_results_index(live)
    rng = random.Random(MASTER_SEED)
    return simulate_tournament(rng, played_per_team=played_per_team,
                               real_index=real_index, deterministic=True)


def get_probs(live=None, n=1000):
    """蒙特卡洛概率（基于动态 Elo）"""
    played_per_team = None
    real_index = {}
    if live and live.get("source") == "online" and live.get("matches"):
        import live_data as LD
        played_per_team = LD.played_games_per_team(live)
        real_index = LD.real_results_index(live)
    return monte_carlo(n=n, played_per_team=played_per_team, real_index=real_index)
