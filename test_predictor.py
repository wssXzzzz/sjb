# -*- coding: utf-8 -*-
"""预测引擎核心逻辑的离线单测（不触网）。
运行：python test_predictor.py   或   pytest test_predictor.py
覆盖：Elo 实力模型、小组赛积分守恒、最佳第三名、第三名槽位回溯匹配、蒙特卡洛概率。"""
import random

import predictor as P
import wc_data as W
import live_data as LD


def test_base_elo_monotonic_and_host_bonus():
    """排名越高 Elo 越高；东道主有 +80 加成。"""
    spain = P.base_elo("Spain")        # rank 1
    ghana = P.base_elo("Ghana")        # rank 72
    assert spain > ghana, "排名靠前的队 Elo 应更高"

    # 东道主加成：墨西哥(rank15,host) 相比同公式无加成应高 80
    mexico = P.base_elo("Mexico")
    assert W.TEAMS["Mexico"]["host"] is True
    assert mexico == 2050 - 15 * 18 + 80


def test_group_stage_match_count_and_points_conservation():
    """全部小组赛场次正确，且每场恰好产出 3 分(分胜负)或 2 分(平局)。"""
    rng = random.Random(12345)
    standings, matches, thirds = P.simulate_groups(rng)

    expected = sum(len(W.GROUP_SCHEDULE[g]) for g in W.GROUPS)
    assert len(matches) == expected == 72

    # 每组应有 4 队、第三名记录齐全
    assert len(thirds) == len(W.GROUPS) == 12
    for g, rows in standings.items():
        assert len(rows) == 4
        # 名次 1..4 连续
        assert [r["pos"] for r in rows] == [1, 2, 3, 4]

    # 积分守恒：每组总积分 == Σ(3 if 分胜负 else 2)
    pts_from_matches = {g: 0 for g in W.GROUPS}
    for m in matches:
        pts_from_matches[m["group"]] += 3 if m["hg"] != m["ag"] else 2
    for g, rows in standings.items():
        assert sum(r["pts"] for r in rows) == pts_from_matches[g]


def test_best_thirds_and_slot_assignment_respect_constraints():
    """选出 8 个最佳第三名，并全部分配到槽位，且不违反同组排除约束。"""
    rng = random.Random(2026)
    standings, _, third_teams = P.simulate_groups(rng)
    sindex = {g: {r["team"]: r for r in rows} for g, rows in standings.items()}

    qualified = P.best_thirds(third_teams, sindex)
    assert len(qualified) == 8

    assignment = P.assign_thirds(qualified)
    assert len(assignment) == 8, "8 个槽位应全部分配成功"

    # 约束：分到某槽位的第三名，其所属组不能是该槽位排除的组
    for slot, team in assignment.items():
        excluded_group = W.THIRD_PLACE_SLOTS_EXCLUDE[slot]
        assert W.TEAMS[team]["group"] != excluded_group

    # 8 支队两两不同
    assert len(set(assignment.values())) == 8


def test_monte_carlo_probabilities_are_consistent():
    """蒙特卡洛：每队概率在 0~100，冠军概率之和约等于 100。"""
    probs = P.monte_carlo(n=30)
    assert probs, "应返回非空概率表"
    for team, p in probs.items():
        for k in ("title", "final", "sf", "r16"):
            assert 0 <= p[k] <= 100
        # 进决赛概率不应低于夺冠概率
        assert p["final"] + 1e-9 >= p["title"]

    total_title = sum(p["title"] for p in probs.values())
    assert abs(total_title - 100) < 5, f"冠军概率之和应≈100，实际 {total_title}"


def test_predicted_scoreline_is_deterministic_and_favours_stronger():
    """赛前预测比分：确定性（不依赖 rng/结果），且强队进球不少于弱队。"""
    a = P.predicted_scoreline("Spain", "Ghana")
    b = P.predicted_scoreline("Spain", "Ghana")
    assert a == b, "同一对阵两次预测应一致（无随机、无泄漏）"

    sp_home, gh_away = a
    assert sp_home >= gh_away, "西班牙(rank1)对加纳(rank72)主队进球不应更少"
    # 反过来摆放，强队仍应占优
    gh_home, sp_away = P.predicted_scoreline("Ghana", "Spain")
    assert sp_away >= gh_home

    # 进球数为非负整数
    for g in (sp_home, gh_away, gh_home, sp_away):
        assert isinstance(g, int) and g >= 0


def test_get_prediction_offline_is_deterministic():
    """离线（无 live 数据）时用固定种子，两次预测结果一致。"""
    a = P.get_prediction(live=None)
    b = P.get_prediction(live=None)
    assert a["champion"] == b["champion"]
    assert a["runner_up"] == b["runner_up"]


def test_kickoff_times_converted_to_beijing():
    """开赛时间换算：UTC→北京(+8)、德国本地CEST→北京(+6)，含跨日。"""
    # 19:00Z → 次日 03:00 北京
    assert LD.to_beijing("2026-06-16T19:00:00Z") == ("2026-06-17", "03:00")
    # 带 +00:00 写法也能解析
    assert LD.to_beijing("2026-06-11T19:00:00+00:00") == ("2026-06-12", "03:00")
    # 兜底：德国本地(CEST=UTC+2) 19:00 → 北京 +6 = 次日 01:00
    assert LD.berlin_to_beijing("2026-06-18", "19:00") == ("2026-06-19", "01:00")
    # 非法输入安全降级
    assert LD.to_beijing("") == (None, None)
    assert LD.berlin_to_beijing(None, None) == (None, None)


def test_is_past_beijing():
    """已开赛判断：过去为 True、未来为 False、非法输入按未开赛(False)。"""
    assert LD.is_past_beijing("2000-01-01", "00:00") is True   # 远古
    assert LD.is_past_beijing("2099-12-31", "23:59") is False  # 远未来
    assert LD.is_past_beijing(None, None) is False             # 非法
    assert LD.is_past_beijing("bad", "x") is False


if __name__ == "__main__":
    tests = [v for k, v in sorted(globals().items()) if k.startswith("test_")]
    failed = 0
    for t in tests:
        try:
            t()
            print(f"  ✓ {t.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"  ✗ {t.__name__}: {e}")
    print(f"\n{len(tests) - failed}/{len(tests)} 通过")
    raise SystemExit(1 if failed else 0)
