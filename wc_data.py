# -*- coding: utf-8 -*-
"""
2026 FIFA World Cup (USA / Canada / Mexico) — 静态数据
48 队 · 12 组 (A-L) · 小组赛 72 场 · 淘汰赛 32 强

分组依据 2025-12-05 华盛顿抽签；FIFA 排名为 2025-11 排名（抽签用）。
赛程日期/场地依据官方赛程框架，沿用标准配对顺序。
"""

# ---------------------------------------------------------------------------
# 48 支球队
# key = 英文短名；每队含中文、FIFA 三字代码、国旗 emoji、排名、足联、所在组、是否东道主
# ---------------------------------------------------------------------------
TEAMS = {
    # Group A
    "Mexico":            {"zh": "墨西哥",        "code": "MEX", "flag": "🇲🇽", "rank": 15, "conf": "CONCACAF", "group": "A", "host": True},
    "South Korea":       {"zh": "韩国",          "code": "KOR", "flag": "🇰🇷", "rank": 22, "conf": "AFC",      "group": "A", "host": False},
    "Czech Republic":    {"zh": "捷克",          "code": "CZE", "flag": "🇨🇿", "rank": 44, "conf": "UEFA",     "group": "A", "host": False},
    "South Africa":      {"zh": "南非",          "code": "RSA", "flag": "🇿🇦", "rank": 61, "conf": "CAF",      "group": "A", "host": False},
    # Group B
    "Canada":            {"zh": "加拿大",        "code": "CAN", "flag": "🇨🇦", "rank": 27, "conf": "CONCACAF", "group": "B", "host": True},
    "Switzerland":       {"zh": "瑞士",          "code": "SUI", "flag": "🇨🇭", "rank": 17, "conf": "UEFA",     "group": "B", "host": False},
    "Qatar":             {"zh": "卡塔尔",        "code": "QAT", "flag": "🇶🇦", "rank": 51, "conf": "AFC",      "group": "B", "host": False},
    "Bosnia and Herz.":  {"zh": "波黑",          "code": "BIH", "flag": "🇧🇦", "rank": 74, "conf": "UEFA",     "group": "B", "host": False},
    # Group C
    "Brazil":            {"zh": "巴西",          "code": "BRA", "flag": "🇧🇷", "rank": 5,  "conf": "CONMEBOL", "group": "C", "host": False},
    "Morocco":           {"zh": "摩洛哥",        "code": "MAR", "flag": "🇲🇦", "rank": 11, "conf": "CAF",      "group": "C", "host": False},
    "Scotland":          {"zh": "苏格兰",        "code": "SCO", "flag": "🏴󠁧󠁢󠁳󠁣󠁴󠁿", "rank": 36, "conf": "UEFA",     "group": "C", "host": False},
    "Haiti":             {"zh": "海地",          "code": "HAI", "flag": "🇭🇹", "rank": 84, "conf": "CONCACAF", "group": "C", "host": False},
    # Group D
    "United States":     {"zh": "美国",          "code": "USA", "flag": "🇺🇸", "rank": 14, "conf": "CONCACAF", "group": "D", "host": True},
    "Australia":         {"zh": "澳大利亚",      "code": "AUS", "flag": "🇦🇺", "rank": 26, "conf": "AFC",      "group": "D", "host": False},
    "Turkey":            {"zh": "土耳其",        "code": "TUR", "flag": "🇹🇷", "rank": 28, "conf": "UEFA",     "group": "D", "host": False},
    "Paraguay":          {"zh": "巴拉圭",        "code": "PAR", "flag": "🇵🇾", "rank": 39, "conf": "CONMEBOL", "group": "D", "host": False},
    # Group E
    "Germany":           {"zh": "德国",          "code": "GER", "flag": "🇩🇪", "rank": 9,  "conf": "UEFA",     "group": "E", "host": False},
    "Ecuador":           {"zh": "厄瓜多尔",      "code": "ECU", "flag": "🇪🇨", "rank": 23, "conf": "CONMEBOL", "group": "E", "host": False},
    "Ivory Coast":       {"zh": "科特迪瓦",      "code": "CIV", "flag": "🇨🇮", "rank": 42, "conf": "CAF",      "group": "E", "host": False},
    "Curacao":           {"zh": "库拉索",        "code": "CUW", "flag": "🇨🇼", "rank": 82, "conf": "CONCACAF", "group": "E", "host": False},
    # Group F
    "Netherlands":       {"zh": "荷兰",          "code": "NED", "flag": "🇳🇱", "rank": 7,  "conf": "UEFA",     "group": "F", "host": False},
    "Japan":             {"zh": "日本",          "code": "JPN", "flag": "🇯🇵", "rank": 18, "conf": "AFC",      "group": "F", "host": False},
    "Sweden":            {"zh": "瑞典",          "code": "SWE", "flag": "🇸🇪", "rank": 25, "conf": "UEFA",     "group": "F", "host": False},
    "Tunisia":           {"zh": "突尼斯",        "code": "TUN", "flag": "🇹🇳", "rank": 40, "conf": "CAF",      "group": "F", "host": False},
    # Group G
    "Belgium":           {"zh": "比利时",        "code": "BEL", "flag": "🇧🇪", "rank": 8,  "conf": "UEFA",     "group": "G", "host": False},
    "Iran":              {"zh": "伊朗",          "code": "IRN", "flag": "🇮🇷", "rank": 20, "conf": "AFC",      "group": "G", "host": False},
    "Egypt":             {"zh": "埃及",          "code": "EGY", "flag": "🇪🇬", "rank": 34, "conf": "CAF",      "group": "G", "host": False},
    "New Zealand":       {"zh": "新西兰",        "code": "NZL", "flag": "🇳🇿", "rank": 86, "conf": "OFC",      "group": "G", "host": False},
    # Group H
    "Spain":             {"zh": "西班牙",        "code": "ESP", "flag": "🇪🇸", "rank": 1,  "conf": "UEFA",     "group": "H", "host": False},
    "Uruguay":           {"zh": "乌拉圭",        "code": "URU", "flag": "🇺🇾", "rank": 16, "conf": "CONMEBOL", "group": "H", "host": False},
    "Saudi Arabia":      {"zh": "沙特",          "code": "KSA", "flag": "🇸🇦", "rank": 60, "conf": "AFC",      "group": "H", "host": False},
    "Cape Verde":        {"zh": "佛得角",        "code": "CPV", "flag": "🇨🇻", "rank": 68, "conf": "CAF",      "group": "H", "host": False},
    # Group I
    "France":            {"zh": "法国",          "code": "FRA", "flag": "🇫🇷", "rank": 3,  "conf": "UEFA",     "group": "I", "host": False},
    "Norway":            {"zh": "挪威",          "code": "NOR", "flag": "🇳🇴", "rank": 29, "conf": "UEFA",     "group": "I", "host": False},
    "Senegal":           {"zh": "塞内加尔",      "code": "SEN", "flag": "🇸🇳", "rank": 19, "conf": "CAF",      "group": "I", "host": False},
    "Iraq":              {"zh": "伊拉克",        "code": "IRQ", "flag": "🇮🇶", "rank": 58, "conf": "AFC",      "group": "I", "host": False},
    # Group J
    "Argentina":         {"zh": "阿根廷",        "code": "ARG", "flag": "🇦🇷", "rank": 2,  "conf": "CONMEBOL", "group": "J", "host": False},
    "Austria":           {"zh": "奥地利",        "code": "AUT", "flag": "🇦🇹", "rank": 24, "conf": "UEFA",     "group": "J", "host": False},
    "Algeria":           {"zh": "阿尔及利亚",    "code": "ALG", "flag": "🇩🇿", "rank": 35, "conf": "CAF",      "group": "J", "host": False},
    "Jordan":            {"zh": "约旦",          "code": "JOR", "flag": "🇯🇴", "rank": 66, "conf": "AFC",      "group": "J", "host": False},
    # Group K
    "Portugal":          {"zh": "葡萄牙",        "code": "POR", "flag": "🇵🇹", "rank": 6,  "conf": "UEFA",     "group": "K", "host": False},
    "Colombia":          {"zh": "哥伦比亚",      "code": "COL", "flag": "🇨🇴", "rank": 13, "conf": "CONMEBOL", "group": "K", "host": False},
    "Uzbekistan":        {"zh": "乌兹别克斯坦",  "code": "UZB", "flag": "🇺🇿", "rank": 50, "conf": "AFC",      "group": "K", "host": False},
    "DR Congo":          {"zh": "民主刚果",      "code": "COD", "flag": "🇨🇩", "rank": 56, "conf": "CAF",      "group": "K", "host": False},
    # Group L
    "England":           {"zh": "英格兰",        "code": "ENG", "flag": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "rank": 4,  "conf": "UEFA",     "group": "L", "host": False},
    "Croatia":           {"zh": "克罗地亚",      "code": "CRO", "flag": "🇭🇷", "rank": 10, "conf": "UEFA",     "group": "L", "host": False},
    "Panama":            {"zh": "巴拿马",        "code": "PAN", "flag": "🇵🇦", "rank": 30, "conf": "CONCACAF", "group": "L", "host": False},
    "Ghana":             {"zh": "加纳",          "code": "GHA", "flag": "🇬🇭", "rank": 72, "conf": "CAF",      "group": "L", "host": False},
}

