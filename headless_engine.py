# -*- coding: utf-8 -*-
"""无头战斗引擎：复用 card_viewer.CardApp 的战斗逻辑，不显示图形界面。

原理：用 withdraw 的 Tk 实例化 CardApp（战斗逻辑 100% 复用，与 GUI 版完全一致），
把依赖 Tk 事件循环的「抽牌动画」手动结算，特效/日志静默收集。

后端 FastAPI 用它驱动人机对战。
"""
import tkinter as tk

import card_viewer as cv
from card_effects import resolve  # noqa: F401  （触发处理器注册）


class BattleEngine:
    def __init__(self, seed=None, hero_hp=None, hero_max_hp=None,
                 hero_atk=0, start_mana=0):
        if seed is not None:
            import random
            random.seed(seed)
        self.root = tk.Tk()
        self.root.withdraw()
        self.app = cv.CardApp(self.root)
        self._apply_run_state(hero_hp, hero_max_hp, hero_atk, start_mana)
        self.events = []   # 特效事件收集（伤害/回血/格挡/震动）
        self._patch_fx()
        self._settle_anim()

    def _apply_run_state(self, hero_hp, hero_max_hp, hero_atk, start_mana):
        """副本模式：继承上一场战斗的英雄状态（血量/上限/攻击/开局能量）"""
        app = self.app
        hero = app.hero
        if hero_max_hp is not None and int(hero_max_hp) > 0:
            hero["max_hp"] = int(hero_max_hp)
            hero["base_max_hp"] = hero["max_hp"]
        if hero_hp is not None and int(hero_hp) > 0:
            hero["hp"] = min(int(hero_hp), hero["max_hp"])
        if hero_atk:
            hero["base_atk"] = hero.get("base_atk", 0) + int(hero_atk)
            hero["atk"] = hero.get("atk", 0) + int(hero_atk)
        if start_mana:
            app.mana = min(app.MAX_MANA, app.mana + int(start_mana))

    def _patch_fx(self):
        """把 CardApp 的特效方法替换成事件收集器，供前端渲染特效"""
        app = self.app

        def _tj(target):
            # 永远返回列表：Unity JsonUtility 的 List 字段收到 JSON null 会解析失败
            return list(target) if target is not None else []

        def dmg(text, target=None):
            self.events.append({"type": "dmg", "text": text, "target": _tj(target)})

        def heal(text, target=None):
            self.events.append({"type": "heal", "text": text, "target": _tj(target)})

        def block(mode, target=None):
            self.events.append({"type": "block", "mode": mode, "target": _tj(target)})

        def shake(target=None):
            self.events.append({"type": "shake", "target": _tj(target)})

        app._spawn_dmg_fx = dmg
        app._spawn_heal_fx = heal
        app._spawn_block_fx = block
        app._spawn_unit_shake = shake

    # ---------- 动画结算 ----------
    def _settle_anim(self):
        """手动完成当前抽牌动画：把飞行中的卡牌直接加入对应手牌"""
        app = self.app
        while app.anim is not None:
            anim = app.anim
            side = anim["side"]
            hand = app.hand if side == "mine" else app.enemy_hand
            hand.extend(anim["entries"])
            app.anim = None
        app.fx = []   # 无头下特效不显示，清空避免累积

    # ---------- 状态序列化（供 Unity 前端渲染） ----------
    def state(self):
        app = self.app
        events = self.events
        self.events = []   # 取走并清空，避免重复发送
        return {
            "turn": app.turn,
            "round": app.round,
            "game_over": app.game_over or "",   # 未结束传空串，避免 JSON null
            "mana": app.mana,
            "mana_max": app.MAX_MANA,
            "enemy_mana": app.enemy_mana,
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

    @staticmethod
    def _equip_state(e):
        c = e["card"]
        return {
            "name": c["name"],
            "rounds": e["rounds"] or 0,   # 同 duration：int 字段不能是 null
            "category": c.get("category", "装备卡"),
            # 供前端悬停显示完整详情
            "desc": c.get("desc", ""),
            "cost": c.get("cost", 0),
            "duration": c.get("duration") or 0,
            "atk_bonus": c.get("atk_bonus") or 0,
            "def_bonus": c.get("def_bonus") or 0,
        }

    @staticmethod
    def _hero_state(h):
        return {
            "hp": h["hp"], "max_hp": h["max_hp"],
            "base_atk": h.get("base_atk", 0), "atk": h["atk"],
            "base_def": h.get("base_def", 0), "def": h["def"],
            "block": h["block"], "true_block": h["true_block"],
            "poison": h.get("poison", 0), "chill": h.get("chill", 0),
            "bleed": h.get("bleed", 0), "charge": h.get("charge", 0),
            "statuses": [{"name": s["name"], "rounds": s.get("rounds", 0),
                          "desc": cv.STATUS_EFFECTS.get(s["name"], {}).get("desc", "")}
                         for s in h["statuses"]],
        }

    @staticmethod
    def _card_state(card):
        if card is None:
            return None
        # 战吼行 / 装备加成行（与 card_viewer 卡面显示一致）
        battlecry = ""
        if card.get("gain_block", 0) > 0:
            battlecry = f"战吼：获得 {card['gain_block']} 格挡"
        bonus = []
        if card.get("atk_bonus", 0) > 0:
            bonus.append(f"攻击 +{card['atk_bonus']}")
        if card.get("def_bonus", 0) > 0:
            bonus.append(f"防御 +{card['def_bonus']}")
        return {
            "name": card["name"], "cost": card["cost"],
            "category": card["category"], "type": card.get("type", "normal"),
            "desc": card.get("desc", ""),
            "needs_target": cv.needs_target(card),
            "max_targets": cv.max_targets(card),   # 多目标卡一次可选目标数
            "battlecry": battlecry,
            "bonus": bonus,
            # 注意：Unity JsonUtility 的 int 字段不能接收 JSON null，无值时传 0（-1 表示永久）
            "duration": card.get("duration") or 0,
            "health": card.get("health") or 0,     # 造物卡生命值
        }

    @staticmethod
    def _unit_state(u):
        return {
            "name": u["card"]["name"], "hp": u["hp"],
            "max_hp": u.get("max_hp", u["hp"]), "atk": u.get("atk", 0),
            "can_attack": u.get("can_attack", True),
            "category": u["card"].get("category", "造物卡"),
            "rounds": u.get("rounds") or 0,
            "desc": u["card"].get("desc", ""),
        }

    # ---------- 玩家出牌 ----------
    @staticmethod
    def _norm_targets(targets):
        """JSON 传入的 list（如 [["hero","enemy"]]）转成 tuple；board 索引转 int"""
        ts = [tuple(t) for t in targets]
        return [
            (t[0], t[1], int(t[2])) if t[0] == "board" and len(t) > 2 else t
            for t in ts
        ]

    def attack(self, unit_idx, targets=None):
        """指挥我方站场造物攻击：unit_idx 为 board_mine 下标。"""
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != "mine":
            return {"error": "不是你的回合"}
        if unit_idx < 0 or unit_idx >= len(app.board_mine):
            return {"error": "无效造物索引"}
        unit = app.board_mine[unit_idx]
        if not unit.get("can_attack"):
            return {"error": f"「{unit['card']['name']}」本回合已攻击过"}
        if not targets:
            return {"error": "需要选择攻击目标"}
        app._resolve_target_attack(("board", "mine", unit_idx),
                                   self._norm_targets(targets))
        self._settle_anim()
        return {"ok": True, "state": self.state()}

    def play(self, hand_idx, targets=None):
        """玩家打出手牌第 hand_idx 张。需目标的卡必须提供 targets。"""
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != "mine":
            return {"error": "不是你的回合"}
        if hand_idx < 0 or hand_idx >= len(app.hand):
            return {"error": "无效手牌索引"}

        card = app._card_of(app.hand[hand_idx])
        if not app._can_play(card, "mine"):
            return {"error": f"当前状态无法使用「{card['name']}」"}
        cost = app._effective_cost(card, "mine")
        if cost > app.mana:
            return {"error": "能量不足"}

        if cv.needs_target(card):
            if not targets:
                return {"error": "该卡需要选择目标"}
            max_t = cv.max_targets(card)
            if max_t > 0 and len(targets) > max_t:
                return {"error": f"「{card['name']}」最多只能选择 {max_t} 个目标"}
            # JSON 传入的是 list（如 [["hero","enemy"]]），转成 tuple；board 目标索引转 int
            app._resolve_target_attack(("hand", hand_idx),
                                       self._norm_targets(targets))
        else:
            app.selected = ("mine", hand_idx)
            app._play_selected()

        self._settle_anim()
        return {"ok": True, "state": self.state()}

    # ---------- 结束回合 + AI 回合 ----------
    def end_turn(self, discard=None):
        app = self.app
        if app.game_over is not None:
            return {"error": "对局已结束"}
        if app.turn != "mine":
            return {"error": "不是你的回合"}

        # 先按玩家指定弃牌（索引从大到小弹出，避免错位）
        if discard:
            for i in sorted(set(int(d) for d in discard), reverse=True):
                if 0 <= i < len(app.hand):
                    card = app._card_of(app.hand[i])
                    app.hand.pop(i)
                    app._log(f"我方 弃置「{card['name']}」")
        self._auto_discard("mine")
        app._finish_turn()
        self._settle_anim()

        if app.game_over is None and app.turn == "enemy":
            self._ai_turn()

        return {"ok": True, "state": self.state()}

    def _auto_discard(self, side):
        """弃牌：手牌超过上限自动弃最左，直到不超限"""
        app = self.app
        hand = app.hand if side == "mine" else app.enemy_hand
        limit = getattr(cv, "HAND_LIMIT", 9)
        who = "我方" if side == "mine" else "敌方"
        while len(hand) > limit:
            card = app._card_of(hand[0])
            hand.pop(0)
            app._log(f"{who} 弃置「{card['name']}」")

    def _ai_turn(self):
        """AI 回合：简单策略——能出的牌尽量出（攻击卡打玩家英雄），然后结束回合"""
        app = self.app
        guard = 0
        while app.turn == "enemy" and app.game_over is None:
            if not self._ai_play_one():
                break
            guard += 1
            if guard > 100:
                break
        if app.game_over is None:
            self._auto_discard("enemy")
            app._finish_turn()
            self._settle_anim()

    def _ai_play_one(self):
        """AI 出一次牌（或造物攻击），返回是否成功行动"""
        app = self.app
        # 1) 站场造物攻击玩家英雄
        for idx, unit in enumerate(app.board_enemy):
            if unit.get("can_attack") and unit.get("atk", 0) > 0:
                app._resolve_target_attack(("board", "enemy", idx),
                                           [("hero", "mine")])
                return True
        # 2) 打手牌
        for idx in range(len(app.enemy_hand)):
            card = app._card_of(app.enemy_hand[idx])
            if not app._can_play(card, "enemy"):
                continue
            cost = app._effective_cost(card, "enemy")
            if cost > app.enemy_mana:
                continue
            if cv.needs_target(card):
                app._resolve_target_attack(("hand", idx), [("hero", "mine")])
            else:
                app.selected = ("enemy", idx)
                app._play_selected()
            return True
        return False

    # ---------- 清理 ----------
    def close(self):
        try:
            self.root.destroy()
        except Exception:
            pass
