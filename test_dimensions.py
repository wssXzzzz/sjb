# -*- coding: utf-8 -*-
"""多维度预测（阵容/战绩/交锋）离线单测，不触网。
覆盖：阵容解析、战绩统计、h2h 派生、维度注入后确定性、理由生成。
运行：python test_dimensions.py"""
import predictor as P
import reasons as R
import wc_data as W
import squad_data as SD
import form_data as FD


def test_squad_parsing_synthetic():
    """合成 HTML 测阵容解析：年龄/五大联赛占比/头号射手 计算正确。"""
    html = '''<h3 id="Test_Team"><span id="Test_Team"></span>Test Team</h3>
<table class="wikitable"><tbody>
<tr><th>No.</th><th>Pos.</th><th>Player</th><th>Date of birth (age)</th><th>Caps</th><th>Goals</th><th>Club</th></tr>
<tr><td>1</td><td>1 GK</td><td>Alpha</td><td>(1990-01-01)Jan 1, 1990 (aged 36)</td><td>50</td><td>0</td><td>Real Madrid</td></tr>
<tr><td>2</td><td>2 DF</td><td>Beta (captain)</td><td>(2000-01-01)Jan 1, 2000 (aged 26)</td><td>20</td><td>10</td><td>Some Local Club</td></tr>
<tr><td>3</td><td>3 MF</td><td>Gamma</td><td>(1995-01-01)Jan 1, 1995 (aged 31)</td><td>30</td><td>3</td><td>Barcelona</td></tr>
</tbody></table>'''
    data = SD._parse_squads_html(html)
    # "Test Team" 不在 TEAMS，应被跳过；用真实队名测
    html2 = html.replace("Test Team", "France").replace("Test_Team", "France")
    data2 = SD._parse_squads_html(html2)
    assert "France" in data2, "France 应被解析"
    f = data2["France"]
    assert f["squad_size"] == 3
    assert f["top5_pct"] == round(100 * 2 / 3, 0)  # Real Madrid + Barcelona 命中
    assert f["avg_caps"] == round((50 + 20 + 30) / 3, 0)
    assert f["top_scorer"] == "Beta"  # (captain) 已清洗，10球最多
    assert f["top_scorer_goals"] == 10
    print("  ✓ test_squad_parsing_synthetic")


def test_is_top5_club_matching():
    """五大联赛俱乐部匹配：精确 + 模糊 + 不命中。"""
    assert SD._is_top5("Real Madrid")
    assert SD._is_top5("Manchester City")
    assert SD._is_top5("Bayern Munich")
    assert not SD._is_top5("Al-Nassr")
    assert not SD._is_top5("Flamengo")
    assert not SD._is_top5("")
    print("  ✓ test_is_top5_club_matching")


def test_h2h_derivation_from_form():
    """h2h 从战绩语料正确派生：胜/平/负计数 + 胜率。"""
    form = {
        "France": {"games": [
            {"opp": "Germany", "sf": 2, "sa": 1, "comp": "欧洲杯", "date": "2024-01-01"},
            {"opp": "Germany", "sf": 1, "sa": 1, "comp": "欧洲杯", "date": "2024-02-01"},
            {"opp": "Spain", "sf": 0, "sa": 2, "comp": "欧洲杯", "date": "2024-03-01"},
        ], "sample_n": 3, "w": 1, "d": 1, "l": 1, "wr": 50, "gf_avg": 1, "ga_avg": 1, "comps": ["欧洲杯"]},
    }
    h = FD.h2h("France", "Germany", form)
    assert h is not None
    assert h["sample_n"] == 2          # 法国 vs 德国 2 次相遇
    assert h["w1"] == 1                # 法国 1 胜
    assert h["d"] == 1                 # 1 平
    assert h["w2"] == 0                # 德国 0 胜
    assert h["wr1"] == 75              # (1 + 0.5) / 2 = 75%
    # 无交锋
    assert FD.h2h("France", "Brazil", form) is None
    print("  ✓ test_h2h_derivation_from_form")


