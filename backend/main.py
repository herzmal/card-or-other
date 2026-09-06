# -*- coding: utf-8 -*-
"""卡牌对战游戏 —— Python 后端（FastAPI）

职责：
- 提供 HTTP 接口给 Unity 前端调用
- 登录/注册（账号存 SQLite，密码 SHA-256 哈希）
- 卡牌数据查询
- （后续）人机对战 / 联网对战，复用同目录的 card_effects 逻辑

启动方式：
    cd backend
    python -m uvicorn main:app --host 0.0.0.0 --port 8000
"""
import os
import sys
import json
import hashlib
import secrets

import pymysql
import pymysql.err
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

# 让 backend 能 import 上级目录的 cards.json
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BASE_DIR)

app = FastAPI(title="卡牌对战后端", version="0.1.0")

# ============ MySQL 账号数据库 ============
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "123456",
    "charset": "utf8mb4",
}
DB_NAME = "card_game"


def _connect(with_db=True):
    """连接 MySQL；with_db=False 时只连服务器（用于建库）"""
    cfg = dict(DB_CONFIG)
    if with_db:
        cfg["database"] = DB_NAME
    return pymysql.connect(**cfg)


def hash_pw(pw: str) -> str:
    return hashlib.sha256(pw.encode("utf-8")).hexdigest()


# ============ 登录会话（token）持久化 ============
# 说明：登录后发 token，前端把它存本地并在启动时用它静默恢复登录态。
# token 同时写盘（sessions.json），后端重启后仍有效 → 前端免登录真正可靠。
TOKENS = {}
SESSIONS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sessions.json")


def _save_sessions():
    """把当前 TOKENS 写盘（含已登录用户名），供重启后恢复。"""
    try:
        with open(SESSIONS_FILE, "w", encoding="utf-8") as f:
            json.dump(TOKENS, f, ensure_ascii=False)
    except Exception:
        pass


def _load_sessions():
    """启动时从磁盘载入历史 token。"""
    global TOKENS
    try:
        if os.path.exists(SESSIONS_FILE):
            with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                TOKENS = loaded
    except Exception:
        TOKENS = {}


def issue_token(username: str) -> str:
    """生成新 token 并写入内存+磁盘，返回 token。"""
    token = secrets.token_hex(16)
    TOKENS[token] = username
    _save_sessions()
    return token


def lookup_token(token: str):
    """校验 token，返回对应用户名；无效返回 None。"""
    if not token:
        return None
    return TOKENS.get(token)


def revoke_token(token: str):
    """登出：删除该 token。"""
    if token and TOKENS.pop(token, None) is not None:
        _save_sessions()


# ============ 请求体模型 ============
class RegisterReq(BaseModel):
    username: str
    password: str


class LoginReq(BaseModel):
    username: str
    password: str


# ============ 卡牌数据 ============
def load_cards():
    with open(os.path.join(BASE_DIR, "cards.json"), encoding="utf-8") as f:
        return json.load(f)


def init_db():
    """创建数据库与用户表（幂等，可重复执行）"""
    conn = _connect(with_db=False)
    try:
        with conn.cursor() as cur:
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
        conn.commit()
    finally:
        conn.close()

    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "CREATE TABLE IF NOT EXISTS users ("
                "id INT PRIMARY KEY AUTO_INCREMENT, "
                "username VARCHAR(64) NOT NULL UNIQUE, "
                "password CHAR(64) NOT NULL"
                ") ENGINE=InnoDB DEFAULT CHARSET=utf8mb4"
            )
        conn.commit()
    finally:
        conn.close()


# ============ 接口 ============
@app.get("/health")
async def health():
    return {"status": "ok", "service": "card-battle-backend"}


@app.get("/api/cards")
async def get_cards():
    cards = load_cards()
    return {"total": len(cards), "cards": cards}


