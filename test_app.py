# -*- coding: utf-8 -*-
"""应用层（视图构建）离线单测，不触网。
覆盖：复盘准确率统计、近期赛程过滤、进行中/待数据 列表。
运行：python test_app.py   或   pytest test_app.py
导入 app 不会触发网络（get_view 仅在 __main__/WARMUP 调用）。"""
import app
import predictor as P
import wc_data as W


def _gm(home, away, status, date, tm, hg=1, ag=0):
    """合成一条 sim['group_matches'] 比赛记录"""
    return {"group": "A", "md": 1, "home": home, "away": away,
            "hg": hg, "ag": ag, "date": date, "time": tm,
            "status": status, "venue": ""}


def _finished(team1, team2, hg, ag):
    """合成一条 live['matches'] 已完赛记录"""
    return {"team1": team1, "team2": team2, "finished": True,
            "is_knockout": False, "hg": hg, "ag": ag}


PAST = ("2000-01-01", "00:00")     # 远古（必已开赛）
FUTURE = ("2099-12-31", "23:59")   # 远未来（必未开赛）


def test_build_accuracy_metrics():
    """复盘指标：精确命中 / 仅胜负对 / 完全未中 三种情形的汇总数值正确。"""
    ph, pa = P.predicted_scoreline("Spain", "Ghana")   # 西班牙强，预测主胜
    assert ph > pa, "前提：西班牙对加纳应预测为主胜"

    live = {"matches": [
        _finished("Spain", "Ghana", ph, pa),         # A 精确命中（含胜负对）
        _finished("Spain", "Ghana", ph + 1, pa),     # B 仅胜负对（仍主胜，比分不同）
        _finished("Spain", "Ghana", 0, ph + 1),      # C 完全未中（客胜）
    ]}
    s = app._build_accuracy(live)["summary"]
    assert s["finished"] == 3
    assert s["exact_correct"] == 1
    assert s["outcome_correct"] == 2
    assert s["points"] == 3 + 1 + 0          # 命中比分+3、仅胜负+1
    assert s["max_points"] == 9
    assert s["outcome_pct"] == round(100 * 2 / 3)
    assert s["exact_pct"] == round(100 * 1 / 3)

    err = (0) + (1) + (ph + abs(pa - (ph + 1)))   # 三场进球绝对误差之和
    assert s["goal_mae"] == round(err / 3, 2)


def test_build_accuracy_skips_unfinished_and_knockout():
    """未完赛 / 淘汰赛 / 无比分 的场不计入复盘。"""
    live = {"matches": [
        {"team1": "Spain", "team2": "Ghana", "finished": False,
         "is_knockout": False, "hg": None, "ag": None},
        {"team1": "Spain", "team2": "Ghana", "finished": True,
         "is_knockout": True, "hg": 2, "ag": 0},
    ]}
    s = app._build_accuracy(live)["summary"]
    assert s["finished"] == 0
    assert s["outcome_pct"] == 0 and s["goal_mae"] == 0


def test_upcoming_filters_past_kickoffs():
    """近期赛程只保留尚未开球的预测场，已过开球的被剔除。"""
    sim = {"group_matches": [
        _gm("Spain", "Ghana", "predicted", *FUTURE),
        _gm("France", "Senegal", "predicted", *PAST),
    ]}
    res = app._build_upcoming(sim, {"matches": []}, None)
    assert len(res) == 1
    assert {res[0]["home"], res[0]["away"]} == {"Spain", "Ghana"}
    assert 99 <= res[0]["home_win"] + res[0]["draw"] + res[0]["away_win"] <= 101


def test_live_now_only_past_predicted():
    """进行中/待数据 只含'已过开球且仍是预测态'的场；未来场与已完赛场都排除。"""
    sim = {"group_matches": [
        _gm("Spain", "Ghana", "predicted", *PAST),       # ✓ 已开球+预测态
        _gm("France", "Senegal", "predicted", *FUTURE),  # ✗ 未来
        _gm("Brazil", "Morocco", "finished", *PAST),     # ✗ 已完赛
    ]}
    res = app._build_live_now(sim)
    assert len(res) == 1
    assert res[0]["home_zh"] == W.TEAMS["Spain"]["zh"]
    assert res[0]["away_zh"] == W.TEAMS["Ghana"]["zh"]


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
