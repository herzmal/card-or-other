# -*- coding: utf-8 -*-
"""
共享辅助函数：目标/阵营解析、伤害结算、状态与层数操作。
所有函数第一个参数 app 为 CardApp 实例。
"""


# ---------- 阵营 / 目标解析 ----------
def enemy_side(side):
    return "enemy" if side == "mine" else "mine"


def hero(app, side):
    return app.hero if side == "mine" else app.enemy_hero


def enemy_hero(app, side):
    return app.enemy_hero if side == "mine" else app.hero


def board(app, side):
    return app.board_mine if side == "mine" else app.board_enemy


def enemy_board(app, side):
    return app.board_enemy if side == "mine" else app.board_mine


def enemy_units(app, side):
    """返回敌方可作为目标的单位 target 元组列表（主角色 + 所有站场造物）"""
    es = enemy_side(side)
    units = [("hero", es)]
    for i in range(len(enemy_board(app, side))):
        units.append(("board", es, i))
    return units


def all_units(app, side):
    """返回某方所有单位（主角色 + 站场造物）"""
    units = [("hero", side)]
    for i in range(len(board(app, side))):
        units.append(("board", side, i))
    return units


def target_owner_side(target):
    """返回目标所属方"""
    return target[1]


# ---------- 伤害 ----------
def deal(app, attacker_hero, target, amount, **flags):
    """统一伤害入口，转发到 CardApp._deal_target"""
    return app._deal_target(attacker_hero, target, amount, **flags)


def _attacker_side(app, attacker_hero):
    """根据攻击方 hero 对象反推其所属方"""
    if attacker_hero is app.hero:
        return "mine"
    return "enemy"


def deal_aoe(app, attacker_hero, amount, **flags):
    """对所有敌方单位造成伤害（简化版，不依赖 _side）"""
    side = _attacker_side(app, attacker_hero)
    es = enemy_side(side)
    total = deal(app, attacker_hero, ("hero", es), amount, **flags)
    eb = enemy_board(app, side)
    for i in range(len(eb)):
        total += deal(app, attacker_hero, ("board", es, i), amount, **flags)
    return total


# ---------- 状态 ----------
def has_status(hero_obj, name):
    return any(st["name"] == name for st in hero_obj.get("statuses", []))


def add_status(app, hero_obj, name, rounds):
    app._apply_status(hero_obj, {"name": name, "rounds": rounds})


def weaken_amount(app, hero_obj):
    p = 0
    for st in hero_obj.get("statuses", []):
        if st["name"] == "弱化":
            p += 4
        elif st["name"] == "加强版弱化":
            p += 6
    return p


# ---------- 层数 ----------
STACK_NAMES = {"poison": "毒", "bleed": "流血", "chill": "寒冷",
               "snow": "雪", "charge": "电感"}


def add_stack(app, hero_obj, key, n):
    hero_obj[key] = hero_obj.get(key, 0) + n
    if n:
        app._log(f"{app._side_label(hero_obj) or '单位'} "
                 f"{STACK_NAMES.get(key, key)}+{n}")