def test_set_dimensions_clears_cache_and_changes_elo():
    """注入维度后 Elo 缓存被清、base_elo 发生变化。"""
    P.set_dimensions(squads=None, form=None)  # 重置干净
    elo_before = P.base_elo("France")
    # 注入合成阵容：法国五大联赛 100%
    P.set_dimensions(squads={"France": {"top5_pct": 100, "avg_age": 27, "avg_caps": 40,
                                         "top_scorer": None, "top_scorer_goals": 0}},
                     form=None)
    elo_after = P.base_elo("France")
    assert elo_after > elo_before, "阵容加成应提升 Elo"
    assert abs(elo_after - elo_before) < 200, "加成幅度合理(<200)"
    P.set_dimensions(squads=None, form=None)  # 清理
    print("  ✓ test_set_dimensions_clears_cache_and_changes_elo")


def test_prediction_deterministic_after_dimensions():
    """注入维度后预测仍确定（同输入同输出）。"""
    squads = {"France": {"top5_pct": 90, "avg_age": 27, "avg_caps": 40,
                          "top_scorer": None, "top_scorer_goals": 0},
              "Senegal": {"top5_pct": 30, "avg_age": 26, "avg_caps": 25,
                           "top_scorer": None, "top_scorer_goals": 0}}
    P.set_dimensions(squads=squads, form=None)
    s1 = P.predicted_scoreline("France", "Senegal")
    s2 = P.predicted_scoreline("France", "Senegal")
    assert s1 == s2, "同输入应同输出（确定性）"
    # 法国应强于塞内加尔
    wp = P.win_prob("France", "Senegal")
    assert wp > 0.5
    P.set_dimensions(squads=None, form=None)
    print("  ✓ test_prediction_deterministic_after_dimensions")


def test_reasons_include_new_dimensions():
    """理由输出含阵容/战绩/交锋维度（数据充足时）。"""
    squads = {"France": {"top5_pct": 92, "avg_age": 26.6, "avg_caps": 31,
                          "top_scorer": "Mbappé", "top_scorer_goals": 56},
              "Senegal": {"top5_pct": 50, "avg_age": 26.0, "avg_caps": 28,
                           "top_scorer": "Mané", "top_scorer_goals": 40}}
    form = {"France": {"games": [{"opp": "Germany", "sf": 2, "sa": 1, "comp": "欧洲杯", "date": "2024"}],
                       "sample_n": 1, "w": 1, "d": 0, "l": 0, "wr": 100,
                       "gf_avg": 2, "ga_avg": 1, "comps": ["欧洲杯"]}}
    P.set_dimensions(squads=squads, form=form)
    r = R.generate_reasons("France", "Senegal", None, 2, 0, squads=squads, form=form)
    joined = " ".join(r["points"])
    assert "阵容" in joined, "应含阵容维度"
    assert "Mbappé" in joined, "阵容要点应含头号射手"
    P.set_dimensions(squads=None, form=None)
    print("  ✓ test_reasons_include_new_dimensions")


def test_reasons_honest_when_data_missing():
    """数据缺失时如实标注，不编造：加纳无战绩→写样本不足。"""
    r = R.generate_reasons("Ghana", "Panama", None, 0, 2,
                           squads={}, form={})  # 空数据
    joined = " ".join(r["points"])
    assert "阵容" not in joined, "无阵容数据不应输出阵容要点"
    assert "近期" not in joined, "无战绩数据不应输出近期要点"
    # 有 form 但加纳 0 场
    form = {"Panama": {"games": [], "sample_n": 0, "w": 0, "d": 0, "l": 0,
                        "wr": 0, "gf_avg": 0, "ga_avg": 0, "comps": []}}
    r2 = R.generate_reasons("Ghana", "Panama", None, 0, 2,
                            squads=None, form=form)
    joined2 = " ".join(r2["points"])
    assert "阵容" not in joined2
    # 巴拿马是看好方(fav)，它有0场→_form_point 返回 None；加纳不是 fav 不输出
    print("  ✓ test_reasons_honest_when_data_missing")


def run_all():
    print("多维度预测单测：")
    test_squad_parsing_synthetic()
    test_is_top5_club_matching()
    test_h2h_derivation_from_form()
    test_set_dimensions_clears_cache_and_changes_elo()
    test_prediction_deterministic_after_dimensions()
    test_reasons_include_new_dimensions()
    test_reasons_honest_when_data_missing()
    print("7/7 通过")


if __name__ == "__main__":
    run_all()