# ---------------------------------------------------------------------------
# 12 个小组的球队顺序（按抽签落位 Pot1→2→3→4）
# ---------------------------------------------------------------------------
GROUPS = {
    "A": ["Mexico", "South Korea", "Czech Republic", "South Africa"],
    "B": ["Canada", "Switzerland", "Qatar", "Bosnia and Herz."],
    "C": ["Brazil", "Morocco", "Scotland", "Haiti"],
    "D": ["United States", "Australia", "Turkey", "Paraguay"],
    "E": ["Germany", "Ecuador", "Ivory Coast", "Curacao"],
    "F": ["Netherlands", "Japan", "Sweden", "Tunisia"],
    "G": ["Belgium", "Iran", "Egypt", "New Zealand"],
    "H": ["Spain", "Uruguay", "Saudi Arabia", "Cape Verde"],
    "I": ["France", "Norway", "Senegal", "Iraq"],
    "J": ["Argentina", "Austria", "Algeria", "Jordan"],
    "K": ["Portugal", "Colombia", "Uzbekistan", "DR Congo"],
    "L": ["England", "Croatia", "Panama", "Ghana"],
}

# ---------------------------------------------------------------------------
# 16 座球场
# ---------------------------------------------------------------------------
VENUES = {
    "AZT": "墨西哥城 · 阿兹特克球场",
    "AKR": "瓜达拉哈拉 · 阿克龙球场",
    "MNT": "蒙特雷 · 蒙特雷球场",
    "BMO": "多伦多 · BMO 球场",
    "BCP": "温哥华 · BC 广场球场",
    "SOF": "洛杉矶 · SoFi 球场",
    "LEV": "旧金山湾区 · 李维球场",
    "LUM": "西雅图 · 流明球场",
    "ATL": "亚特兰大 · 梅赛德斯奔驰球场",
    "HOU": "休斯敦 · NRG 球场",
    "DAL": "达拉斯 · AT&T 球场",
    "KCY": "堪萨斯城 · 箭头球场",
    "GIL": "波士顿 · 吉列球场",
    "PHL": "费城 · 林肯金融球场",
    "MIA": "迈阿密 · 硬石球场",
    "MET": "纽约/新泽西 · 大都会生活球场",
}

