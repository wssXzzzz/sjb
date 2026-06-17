# ⚽ 2026 世界杯 · 实时比分预测

参考 [shuangseqiu666](https://github.com/wssXzzzz/shuangseqiu666) 的 **iOS 26 液态玻璃 (Liquid Glass)** 设计风格，做一个 **2026 美加墨世界杯（48 队）** 的**实时混合预测**应用。

## ✨ 核心理念：用可信度建立信任

- **首页只放近期比赛预测 + 理由** — 明天就能验证，可信度高
- **冠军/16强/8强等远期预测单独成页** — 诚实承认"越远越不确定"
- 每场预测附**多维数据支撑的理由**（排名、赔率、阵容、战绩、交锋），不靠瞎猜
- **赔率不骗人**：市场赔率作为最强信号融入，修正纯模型的偏差

## 🎯 五维预测信号

每场未踢比赛的预测理由来自 5 个可查证维度：

| 维度 | 数据源 | 在模型里的作用 |
|---|---|---|
| **🏟 市场赔率** | The Odds API（38-41 家博彩公司均值） | **最强信号**，去水后融合，权重 0.7（分歧时自适应到 0.85） |
| **🏆 FIFA 排名 → Elo** | 内置（2025-11 排名） | 基础实力 `Elo = 2050 − rank×8`（东道主+60） |
| **👥 阵容质量** | Wikipedia squads 页（48 队 26 人） | 五大联赛占比 + 年龄曲线 → Elo 修正（替代无法免费获取的€身价） |
| **📊 近期战绩** | OpenLigaDB 大赛（欧洲杯/美洲杯/欧国联/世界杯） | 胜率/进球展示（诚实标注 CAF/AFC 队可能样本不足） |
| **⚔️ 历史交锋** | 从近期战绩语料派生 | 对局微调 ±0.10（样本≥3 才启用） |

> 已踢完的比赛直接用真实赛果（绿色标记）；未踢的用融合模型预测（蓝色标记）。

## 🎨 五个玻璃视图

### 🔮 预测（首页）
- **下一场大卡**：开球时间 + 预测比分 + 胜率条 + **完整预测理由**（5 维度 + 一句总评）
- **近期赛程预测**：所有未踢比赛按日期分组，每场**点击展开**看预测理由
- 已踢场绿色（真实赛果）、未踢场蓝色（预测）

### 📋 小组赛
12 组，每场标绿(真实)/蓝(预测)，含积分榜（前2绿色晋级、第3橙色争最佳）

### 🔍 复盘（准确率）
诚实的赛前预测复盘 —— 用**赛前纯模型**（仅 FIFA 排名 Elo + 阵容，**不含赔率、不看任何结果**）逐场预测，对比真实赛果：胜负判对率、比分命中、竞猜打分。**复盘刻意不用赔率融合**（防口径污染，ODDS_PLAN §5）。

### ⚔️ 淘汰赛
32强→决赛完整签表，每场国旗+比分，决赛金色高亮

### 🏆 夺冠
远期预测专属页：预测冠军/亚军 + 四强/八强/十六强（热力色块）+ 8 个最佳第三名 + 夺冠概率 Top12 + ECharts

## 🔌 数据源

| 源 | 用途 | 免费/key |
|---|---|---|
| **[OpenLigaDB](https://www.openligadb.de/)** | 真实赛果 + 近期战绩 + 开球时间 | 免费，无 key |
| **[The Odds API](https://the-odds-api.com/)** | 市场赔率（38-41 家均值） | 免费 500 请求/月，需 key |
| **Wikipedia** squads 页 | 阵容质量（年龄/五大联赛占比/国脚） | 免费，无 key |

赔率缓存 2 小时（控配额），赛果 5 分钟缓存。`/api/refresh` 强制刷新。

## 🧠 预测算法

| 环节 | 方法 |
|---|---|
| 基础实力 | FIFA 排名 → Elo（+ 阵容质量修正） |
| 动态实力 | 每踢完一场，`Δ = 16×(实际净胜 − 期望净胜)` |
| **模型 1X2** | 泊松联合网格按区域求和 → 胜/平/负概率 |
| **赔率融合** | `blend_1x2 = 0.3×模型 + 0.7×赔率去水概率`（方向分歧时自适应提权） |
| 预测比分 | 融合 1X2 的 argmax 定方向 → 该方向众数比分（确定性，首页/小组赛同场一致） |
| 复盘准确率 | 赛前纯模型预测（**use_odds=False**，无信息泄漏） |
| 夺冠概率 | 蒙特卡洛 1000 次（有赔率场用融合 1X2 抽样） |

## 📁 结构

```
shijiebei/
├── app.py              # Flask 路由 + 视图数据 + 实时缓存
├── predictor.py        # Elo + 模型1X2 + 赔率融合 + 蒙特卡洛
├── odds_data.py        # The Odds API 抓取 + 去水(vig removal) + 2h缓存
├── squad_data.py       # Wikipedia 阵容抓取 + 五大联赛占比
├── form_data.py        # OpenLigaDB 大赛战绩 + h2h 派生
├── reasons.py          # 预测理由生成器(排名/赔率/阵容/战绩/交锋/总评)
├── live_data.py        # OpenLigaDB 赛果抓取 + 真实/未踢分类
├── wc_data.py          # 48队 + 12组 + 签表 + 球场 + 德名映射
├── templates/index.html # 单页：玻璃外壳 + 5Tab + 预测理由
├── test_predictor.py   # 核心逻辑单测
├── test_app.py         # 应用层单测
├── test_dimensions.py  # 多维度单测
├── test_odds.py        # 赔率融合单测
├── Dockerfile          # Docker 部署（gunicorn）
├── docker-compose.yml  # 端口 6889 映射
└── requirements.txt
```

## 🚀 运行

```bash
pip install -r requirements.txt

# 赔率功能需要 key（可选；无 key 自动降级为纯模型）
export ODDS_API_KEY="你的key"    # https://the-odds-api.com/ 免费注册

python app.py          # → http://localhost:8000
python test_predictor.py && python test_app.py && python test_dimensions.py && python test_odds.py
```

### Docker 部署（VPS）

```bash
git clone https://github.com/wssXzzzz/sjb.git && cd sjb
# 赔率 key（可选）
echo 'ODDS_API_KEY=你的key' > .env
docker compose up -d --build    # → http://你的VPS_IP:6889
```

## ⚠️ 说明
- 分组依据 2025-12-05 抽签；FIFA 排名为 2025-11 排名
- 开赛时间统一为北京时间（OpenLigaDB `matchDateTimeUTC` 换算）
- 近期战绩对 CAF/AFC 队可能样本不足（OpenLigaDB 不含非洲杯/亚洲杯），如实标注
- €身价/伤病/签证无免费可靠源，未做；阵容质量作为球员实力代理
- 预测仅为模型娱乐，不代表真实赛果
