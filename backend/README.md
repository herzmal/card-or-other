# 卡牌对战 Python 后端

FastAPI 实现的后端服务，给 Unity 前端提供接口（登录注册 / 人机对战 / 联网 PVP / 副本开局参数）。

> ⚠️ **运行环境**：人机对战接口复用了无头引擎（`headless_engine.py`），它依赖 tkinter，所以后端**必须用带 tkinter 的 Python 运行**（项目自带的 `D:\zzdelvelp\python\python.exe` 3.14.6 即可，`启动后端.bat` 已配置好）。

## 目录结构

```
backend/
├── main.py          # 后端入口（登录/注册/卡牌/人机对战/房间+WebSocket）
├── requirements.txt # 依赖（fastapi / uvicorn / pymysql）
├── 启动后端.bat      # 一键启动
└── README.md
```

## 准备工作

### 1. MySQL

- 本机需运行 MySQL 服务（项目使用 MySQL 8.4）
- 连接配置在 `main.py` 顶部的 `DB_CONFIG`（host / port / user / password），按需修改
- 数据库 `card_game` 与用户表 `users` 在**后端启动时自动创建**（幂等），无需手动建库
- 密码以 SHA-256 哈希存储（非明文），所有查询使用参数化占位符防注入

### 2. Python 依赖

```bash
cd /d "D:\zzdelvelp\卡牌制作\backend"
"D:\zzdelvelp\python\python.exe" -m pip install -r requirements.txt
```

## 启动

双击 `启动后端.bat`，或手动执行：

```bash
cd /d "D:\zzdelvelp\卡牌制作\backend"
"D:\zzdelvelp\python\python.exe" -m uvicorn main:app --host 0.0.0.0 --port 8000
```

启动后：

- 接口文档（Swagger，浏览器打开）：http://127.0.0.1:8000/docs
- 健康检查：http://127.0.0.1:8000/health

## 现有接口

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | /health | 健康检查 |
| GET | /api/cards | 返回全部 197 张卡牌数据 |
| POST | /api/register | 注册，body: `{"username":"xxx","password":"xxx"}` |
| POST | /api/login | 登录，返回 token |
| POST | /api/battle/start | 开始人机对局，返回 battle_id + 初始状态；**副本模式可带可选继承参数**（见下） |
| GET | /api/battle/{battle_id}/state | 获取当前战斗状态 |
| POST | /api/battle/{battle_id}/play | 出牌，body: `{"hand_index":0,"targets":[["hero","enemy"]]}` |
| POST | /api/battle/{battle_id}/attack | 指挥我方造物攻击，body: `{"unit_index":0,"targets":[["hero","enemy"]]}` |
| POST | /api/battle/{battle_id}/end_turn | 结束回合（自动触发 AI 回合），body 可选 `{"discard":[0,1]}`（手牌超限时指定弃置索引） |
| POST | /api/room/create | 创建联网对战房间，返回 room_id |
| POST | /api/room/join | 加入房间，body: `{"room_id":"xxx"}`，返回可用 side |
| WS | /ws/room/{room_id}?side=mine 或 enemy | 联网对战 WebSocket：收 `state`/`error`，发 `{"action":"play"/"attack"/"end_turn", ...}` |

### 副本开局参数（/api/battle/start 可选 body）

副本爬塔时英雄血量在战斗间继承，奖励提供成长加成，开局时由 Unity 传入：

```json
{
  "hero_hp": 55,        // 继承的当前血量（不传则满血 100）
  "hero_max_hp": 80,    // 继承的血量上限
  "hero_atk": 3,        // 攻击加成（副本奖励，整场副本有效）
  "start_mana": 2       // 开局额外能量（副本奖励，一次性）
}
```

普通对战不传 body 或传 `{}` 即可，完全兼容。

## 战斗状态字段说明

`state` 返回的结构：

```json
{
  "turn": "mine", "round": 1, "game_over": null,
  "mana": 6, "mana_max": 12, "enemy_mana": 0,
  "hero": {"hp":100,"max_hp":100,"atk":0,"def":0,"block":0,"statuses":["虚弱"]},
  "enemy": {"hp":100, "..."},
  "hand": [{"name":"斩杀","cost":5,"category":"攻击卡","desc":"...","needs_target":true}],
  "enemy_hand_count": 6,
  "board_mine": [], "board_enemy": [],
  "equips_mine": [], "equips_enemy": [],
  "events": [{"type":"dmg","text":"-8","target":["hero","enemy"]}],
  "log": ["我方 打出「斩杀」", "..."]
}
```

- `needs_target=true` 的卡出牌时需要传 `targets`（目标元组，如 `["hero","enemy"]` 打敌方主角）。
- `events` 是自上次取状态以来的特效事件（dmg/heal/block/shake），供前端渲染飘字与震动。
- `log` 是最近的战斗记录，供前端左侧记录栏滚动显示。

## 说明

- 账号存 MySQL（`card_game`.`users`），密码 SHA-256 哈希，查询全部参数化防注入。
- 登录返回的 `token` 目前存在内存里，重启后端后失效；正式项目建议换成 JWT。
- 人机对战的 AI 目前是「能出就出」的简单策略，后续可替换成更聪明的算法。
- 旧版 SQLite 的 `users.db` 已不再使用，确认无需保留旧账号后可删除。