# ---------------------------------------------------------------------------
# OpenLigaDB 德语队名 → 内部英文名 映射（48 队，API 验证完整）
# ---------------------------------------------------------------------------
DE_TO_EN = {
    "Mexiko": "Mexico", "Südkorea": "South Korea", "Tschechien": "Czech Republic",
    "Südafrika": "South Africa", "Kanada": "Canada", "Schweiz": "Switzerland",
    "Katar": "Qatar", "Bosnien-Herzegowina": "Bosnia and Herz.",
    "Brasilien": "Brazil", "Marokko": "Morocco", "Schottland": "Scotland",
    "Haiti": "Haiti", "USA": "United States", "Australien": "Australia",
    "Türkei": "Turkey", "Paraguay": "Paraguay", "Deutschland": "Germany",
    "Ecuador": "Ecuador", "Elfenbeinküste": "Ivory Coast", "Curaçao": "Curacao",
    "Niederlande": "Netherlands", "Japan": "Japan", "Schweden": "Sweden",
    "Tunesien": "Tunisia", "Belgien": "Belgium", "Iran": "Iran",
    "Ägypten": "Egypt", "Neuseeland": "New Zealand", "Spanien": "Spain",
    "Uruguay": "Uruguay", "Saudi-Arabien": "Saudi Arabia", "Kap Verde": "Cape Verde",
    "Frankreich": "France", "Norwegen": "Norway", "Senegal": "Senegal",
    "Irak": "Iraq", "Argentinien": "Argentina", "Algerien": "Algeria",
    "Österreich": "Austria", "Jordanien": "Jordan", "Portugal": "Portugal",
    "Kolumbien": "Colombia", "Usbekistan": "Uzbekistan", "DR Kongo": "DR Congo",
    "England": "England", "Kroatien": "Croatia", "Panama": "Panama", "Ghana": "Ghana",
}

