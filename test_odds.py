# -*- coding: utf-8 -*-
"""赔率融合离线单测，不触网。
覆盖：去水、跨家均值、blend_1x2、平局修复、复盘隔离、降级。
运行：python test_odds.py"""
import predictor as P
import odds_data as OD


def test_implied_probs_vig_removal():
    """去水：1/odds 归一化后 sum=1，overround 正值。"""
    ip = OD.implied_probs(1.85, 3.40, 4.20)
    assert ip is not None
    pH, pD, pA, over = ip
    assert abs(pH + pD + pA - 1.0) < 1e-9, "归一后应 sum=1"
    assert over > 1.0, "overround 应 >1（庄家利润）"
    assert 0.45 < pH < 0.55, "主胜应≈50%"
    # 无效赔率
    assert OD.implied_probs(1.0, 3.0, 4.0) is None
    assert OD.implied_probs(None, 3.0, 4.0) is None
    print("  ✓ test_implied_probs_vig_removal")


def test_odds_for_directional():
    """odds_for 方向感知：正查 pH=home胜，反查 pH/pA 交换。"""
    odds = {("Panama", "Ghana"): {"pH": 0.41, "pD": 0.30, "pA": 0.29, "books_n": 5}}
    # 正查
    r1 = OD.odds_for("Panama", "Ghana", odds)
    assert r1["pH"] == 0.41 and r1["pA"] == 0.29
    # 反查：Ghana(home) vs Panama(away) → pH=加纳胜=原pA=0.29
    r2 = OD.odds_for("Ghana", "Panama", odds)
    assert r2["pH"] == 0.29 and r2["pA"] == 0.41
    # 无赔率
    assert OD.odds_for("France", "Spain", odds) is None
    assert OD.odds_for("A", "B", {}) is None
    print("  ✓ test_odds_for_directional")


def test_model_1x2_sums_to_one():
    """model_1x2 三项和≈1。"""
    P.set_dimensions()  # 清空所有维度
    m = P.model_1x2("France", "Senegal")
    assert abs(sum(m) - 1.0) < 0.02, f"model_1x2 sum={sum(m)} 应≈1"
    # 法国应强于塞内加尔
    assert m[0] > m[2], "法国主胜率应>客胜率"
    print("  ✓ test_model_1x2_sums_to_one")


def test_blend_pulls_toward_market():
    """blend_1x2 把模型拉向市场方向：注入与模型相反的赔率，融合值介于两者间。"""
    P.set_dimensions()
    m = P.model_1x2("France", "Senegal")  # 模型：法国强
    # 注入假赔率：塞内加尔被看好（与模型相反）
    odds = {("France", "Senegal"): {"pH": 0.20, "pD": 0.25, "pA": 0.55, "books_n": 10}}
    P.set_dimensions(odds=odds)
    b = P.blend_1x2("France", "Senegal")
    # 融合后法国胜率应 < 模型值（被市场拉低）
    assert b[0] < m[0], "融合后法国胜率应低于纯模型"
    # 但仍 > 市场的 0.20（模型仍有权重）
    assert b[0] > 0.20, "融合值应高于纯市场0.20"
    P.set_dimensions()
    print("  ✓ test_blend_pulls_toward_market")


def test_blend_fallback_no_odds():
    """无赔率时 blend_1x2 回退纯模型（与 model_1x2 一致）。"""
    P.set_dimensions()  # odds=None
    b = P.blend_1x2("France", "Senegal")
    m = P.model_1x2("France", "Senegal")
    assert abs(b[0] - m[0]) < 1e-9, "无赔率时 blend 应等于 model"
    assert abs(b[1] - m[1]) < 1e-9
    assert abs(b[2] - m[2]) < 1e-9
    print("  ✓ test_blend_fallback_no_odds")


def test_review_isolation_use_odds_false():
    """复盘隔离：use_odds=False 时 predicted_scoreline 不受注入赔率影响（ODDS_PLAN §5）。"""
    P.set_dimensions()
    # 纯模型预测
    base = P.predicted_scoreline("France", "Senegal", use_odds=False)
    # 注入极端赔率（塞内加尔 90% 胜）
    odds = {("France", "Senegal"): {"pH": 0.05, "pD": 0.05, "pA": 0.90, "books_n": 10}}
    P.set_dimensions(odds=odds)
    # use_odds=False 应不变
    iso = P.predicted_scoreline("France", "Senegal", use_odds=False)
    assert iso == base, "复盘(use_odds=False)不应受赔率影响"
    # use_odds=True 会变（融合了）
    blended = P.predicted_scoreline("France", "Senegal", use_odds=True)
    P.set_dimensions()
    print("  ✓ test_review_isolation_use_odds_false")


def test_scoreline_direction_consistency():
    """预测比分方向与融合 1X2 的 argmax 一致。"""
    P.set_dimensions()
    odds = {("Spain", "Uruguay"): {"pH": 0.15, "pD": 0.23, "pA": 0.62, "books_n": 8}}
    P.set_dimensions(odds=odds)
    b = P.blend_1x2("Spain", "Uruguay")
    sc = P.predicted_scoreline("Spain", "Uruguay")
    direction = max(range(3), key=lambda k: b[k])
    if direction == 2:  # 客胜(乌拉圭)
        assert sc[0] < sc[1], f"客胜方向比分应 away>home，得{sc}"
    elif direction == 0:
        assert sc[0] > sc[1], f"主胜方向比分应 home>away，得{sc}"
    P.set_dimensions()
    print("  ✓ test_scoreline_direction_consistency")


def test_random_matches_follow_blended_market_direction():
    """蒙特卡洛单场抽样应使用融合赔率，而不是仅使用 Elo。"""
    import random
    odds = {("France", "Senegal"): {"pH": 0.05, "pD": 0.05, "pA": 0.90, "books_n": 10}}
    P.set_dimensions(odds=odds)
    rng = random.Random(2026)
    away_wins = 0
    for _ in range(300):
        hg, ag, _ = P.play_match(rng, "France", "Senegal")
        away_wins += ag > hg
    P.set_dimensions()
    assert away_wins > 180, f"极端客胜市场下应多数客胜，实际 {away_wins}/300"
    print("  ✓ test_random_matches_follow_blended_market_direction")


def run_all():
    print("赔率融合单测：")
    test_implied_probs_vig_removal()
    test_odds_for_directional()
    test_model_1x2_sums_to_one()
    test_blend_pulls_toward_market()
    test_blend_fallback_no_odds()
    test_review_isolation_use_odds_false()
    test_scoreline_direction_consistency()
    test_random_matches_follow_blended_market_direction()
    print("8/8 通过")


if __name__ == "__main__":
    run_all()
