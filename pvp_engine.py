# -*- coding: utf-8 -*-
"""双人对战引擎：复用 CardApp 战斗逻辑，无 AI，两个玩家轮流操作。

玩家 A 控制 mine 侧，玩家 B 控制 enemy 侧。服务端是唯一权威状态，
两个玩家通过 WebSocket 各自发送操作（出牌/结束回合），服务端结算后
广播最新状态给双方。
"""
import tkinter as tk

import card_viewer as cv
from headless_engine import BattleEngine


class PvpEngine(BattleEngine):
    """双人对战：复用 BattleEngine 的初始化/特效收集/状态序列化，重写出牌与回合切换。"""

    # ---------- 玩家出牌 ----------
    def play(self, side, hand_idx, targets=None):
        """side 玩家打出手牌第 hand_idx 张。"""
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != side:
            return {"error": "不是你的回合"}
        hand = app.hand if side == "mine" else app.enemy_hand
        if hand_idx < 0 or hand_idx >= len(hand):
            return {"error": "无效手牌索引"}

        card = app._card_of(hand[hand_idx])
        if not app._can_play(card, side):
            return {"error": f"当前状态无法使用「{card['name']}」"}
        cost = app._effective_cost(card, side)
        cost_attr = "mana" if side == "mine" else "enemy_mana"
        if cost > getattr(app, cost_attr):
            return {"error": "能量不足"}

        if cv.needs_target(card):
            if not targets:
                return {"error": "该卡需要选择目标"}
            max_t = cv.max_targets(card)
            if max_t > 0 and len(targets) > max_t:
                return {"error": f"「{card['name']}」最多只能选择 {max_t} 个目标"}
            # 站场造物攻击：src 用 ("board", side, idx)
            app._resolve_target_attack(("hand", hand_idx),
                                       self._norm_targets(targets))
        else:
            app.selected = (side, hand_idx)
            app._play_selected()

        self._settle_anim()
        return {"ok": True, "state": self.state(side)}

    # ---------- 造物攻击 ----------
    def attack(self, side, unit_idx, targets=None):
        """side 玩家指挥自己场上的造物攻击（每回合每只限一次）。"""
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != side:
            return {"error": "不是你的回合"}
        board = app.board_mine if side == "mine" else app.board_enemy
        if unit_idx < 0 or unit_idx >= len(board):
            return {"error": "无效造物索引"}
        unit = board[unit_idx]
        if not unit.get("can_attack"):
            return {"error": f"「{unit['card']['name']}」本回合已攻击过"}
        if not targets:
            return {"error": "需要选择攻击目标"}
        app._resolve_target_attack(("board", side, unit_idx),
                                   self._norm_targets(targets))
        self._settle_anim()
        return {"ok": True, "state": self.state(side)}

    # ---------- 结束回合 ----------
    def end_turn(self, side, discard=None):
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != side:
            return {"error": "不是你的回合"}

        # 玩家指定的弃牌（索引从大到小弹出，避免错位）
        if discard:
            hand = app.hand if side == "mine" else app.enemy_hand
            who = "我方" if side == "mine" else "敌方"
            for i in sorted(set(int(d) for d in discard), reverse=True):
                if 0 <= i < len(hand):
                    card = app._card_of(hand[i])
                    hand.pop(i)
                    app._log(f"{who} 弃置「{card['name']}」")
        self._auto_discard(side)
        app._finish_turn()
        self._settle_anim()
        # 无 AI：切回合后等待另一方操作
        return {"ok": True, "state": self.state(side)}

    # ---------- 按视角返回状态 ----------
    def state(self, side="mine"):
        """返回指定 side 视角的状态（enemy 视角时对调 hero/enemy、hand、board、equips、mana）。"""
        app = self.app
        events = self.events
        self.events = []   # 取走并清空，避免重复发送

        if side == "mine":
            return {
                "turn": app.turn,
                "round": app.round,
                "game_over": app.game_over,
                "mana": app.mana, "mana_max": app.MAX_MANA, "enemy_mana": app.enemy_mana,
                "hero": self._hero_state(app.hero),
                "enemy": self._hero_state(app.enemy_hero),
                "hand": [self._card_state(app._card_of(e)) for e in app.hand],
                "enemy_hand_count": len(app.enemy_hand),
                "board_mine": [self._unit_state(u) for u in app.board_mine],
                "board_enemy": [self._unit_state(u) for u in app.board_enemy],
                "equips_mine": [self._equip_state(e) for e in app.hero_equips],
                "equips_enemy": [self._equip_state(e) for e in app.enemy_equips],
                "played": [{"name": c["name"], "category": c.get("category", "基本卡")}
                           for c, _, _ in app.played],
                "log": app.log[-200:],
                "events": events,
            }
        else:
            # enemy 视角：对调敌我
            return {
                "turn": app.turn,
                "round": app.round,
                "game_over": app.game_over,
                "mana": app.enemy_mana, "mana_max": app.MAX_MANA, "enemy_mana": app.mana,
                "hero": self._hero_state(app.enemy_hero),
                "enemy": self._hero_state(app.hero),
                "hand": [self._card_state(app._card_of(e)) for e in app.enemy_hand],
                "enemy_hand_count": len(app.hand),
                "board_mine": [self._unit_state(u) for u in app.board_enemy],
                "board_enemy": [self._unit_state(u) for u in app.board_mine],
                "equips_mine": [self._equip_state(e) for e in app.enemy_equips],
                "equips_enemy": [self._equip_state(e) for e in app.hero_equips],
                "played": [{"name": c["name"], "category": c.get("category", "基本卡")}
                           for c, _, _ in app.played],
                "log": app.log[-200:],
                "events": events,
            }