# ---------------------------------------------------------------------------
# 小组赛赛程兜底表（API 不可达时使用）：72 场，按球队名显式配对
# 配对顺序依据 OpenLigaDB 真实赛程（如 A 组首场 Mexico v South Africa）
# 元素: (轮次, 主队, 客队, 日期, 时间, 球场代码)
# ---------------------------------------------------------------------------
GROUP_SCHEDULE = {
    "A": [
        (1, "Mexico", "South Africa", "2026-06-11", "21:00", "AZT"),
        (1, "South Korea", "Czech Republic", "2026-06-12", "13:00", "AKR"),
        (2, "Mexico", "Czech Republic", "2026-06-18", "19:00", "MNT"),
        (2, "South Africa", "South Korea", "2026-06-18", "16:00", "AKR"),
        (3, "Mexico", "South Korea", "2026-06-24", "21:00", "AZT"),
        (3, "Czech Republic", "South Africa", "2026-06-24", "16:00", "MNT"),
    ],
    "B": [
        (1, "Canada", "Bosnia and Herz.", "2026-06-12", "19:00", "BMO"),
        (1, "Qatar", "Switzerland", "2026-06-13", "21:00", "BCP"),
        (2, "Canada", "Switzerland", "2026-06-18", "19:30", "BMO"),
        (2, "Bosnia and Herz.", "Qatar", "2026-06-19", "13:00", "BCP"),
        (3, "Canada", "Qatar", "2026-06-24", "19:00", "BMO"),
        (3, "Switzerland", "Bosnia and Herz.", "2026-06-24", "13:00", "BCP"),
    ],
    "C": [
        (1, "Brazil", "Morocco", "2026-06-14", "00:00", "MET"),
        (1, "Haiti", "Scotland", "2026-06-14", "03:00", "GIL"),
        (2, "Brazil", "Scotland", "2026-06-19", "16:00", "MET"),
        (2, "Morocco", "Haiti", "2026-06-19", "13:00", "GIL"),
        (3, "Brazil", "Haiti", "2026-06-24", "19:00", "MET"),
        (3, "Scotland", "Morocco", "2026-06-25", "16:00", "GIL"),
    ],
    "D": [
        (1, "United States", "Paraguay", "2026-06-13", "03:00", "SOF"),
        (1, "Australia", "Turkey", "2026-06-14", "06:00", "ATL"),
        (2, "United States", "Turkey", "2026-06-19", "19:30", "SOF"),
        (2, "Paraguay", "Australia", "2026-06-20", "13:00", "ATL"),
        (3, "United States", "Australia", "2026-06-25", "19:30", "SOF"),
        (3, "Turkey", "Paraguay", "2026-06-26", "13:00", "ATL"),
    ],
    "E": [
        (1, "Germany", "Curacao", "2026-06-14", "19:00", "PHL"),
        (1, "Ivory Coast", "Ecuador", "2026-06-15", "01:00", "MIA"),
        (2, "Germany", "Ecuador", "2026-06-20", "19:00", "PHL"),
        (2, "Curacao", "Ivory Coast", "2026-06-21", "13:00", "MIA"),
        (3, "Germany", "Ivory Coast", "2026-06-25", "16:00", "PHL"),
        (3, "Ecuador", "Curacao", "2026-06-26", "13:00", "MIA"),
    ],
    "F": [
        (1, "Netherlands", "Japan", "2026-06-14", "22:00", "HOU"),
        (1, "Sweden", "Tunisia", "2026-06-15", "04:00", "DAL"),
        (2, "Netherlands", "Tunisia", "2026-06-20", "19:00", "HOU"),
        (2, "Japan", "Sweden", "2026-06-21", "16:00", "DAL"),
        (3, "Netherlands", "Sweden", "2026-06-25", "19:00", "HOU"),
        (3, "Japan", "Tunisia", "2026-06-26", "16:00", "DAL"),
    ],
    "G": [
        (1, "Belgium", "Egypt", "2026-06-15", "21:00", "KCY"),
        (1, "Iran", "New Zealand", "2026-06-16", "03:00", "LEV"),
        (2, "Belgium", "New Zealand", "2026-06-21", "19:00", "KCY"),
        (2, "Egypt", "Iran", "2026-06-22", "13:00", "LEV"),
        (3, "Belgium", "Iran", "2026-06-26", "19:00", "KCY"),
        (3, "New Zealand", "Egypt", "2026-06-27", "13:00", "LEV"),
    ],
    "H": [
        (1, "Spain", "Cape Verde", "2026-06-15", "18:00", "LUM"),
        (1, "Saudi Arabia", "Uruguay", "2026-06-16", "00:00", "MNT"),
        (2, "Spain", "Uruguay", "2026-06-21", "16:00", "LUM"),
        (2, "Cape Verde", "Saudi Arabia", "2026-06-22", "16:00", "MNT"),
        (3, "Spain", "Saudi Arabia", "2026-06-26", "16:00", "LUM"),
        (3, "Uruguay", "Cape Verde", "2026-06-27", "16:00", "MNT"),
    ],
    "I": [
        (1, "France", "Senegal", "2026-06-16", "21:00", "MET"),
        (1, "Iraq", "Norway", "2026-06-17", "00:00", "GIL"),
        (2, "France", "Norway", "2026-06-22", "19:00", "MET"),
        (2, "Senegal", "Iraq", "2026-06-22", "13:00", "GIL"),
        (3, "France", "Iraq", "2026-06-26", "19:00", "MET"),
        (3, "Norway", "Senegal", "2026-06-27", "13:00", "GIL"),
    ],
    "J": [
        (1, "Argentina", "Algeria", "2026-06-17", "03:00", "ATL"),
        (1, "Austria", "Jordan", "2026-06-17", "06:00", "MIA"),
        (2, "Argentina", "Jordan", "2026-06-22", "19:30", "ATL"),
        (2, "Austria", "Algeria", "2026-06-23", "13:00", "MIA"),
        (3, "Argentina", "Austria", "2026-06-27", "19:30", "ATL"),
        (3, "Jordan", "Algeria", "2026-06-28", "13:00", "MIA"),
    ],
    "K": [
        (1, "Portugal", "DR Congo", "2026-06-17", "19:00", "HOU"),
        (1, "Uzbekistan", "Colombia", "2026-06-18", "04:00", "AZT"),
        (2, "Portugal", "Colombia", "2026-06-23", "19:00", "HOU"),
        (2, "DR Congo", "Uzbekistan", "2026-06-23", "19:30", "AKR"),
        (3, "Portugal", "Uzbekistan", "2026-06-27", "19:00", "HOU"),
        (3, "Colombia", "DR Congo", "2026-06-28", "16:00", "AKR"),
    ],
    "L": [
        (1, "England", "Croatia", "2026-06-17", "22:00", "DAL"),
        (1, "Ghana", "Panama", "2026-06-18", "01:00", "SOF"),
        (2, "England", "Panama", "2026-06-23", "19:00", "DAL"),
        (2, "Croatia", "Ghana", "2026-06-24", "16:00", "SOF"),
        (3, "England", "Ghana", "2026-06-27", "19:00", "DAL"),
        (3, "Croatia", "Panama", "2026-06-28", "16:00", "SOF"),
    ],
}

