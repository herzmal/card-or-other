# -*- coding: utf-8 -*-
"""魔法卡效果处理器"""
from . import register, helpers


@register("振奋", 4)
def 振奋(app, ctx):
    me = helpers.hero(app, ctx["side"])
    # 清除所有负面状态（不含正面效果）
    negative = ("虚弱", "弱化", "加强版弱化", "低迷", "易伤", "致盲", "冻结",
                "极寒", "束缚", "蝠咬", "毒停滞", "放血", "鬼链", "嘲讽")
    me["statuses"] = [st for st in me["statuses"] if st["name"] not in negative]
    for k in ("chill", "bleed", "poison", "charge", "snow"):
        me[k] = 0
    helpers.add_status(app, me, "虚弱", 1)


@register("特殊操作", 3)
def 特殊操作(app, ctx):
    me = helpers.hero(app, ctx["side"])
    es = helpers.enemy_side(ctx["side"])
    # 简化：随机触发两张基本卡的效果（对敌方主角色）
    import random
    from . import resolve
    basic = [c for c in app.CARDS if c["category"] == "基本卡"]
    if basic:
        for c in random.sample(basic, min(2, len(basic))):
            targets = [("hero", es)] if ("目标" in c.get("desc", "") or "对敌" in c.get("desc", "")) else []
            resolve(app, c, ctx["side"], targets)


@register("医者仁心", 1)
def 医者仁心(app, ctx):
    # 恢复所有目标（敌我）6 点，自身额外 4 点
    for side in ("mine", "enemy"):
        helpers.heal(app, helpers.hero(app, side), 6)
    helpers.heal(app, helpers.hero(app, ctx["side"]), 4)


@register("雪崩🧊", 3)
def 雪崩(app, ctx):
    es = helpers.enemy_side(ctx["side"])
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        if tdef.get("snow", 0) > 0:
            tdef["snow"] = 0
            helpers.trigger_avalanche(app, tdef, t[1])