@app.post("/api/register")
async def register(req: RegisterReq):
    u = req.username.strip()
    p = req.password
    if not u or not p:
        raise HTTPException(status_code=400, detail="账号和密码不能为空")
    if len(u) > 64:
        raise HTTPException(status_code=400, detail="账号过长（最多 64 字符）")
    conn = _connect()
    try:
        with conn.cursor() as cur:
            try:
                cur.execute(
                    "INSERT INTO users (username, password) VALUES (%s, %s)",
                    (u, hash_pw(p)),
                )
                conn.commit()
            except pymysql.err.IntegrityError:
                raise HTTPException(status_code=400, detail="账号已存在")
    finally:
        conn.close()
    return {"ok": True, "msg": "注册成功"}


@app.get("/api/check_username")
async def check_username(username: str = ""):
    """注册界面实时校验账号是否已被占用"""
    u = username.strip()
    if not u:
        return {"ok": True, "exists": False}
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM users WHERE username=%s LIMIT 1", (u,))
            row = cur.fetchone()
    finally:
        conn.close()
    return {"ok": True, "exists": row is not None}


@app.post("/api/login")
async def login(req: LoginReq):
    u = req.username.strip()
    p = req.password
    conn = _connect()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT password FROM users WHERE username=%s", (u,))
            row = cur.fetchone()
    finally:
        conn.close()
    if row is None or row[0] != hash_pw(p):
        raise HTTPException(status_code=401, detail="账号或密码错误")

    token = issue_token(u)
    return {"ok": True, "msg": "登录成功", "token": token, "username": u}


@app.get("/api/session")
async def session(token: str = ""):
    """客户端用本地保存的 token 静默恢复登录态。有效返回用户名，无效返回 401。"""
    u = lookup_token(token)
    if u is None:
        raise HTTPException(status_code=401, detail="登录已失效")
    return {"ok": True, "username": u}


@app.post("/api/logout")
async def logout(token: str = ""):
    """登出：使该 token 失效。"""
    revoke_token(token)
    return {"ok": True, "msg": "已登出"}


# ============ 人机对战（复用无头引擎，需带 tkinter 的 Python） ============
BATTLES = {}   # battle_id -> BattleEngine


class BattlePlayReq(BaseModel):
    hand_index: int
    targets: list = []


class BattleEndTurnReq(BaseModel):
    discard: list = []   # 手牌超限时玩家指定弃置的索引


class BattleAttackReq(BaseModel):
    unit_index: int          # 我方站场造物在 board_mine 中的下标
    targets: list = []       # 攻击目标（目前单目标，如 [["hero","enemy"]]）


class BattleStartReq(BaseModel):
    """副本模式开局参数：继承上一场战斗的英雄状态与奖励加成（普通对战可不传）"""
    hero_hp: int | None = None       # 继承的当前血量（不传则满血开局）
    hero_max_hp: int | None = None   # 继承的血量上限
    hero_atk: int = 0                # 副本奖励：攻击加成（整场副本有效）
    start_mana: int = 0              # 副本奖励：开局额外能量（一次性）


def _new_battle(hero_hp=None, hero_max_hp=None, hero_atk=0, start_mana=0):
    """创建新对局；同时关闭旧对局，避免多个 Tk 实例共存。"""
    import headless_engine  # 延迟导入：仅 battle 接口需要 tkinter
    for e in BATTLES.values():
        e.close()
    BATTLES.clear()
    engine = headless_engine.BattleEngine(
        hero_hp=hero_hp, hero_max_hp=hero_max_hp,
        hero_atk=hero_atk, start_mana=start_mana)
    battle_id = secrets.token_hex(16)
    BATTLES[battle_id] = engine
    return battle_id, engine


@app.post("/api/battle/start")
async def battle_start(req: BattleStartReq = None):
    r = req or BattleStartReq()
    battle_id, engine = _new_battle(
        hero_hp=r.hero_hp, hero_max_hp=r.hero_max_hp,
        hero_atk=r.hero_atk, start_mana=r.start_mana)
    return {"ok": True, "battle_id": battle_id, "state": engine.state()}


