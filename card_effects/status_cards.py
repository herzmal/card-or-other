# -*- coding: utf-8 -*-
"""状态卡效果处理器"""
from . import register, helpers


@register("狂热😈", 8, max_targets=1)
def 狂热(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_status(app, tdef, "狂热", 3)
        target = t
        def 触发():
            if helpers.has_status(tdef, "狂热"):
                tdef["max_hp"] = max(1, tdef["max_hp"] - 32)
                tdef["hp"] = min(tdef["hp"], tdef["max_hp"])
                helpers.add_status(app, me, "虚弱", 3)
        app._add_pending(3, 触发)


@register("沙尘", 3)
def 沙尘(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        helpers.add_status(app, tdef, "掩体状态", 1)
        tdef["vuln"] = tdef.get("vuln", 0) + 1


@register("弱化药剂", 5)
def 弱化药剂(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_status(app, app._target_obj(t), "弱化", 3)


@register("禁言", 3, max_targets=1)
def 禁言(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        tdef["card_void"] = tdef.get("card_void", 0) + 1


@register("能力提升", 2)
def 能力提升(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_attack(app, me, 2, 2)
    helpers.add_defense(app, me, 2, 2)


@register("能量剥夺", 3)
def 能量剥夺(app, ctx):
    helpers.lose_energy(app, helpers.enemy_side(ctx["side"]), 3)


@register("捕兽夹", 2, max_targets=1)
def 捕兽夹(app, ctx):
    for t in ctx["targets"]:
        app._target_obj(t)["捕兽夹"] = True


@register("缴械", 2, max_targets=1)
def 缴械(app, ctx):
    for t in ctx["targets"]:
        tside = t[1]
        equips = app.hero_equips if tside == "mine" else app.enemy_equips
        if equips:
            equips.pop()


@register("净化", 6)
def 净化(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["statuses"] = []
    for k in ("chill", "bleed", "poison", "charge", "snow", "vuln"):
        me[k] = 0
    me["atk"] = me.get("base_atk", 0)
    me["def"] = me.get("base_def", 0)
    helpers.heal(app, me, 8)
    helpers.add_status(app, me, "净化免疫", 1)


@register("法术沉淀", 2, max_targets=1)
def 法术沉淀(app, ctx):
    for t in ctx["targets"]:
        helpers.add_status(app, app._target_obj(t), "法术沉淀", 1)


@register("修补", 2)
def 修补(app, ctx):
    helpers.hero(app, ctx["side"])["block_persist"] = True


@register("枷锁", 2, max_targets=1)
def 枷锁(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_status(app, tdef, "弱化", 1)
        helpers.add_status(app, tdef, "虚弱", 2)


@register("泳潮悲歌", 6)
def 泳潮悲歌(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, me["max_hp"] // 2)
    helpers.add_pursuit(app, me, 3, 3)
    helpers.add_defense(app, me, 5, 3)
    helpers.add_status(app, me, "致盲", 1)
    app.energy_penalty[ctx["side"]] += 4


@register("极寒🧊", 2)
def 极寒(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_status(app, app._target_obj(t), "极寒", 2)
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "冰系强化", 99)


@register("反制", 3)
def 反制(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "反制", 1)


@register("重铸", 2)
def 重铸(app, ctx):
    total = app.mana + app.enemy_mana
    each = total // 2
    app.mana = each
    app.enemy_mana = each


@register("血红酒😈", 1)
def 血红酒(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "血红酒", 1)


@register("禁令", 4, max_targets=1)
def 禁令(app, ctx):
    for t in ctx["targets"]:
        app._target_obj(t)["next_card_void"] = True


@register("解毒剂", 2)
def 解毒剂(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["poison"] = max(0, me.get("poison", 0) - 12)


@register("热熔剂", 2)
def 热熔剂(app, ctx):
    helpers.remove_chill(app, helpers.hero(app, ctx["side"]), 12)


@register("修罗的终极毒药🤢", 10, max_targets=1)
def 修罗的终极毒药(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_stack(app, tdef, "poison", 14)
        target = t
        app._add_pending(3, lambda: _修罗判定(app, target))


def _修罗判定(app, target):
    tdef = app._target_obj(target)
    if tdef.get("poison", 0) > 60:
        tdef["hp"] = 0
        app._spawn_dmg_fx("-斩杀", target)


@register("导体⚡️", 2, max_targets=1)
def 导体(app, ctx):
    for t in ctx["targets"]:
        helpers.add_charge(app, app._target_obj(t), 3, 1)


@register("充能闪电球⚡️", 3, max_targets=1)
def 充能闪电球(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        target = t
        def 触发():
            helpers.deal(app, me, target, 9)
            helpers.add_status(app, app._target_obj(target), "束缚", 1)
        app._add_pending(1, 触发)


@register("绝缘体", 2)
def 绝缘体(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["charge"] = 0
    me["charge_rounds"] = 0


@register("电云⚡️", 2)
def 电云(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        helpers.add_charge(app, app._target_obj(t), 1, 2)


@register("高压⚡️", 2)
def 高压(app, ctx):
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = app._target_obj(t)
        if tdef.get("charge", 0) > 0:
            tdef["charge_rounds"] = tdef.get("charge_rounds", 0) + 1


@register("加速时钟", 2)
def 加速时钟(app, ctx):
    for u in helpers.board(app, ctx["side"]):
        if u.get("rounds") not in (None, -1):
            u["rounds"] = max(0, u["rounds"] - 1)


@register("莫诺的望远镜", 2)
def 莫诺的望远镜(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["next_attack_bonus"] = me.get("next_attack_bonus", 0) + 5 + me.get("pursuit", 0)


@register("兵书", 2)
def 兵书(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "兵书", 2)