@register("暴风雪🧊", 6)
def 暴风雪(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_chill(app, tdef, 13, t[1])
        helpers.add_snow(app, tdef, 3, t[1])


@register("没落", 4, max_targets=1)
def 没落(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        tdef["card_void"] = tdef.get("card_void", 0) + 1
        helpers.add_status(app, tdef, "虚弱", 2)


@register("不详的征兆", 1)
def 不详的征兆(app, ctx):
    es = helpers.enemy_side(ctx["side"])
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_attack(app, tdef, 6, 2)
    helpers.gain_energy(app, es, 3)
    def 触发():
        helpers.lose_energy(app, es, 999)
        for t in helpers.enemy_units(app, ctx["side"]):
            helpers.deal(app, helpers.enemy_hero(app, ctx["side"]), t, 20, force=True)
    app._add_pending(3, 触发)


@register("火花四溅⚡️", 2)
def 火花四溅(app, ctx):
    me = helpers.hero(app, ctx["side"])
    es = helpers.enemy_side(ctx["side"])
    count = 1 + len(helpers.enemy_board(app, ctx["side"]))
    dmg = count * 3
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.deal(app, me, t, dmg, ignore_def=True)


@register("鬼毒阵🤢", 7)
def 鬼毒阵(app, ctx):
    es = helpers.enemy_side(ctx["side"])
    helpers.add_status(app, helpers.enemy_hero(app, ctx["side"]), "鬼毒", 3)


@register("荆刺🤢", 2, max_targets=1)
def 荆刺(app, ctx):
    for t in ctx["targets"]:
        helpers.add_status(app, app._target_obj(t), "荆刺", 2)


@register("冰爆🧊", 1, max_targets=1)
def 冰爆(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        chill = tdef.get("chill", 0)
        helpers.deal(app, me, t, max(0, chill - 4))
        helpers.remove_chill(app, tdef, chill)


@register("归一", 2, max_targets=1)
def 归一(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        energy = helpers.energy_of(app, t[1])
        helpers.heal(app, me, energy * 2)


@register("强光", 2)
def 强光(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_status(app, app._target_obj(t), "致盲", 1)


@register("持续疗法", 7)
def 持续疗法(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, 8)
    helpers.add_status(app, me, "持续疗法", 3)


@register("小雪球🧊", 2)
def 小雪球(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_snow(app, app._target_obj(t), 1, t[1])


@register("大雪球🧊", 4)
def 大雪球(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_chill(app, tdef, 4, t[1])
        helpers.add_snow(app, tdef, 2, t[1])


@register("雪盲症🧊", 1, max_targets=1)
def 雪盲症(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        if tdef.get("chill", 0) > 14 or tdef.get("snow", 0) > 0:
            helpers.add_status(app, tdef, "致盲", 1)


@register("毒绞🤢", 5, max_targets=1)
def 毒绞(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.deal(app, me, t, 10)
        helpers.add_stack(app, tdef, "poison", 8)
        app._add_pending(1, lambda: helpers.add_stack(app, tdef, "poison", 6))


@register("炙阳", 1)
def 炙阳(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for side in ("mine", "enemy"):
        helpers.add_status(app, helpers.hero(app, side), "炙阳", 2)


@register("彻骨冰寒", 4, max_targets=1)
def 彻骨冰寒(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.deal(app, me, t, 7)
        helpers.add_status(app, tdef, "冻结", 1)
        target = t
        app._add_pending(1, lambda: _彻骨后续(app, me, target))


def _彻骨后续(app, me, target):
    tdef = app._target_obj(target)
    if tdef.get("chill", 0) > 20:
        helpers.remove_chill(app, tdef, 20)
        helpers.deal(app, me, target, 22)


@register("冰冻🧊", 4)
def 冰冻(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_status(app, app._target_obj(t), "冻结", 3)


@register("压制", 2, max_targets=1)
def 压制(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        if helpers.has_status(tdef, "弱化"):
            tdef["statuses"] = [st for st in tdef["statuses"] if st["name"] != "弱化"]
            helpers.add_status(app, tdef, "加强版弱化", 3)
        else:
            helpers.add_status(app, tdef, "弱化", 1)


@register("备用医药", 3)
def 备用医药(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, 10)
    app._add_pending(1, lambda: helpers.heal(app, me, 4))


@register("圣石", 3)
def 圣石(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_immune(app, me, 1)
    helpers.add_status(app, me, "虚弱", 1)


@register("巫毒法术🤢", 4)
def 巫毒法术(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_stack(app, tdef, "poison", 9)
        helpers.add_status(app, tdef, "毒停滞", 2)


@register("雷电乌云⚡️", 7, max_targets=1)
def 雷电乌云(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.add_status(app, app._target_obj(t), "雷电乌云", 3)


@register("引雷⚡️", 6, max_targets=1)
def 引雷(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        charge = tdef.get("charge", 0)
        tdef["charge"] = 0
        helpers.deal(app, me, t, charge * 4)


@register("感染🤢", 2, max_targets=1)
def 感染(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        if tdef.get("bleed", 0) > 0:
            helpers.add_stack(app, tdef, "poison", 10)


@register("亡灵的嚎哭 😈", 4)
def 亡灵的嚎哭(app, ctx):
    es = helpers.enemy_side(ctx["side"])
    helpers.add_status(app, helpers.enemy_hero(app, ctx["side"]), "亡灵的嚎哭", 3)


@register("血色祭典😈", 1)
def 血色祭典(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["max_hp"] = max(1, me["max_hp"] - 6)
    me["hp"] = min(me["hp"], me["max_hp"])
    helpers.heal(app, me, 8)
    helpers.add_status(app, me, "虚弱", 1)


@register("侵蚀虫毒🤢", 3, max_targets=1)
def 侵蚀虫毒(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_stack(app, tdef, "poison", 5)
        tside = t[1]
        def 腐蚀():
            equips = app.hero_equips if tside == "mine" else app.enemy_equips
            if equips:
                equips.pop()
        app._add_pending(1, 腐蚀)


@register("陨落咒术", 6, max_targets=1)
def 陨落咒术(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_defense(app, me, -4, 3)
    me["charging"] = True
    for t in ctx["targets"]:
        target = t
        def 爆发():
            helpers.deal(app, me, target, 40)
            helpers.add_status(app, me, "虚弱", 6)
            me["charging"] = False
        app._add_pending(3, 爆发, tag="charge", side=ctx["side"])


@register("奥术魔典", 2)
def 奥术魔典(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["charging"] = True
    def 强化():
        helpers.add_attack(app, me, 4, 1)
        helpers.add_defense(app, me, 4, 1)
        me["charging"] = False
    app._add_pending(2, 强化, tag="charge", side=ctx["side"])


@register("冰川时代🧊", 10)
def 冰川时代(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_status(app, app._target_obj(t), "极寒", 3)
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "冰系节能", 3)


@register("汇流凝冰 🧊", 3)
def 汇流凝冰(app, ctx):
    me = helpers.hero(app, ctx["side"])
    if me.get("chill", 0) > 0:
        helpers.remove_chill(app, me, 12)
        helpers.gain_block(app, me, 7)


@register("冰雪制造术🧊", 1, max_targets=1)
def 冰雪制造术(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        if tdef.get("chill", 0) >= 12:
            helpers.remove_chill(app, tdef, 12)
            helpers.add_snow(app, tdef, 2, t[1])


@register("沙尘暴", 5)
def 沙尘暴(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_status(app, tdef, "掩体状态", 2)
        helpers.add_status(app, tdef, "致盲", 1)