# ---------------------------------------------------------------------------
# 淘汰赛签表（32 强）
# 32 强共 16 场，构成完整二叉树。
# seed 表示从哪来：
#   "1A"~"1L"：小组第一；"2A"~"2L"：小组第二；"3?"：8 个最佳第三名之一
# R32 配比：8 场 [小组第一 vs 第三名] + 4 场 [第一 vs 第二] + 4 场 [第二 vs 第二]
#   = 12 第一 + 12 第二 + 8 第三 = 32 队 ✓
# 比赛编号：M1..M16=R32, M17..M24=R16, M25..M28=QF, M29..M30=SF, M31=F
# ---------------------------------------------------------------------------
KNOCKOUT = [
    # Round of 32 —— 8 场 [第一 vs 第三名] (M1-M8)
    {"id": "M1",  "round": "R32", "home": "1A", "away": "3?",  "winner_to": "M17"},
    {"id": "M2",  "round": "R32", "home": "1B", "away": "3?",  "winner_to": "M17"},
    {"id": "M3",  "round": "R32", "home": "1D", "away": "3?",  "winner_to": "M18"},
    {"id": "M4",  "round": "R32", "home": "1E", "away": "3?",  "winner_to": "M18"},
    {"id": "M5",  "round": "R32", "home": "1G", "away": "3?",  "winner_to": "M19"},
    {"id": "M6",  "round": "R32", "home": "1I", "away": "3?",  "winner_to": "M19"},
    {"id": "M7",  "round": "R32", "home": "1K", "away": "3?",  "winner_to": "M20"},
    {"id": "M8",  "round": "R32", "home": "1L", "away": "3?",  "winner_to": "M20"},
    # Round of 32 —— 4 场 [第一 vs 第二] (M9-M12)
    {"id": "M9",  "round": "R32", "home": "1C", "away": "2E",  "winner_to": "M21"},
    {"id": "M10", "round": "R32", "home": "1F", "away": "2H",  "winner_to": "M21"},
    {"id": "M11", "round": "R32", "home": "1H", "away": "2A",  "winner_to": "M22"},
    {"id": "M12", "round": "R32", "home": "1J", "away": "2G",  "winner_to": "M22"},
    # Round of 32 —— 4 场 [第二 vs 第二] (M13-M16)
    {"id": "M13", "round": "R32", "home": "2B", "away": "2D",  "winner_to": "M23"},
    {"id": "M14", "round": "R32", "home": "2C", "away": "2I",  "winner_to": "M23"},
    {"id": "M15", "round": "R32", "home": "2F", "away": "2K",  "winner_to": "M24"},
    {"id": "M16", "round": "R32", "home": "2J", "away": "2L",  "winner_to": "M24"},
    # Round of 16 (M17-M24)
    {"id": "M17", "round": "R16", "home": "W1",  "away": "W2",  "winner_to": "M25"},
    {"id": "M18", "round": "R16", "home": "W3",  "away": "W4",  "winner_to": "M25"},
    {"id": "M19", "round": "R16", "home": "W5",  "away": "W6",  "winner_to": "M26"},
    {"id": "M20", "round": "R16", "home": "W7",  "away": "W8",  "winner_to": "M26"},
    {"id": "M21", "round": "R16", "home": "W9",  "away": "W10", "winner_to": "M27"},
    {"id": "M22", "round": "R16", "home": "W11", "away": "W12", "winner_to": "M27"},
    {"id": "M23", "round": "R16", "home": "W13", "away": "W14", "winner_to": "M28"},
    {"id": "M24", "round": "R16", "home": "W15", "away": "W16", "winner_to": "M28"},
    # Quarter-finals (M25-M28)
    {"id": "M25", "round": "QF", "home": "W17", "away": "W18", "winner_to": "M29"},
    {"id": "M26", "round": "QF", "home": "W19", "away": "W20", "winner_to": "M29"},
    {"id": "M27", "round": "QF", "home": "W21", "away": "W22", "winner_to": "M30"},
    {"id": "M28", "round": "QF", "home": "W23", "away": "W24", "winner_to": "M30"},
    # Semi-finals (M29-M30)
    {"id": "M29", "round": "SF", "home": "W25", "away": "W26", "winner_to": "M31"},
    {"id": "M30", "round": "SF", "home": "W27", "away": "W28", "winner_to": "M31"},
    # Final (M31)
    {"id": "M31", "round": "F", "home": "W29", "away": "W30", "winner_to": None},
]