@app.get("/api/battle/{battle_id}/state")
async def battle_state(battle_id: str):
    engine = BATTLES.get(battle_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    return {"ok": True, "state": engine.state()}


@app.post("/api/battle/{battle_id}/play")
async def battle_play(battle_id: str, req: BattlePlayReq):
    engine = BATTLES.get(battle_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    result = engine.play(req.hand_index, req.targets)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, "state": result["state"]}


@app.post("/api/battle/{battle_id}/attack")
async def battle_attack(battle_id: str, req: BattleAttackReq):
    """指挥我方站场造物攻击（每只造物每回合限一次）。"""
    engine = BATTLES.get(battle_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    result = engine.attack(req.unit_index, req.targets)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, "state": result["state"]}


@app.post("/api/battle/{battle_id}/end_turn")
async def battle_end_turn(battle_id: str, req: BattleEndTurnReq = None):
    engine = BATTLES.get(battle_id)
    if engine is None:
        raise HTTPException(status_code=404, detail="对局不存在")
    result = engine.end_turn(req.discard if req else [])
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return {"ok": True, "state": result["state"]}


# ============ 联网人人对战（房间 + WebSocket） ============
ROOMS = {}   # room_id -> {"engine": PvpEngine, "mine": WebSocket|None, "enemy": WebSocket|None}


class JoinReq(BaseModel):
    room_id: str


@app.post("/api/room/create")
async def room_create():
    """创建房间，返回 room_id（创建者连接 WebSocket 时用 side=mine）。"""
    import pvp_engine
    engine = pvp_engine.PvpEngine()
    room_id = secrets.token_hex(8)
    ROOMS[room_id] = {"engine": engine, "mine": None, "enemy": None}
    return {"ok": True, "room_id": room_id}


@app.post("/api/room/join")
async def room_join(req: JoinReq):
    """加入房间，返回可用的 side（enemy 或 mine）。"""
    room = ROOMS.get(req.room_id)
    if room is None:
        raise HTTPException(status_code=404, detail="房间不存在")
    if room["enemy"] is None:
        return {"ok": True, "side": "enemy"}
    if room["mine"] is None:
        return {"ok": True, "side": "mine"}
    raise HTTPException(status_code=409, detail="房间已满")


async def _broadcast(room, engine):
    """把最新状态按各自视角广播给双方。"""
    for side, ws in (("mine", room["mine"]), ("enemy", room["enemy"])):
        if ws is not None:
            try:
                await ws.send_json({"type": "state", "state": engine.state(side)})
            except Exception:
                pass


@app.websocket("/ws/room/{room_id}")
async def room_ws(websocket: WebSocket, room_id: str):
    await websocket.accept()
    room = ROOMS.get(room_id)
    if room is None:
        await websocket.send_json({"type": "error", "message": "房间不存在"})
        await websocket.close()
        return

    side = websocket.query_params.get("side", "mine")
    if side not in ("mine", "enemy"):
        side = "mine"
    if room[side] is not None:
        await websocket.send_json({"type": "error", "message": "该位置已被占用"})
        await websocket.close()
        return

    room[side] = websocket
    engine = room["engine"]
    # 发送当前状态给刚连接的玩家
    await websocket.send_json({"type": "state", "state": engine.state(side)})
    # 通知对方有新玩家加入（只发给对方，避免给刚连接玩家重复发 state）
    other = "enemy" if side == "mine" else "mine"
    if room[other] is not None:
        try:
            await room[other].send_json({"type": "state", "state": engine.state(other)})
        except Exception:
            pass

    try:
        while True:
            msg = await websocket.receive_json()
            action = msg.get("action")

            if action == "play":
                result = engine.play(side, msg.get("hand_index"), msg.get("targets"))
            elif action == "attack":
                result = engine.attack(side, msg.get("unit_index"),
                                       msg.get("targets"))
            elif action == "end_turn":
                result = engine.end_turn(side, msg.get("discard"))
            elif action == "state":
                result = {"ok": True, "state": engine.state(side)}
            else:
                result = {"error": "未知操作"}

            if "error" in result:
                await websocket.send_json({"type": "error", "message": result["error"]})
            else:
                await _broadcast(room, engine)
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        if room.get(side) is websocket:
            room[side] = None
        # 双方都断开时清理房间
        if room["mine"] is None and room["enemy"] is None:
            try:
                engine.close()
            except Exception:
                pass
            ROOMS.pop(room_id, None)


# ============ 启动时初始化 ============
_load_sessions()   # 载入历史登录 token（后端重启后免登录仍有效）
init_db()