def add_chill(app, hero_obj, n, side):
    """施加寒冷；冻结状态下额外叠加"""
    if n <= 0:
        return
    if has_status(hero_obj, "冻结"):
        n += (n // 4) * 2
    hero_obj["chill"] = hero_obj.get("chill", 0) + n
    app._log(f"{app._side_label(hero_obj) or '单位'} 寒冷+{n}")


def add_snow(app, hero_obj, n, side):
    """施加雪：需存在寒冷；集满 3 层触发雪崩"""
    if hero_obj.get("chill", 0) <= 0:
        return
    hero_obj["snow"] = hero_obj.get("snow", 0) + n
    app._log(f"{app._side_label(hero_obj) or '单位'} 雪+{n}")
    trigger_avalanche(app, hero_obj, side)


def trigger_avalanche(app, hero_obj, side):
    """雪崩：减少 3 层雪，造成 16 点攻击，再获得 1 层雪"""
    neutral = {"atk": 0, "chill": 0, "statuses": []}
    while hero_obj.get("snow", 0) >= 3:
        hero_obj["snow"] -= 3
        deal(app, neutral, ("hero", side), 16)
        hero_obj["snow"] += 1


def check_snow(app, hero_obj):
    """寒冷被破除时雪同步消散"""
    if hero_obj.get("chill", 0) <= 0:
        hero_obj["snow"] = 0


def remove_chill(app, hero_obj, n):
    hero_obj["chill"] = max(0, hero_obj.get("chill", 0) - n)
    check_snow(app, hero_obj)


def add_charge(app, hero_obj, n, rounds):
    """施加电感：层数叠加，取最长回合"""
    hero_obj["charge"] = hero_obj.get("charge", 0) + n
    hero_obj["charge_rounds"] = max(hero_obj.get("charge_rounds", 0), rounds)
    app._log(f"{app._side_label(hero_obj) or '单位'} 电感+{n}")


# ---------- 能量 ----------
def energy_of(app, side):
    return app.mana if side == "mine" else app.enemy_mana


def gain_energy(app, side, n):
    if side == "mine":
        app.mana = min(app.MAX_MANA, app.mana + n)
    else:
        app.enemy_mana = min(app.MAX_MANA, app.enemy_mana + n)
    app._log(f"{'我方' if side == 'mine' else '敌方'} 能量+{n}")


def lose_energy(app, side, n):
    if side == "mine":
        app.mana = max(0, app.mana - n)
    else:
        app.enemy_mana = max(0, app.enemy_mana - n)
    app._log(f"{'我方' if side == 'mine' else '敌方'} 能量-{n}")


# ---------- 生命 / 格挡 ----------
def _halved(hero_obj, n):
    """低迷：获得格挡与恢复生命值效果减半"""
    if any(st["name"] == "低迷" for st in hero_obj.get("statuses", [])):
        return n // 2
    return n


def heal(app, hero_obj, n):
    """恢复生命，返回实际恢复量"""
    n = _halved(hero_obj, max(0, n))
    before = hero_obj["hp"]
    hero_obj["hp"] = min(hero_obj["max_hp"], hero_obj["hp"] + n)
    gain = hero_obj["hp"] - before
    if gain > 0:
        app._spawn_heal_fx(f"+{gain}", app._unit_target(hero_obj))
        app._log(f"{app._side_label(hero_obj) or '单位'} +{gain}")
    return gain


def damage_hp(app, hero_obj, n):
    """纯伤害：直接扣血（无视格挡/防御/免疫），返回实际损失"""
    n = max(0, n)
    before = hero_obj["hp"]
    hero_obj["hp"] = max(0, hero_obj["hp"] - n)
    loss = before - hero_obj["hp"]
    if loss > 0:
        app._spawn_dmg_fx(f"-{loss}", app._unit_target(hero_obj))
        app._log(f"{app._side_label(hero_obj) or '单位'} -{loss}")
    return loss


def gain_block(app, hero_obj, n):
    gain = _halved(hero_obj, n)
    hero_obj["block"] = hero_obj.get("block", 0) + gain
    if gain:
        app._log(f"{app._side_label(hero_obj) or '单位'} 获得{gain}格挡")


def gain_true_block(app, hero_obj, n):
    hero_obj["true_block"] = hero_obj.get("true_block", 0) + n
    if n:
        app._log(f"{app._side_label(hero_obj) or '单位'} 获得{n}真实格挡")


def gain_absorb(app, hero_obj, n):
    hero_obj["absorb"] = hero_obj.get("absorb", 0) + n
    if n:
        app._log(f"{app._side_label(hero_obj) or '单位'} 获得{n}吸收")


def gain_immune(app, hero_obj, n):
    hero_obj["immune"] = hero_obj.get("immune", 0) + n
    if n:
        app._log(f"{app._side_label(hero_obj) or '单位'} 获得{n}免疫")


def add_attack(app, hero_obj, n, rounds=None):
    """临时提升/削减攻击力（n 可正可负），rounds 为持续回合"""
    hero_obj["atk"] = hero_obj.get("atk", 0) + n
    if rounds:
        name = "攻击提升" if n >= 0 else "攻击削减"
        add_status(app, hero_obj, name, rounds)
        st = _find_status(hero_obj, name)
        if st is not None:
            st["amount"] = st.get("amount", 0) + n


def add_defense(app, hero_obj, n, rounds=None):
    hero_obj["def"] = hero_obj.get("def", 0) + n
    if rounds:
        name = "防御提升" if n >= 0 else "防御削减"
        add_status(app, hero_obj, name, rounds)
        st = _find_status(hero_obj, name)
        if st is not None:
            st["amount"] = st.get("amount", 0) + n


def add_pursuit(app, hero_obj, level, rounds):
    """追击等级叠加，rounds 为持续回合"""
    hero_obj["pursuit"] = hero_obj.get("pursuit", 0) + level
    add_status(app, hero_obj, "追击", rounds)
    st = _find_status(hero_obj, "追击")
    if st is not None:
        st["level"] = st.get("level", 0) + level


def _find_status(hero_obj, name):
    for st in hero_obj.get("statuses", []):
        if st["name"] == name:
            return st
    return None


# ---------- 卡牌特征 ----------
ELEMENT_EMOJIS = ("🧊", "🤢", "⚡️", "😈", "👿")


def is_attack_card(card):
    """是否攻击类卡牌（致盲限制使用）"""
    if card.get("category") == "攻击卡":
        return True
    if card.get("category") == "基本卡" and "攻击" in card.get("desc", ""):
        return True
    return False


def has_element(card, emoji):
    return emoji in card.get("name", "") or emoji in card.get("desc", "")


def card_element(card):
    """返回卡牌所属元素（🧊/🤢/⚡️/😈/👿），无则 None"""
    for e in ELEMENT_EMOJIS:
        if has_element(card, e):
            return e
    return None


def card_has(card, *subs):
    desc = card.get("desc", "")
    return any(s in desc for s in subs)