# ---------------------------------------------------------------------------
# 8 个"第三名"槽位约束
# 规则：第三名不能在 R32 遇到同组对手，故每个 [1X vs 3?] 槽位排除其所属组 X。
# 键 = KNOCKOUT 中含 "3?" 的比赛 id；值 = 该组第一所属小组（被排除）
# ---------------------------------------------------------------------------
THIRD_PLACE_SLOTS_EXCLUDE = {
    "M1": "A", "M2": "B", "M3": "D", "M4": "E",
    "M5": "G", "M6": "I", "M7": "K", "M8": "L",
}

# 淘汰赛各轮日期（官方框架）
KNOCKOUT_DATES = {
    "R32": ("2026-06-29", "2026-07-04"),
    "R16": ("2026-07-05", "2026-07-09"),
    "QF":  ("2026-07-10", "2026-07-12"),
    "SF":  ("2026-07-14", "2026-07-15"),
    "F":   ("2026-07-19", "2026-07-19"),
}

ROUND_NAMES = {
    "R32": "三十二强赛",
    "R16": "十六强赛",
    "QF":  "四分之一决赛",
    "SF":  "半决赛",
    "F":   "决赛",
}

# 东道主
HOSTS = ["Mexico", "Canada", "United States"]


def team_meta(name):
    """返回球队展示信息字典"""
    return TEAMS[name]


def all_group_names():
    return list(GROUPS.keys())


def find_group(t1, t2):
    """根据两支球队反查所属小组字母；找不到返回 None"""
    for g, teams in GROUPS.items():
        if t1 in teams and t2 in teams:
            return g
    return None


def find_matchday(g, t1, t2):
    """在兜底 GROUP_SCHEDULE 里查 (g 组中 t1 v t2) 的轮次；找不到返回 None"""
    for (md, a, b, _d, _t, _v) in GROUP_SCHEDULE.get(g, []):
        if {a, b} == {t1, t2}:
            return md
    return None
