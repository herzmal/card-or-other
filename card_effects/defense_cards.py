# -*- coding: utf-8 -*-
"""防御卡效果处理器"""
from . import register, helpers


@register("圣盾", 4)
def 圣盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, 8)
    helpers.gain_block(app, me, 12)


@register("钢铁意志", 7)
def 钢铁意志(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_true_block(app, me, 10)
    helpers.add_defense(app, me, 6, 3)
    helpers.add_status(app, me, "减伤", 1)


@register("弹反盾", 3)
def 弹反盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 12)
    me["reflect"] = 8


@register("强心剂", 3)
def 强心剂(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, 24)
    helpers.add_status(app, me, "加强版弱化", 2)
    helpers.add_status(app, me, "虚弱", 2)


@register("反刺盾", 5)
def 反刺盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 16)
    me["shield_flag"] = {"name": "反刺盾", "block": me["block"]}


@register("缠绕护体", 4, max_targets=1)
def 缠绕护体(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 2, lifesteal=True)
    helpers.gain_block(app, me, 10)
    helpers.gain_absorb(app, me, 1)


@register("教条立场", 6)
def 教条立场(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_defense(app, me, 5, 1)
    helpers.heal(app, me, 12)


@register("协同治疗", 2)
def 协同治疗(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "治疗增效", 1)


@register("医疗盾", 5)
def 医疗盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 16)
    me["shield_flag"] = {"name": "医疗盾", "block": me["block"]}


@register("沉梦护盾", 4)
def 沉梦护盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 6)
    helpers.gain_absorb(app, me, 2)
    helpers.add_status(app, me, "筑梦", 2)


@register("死亡图腾", 3)
def 死亡图腾(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "庇护", 99)


@register("神龟", 4)
def 神龟(app, ctx):
    me = helpers.hero(app, ctx["side"])
    enemy = helpers.enemy_hero(app, ctx["side"])
    stolen = enemy.get("def", 0)
    enemy["def"] = max(0, enemy["def"] - stolen)
    helpers.add_defense(app, me, stolen, 2)
    helpers.gain_immune(app, me, 1)
    helpers.add_status(app, me, "虚弱", 2)


@register("临时格挡", 3)
def 临时格挡(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 14)
    me["temp_block"] = True


@register("大地之盾", 3)
def 大地之盾(app, ctx):
    helpers.gain_true_block(app, helpers.hero(app, ctx["side"]), 11)


@register("壳状防御", 3)
def 壳状防御(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_true_block(app, me, 6)
    helpers.gain_block(app, me, 10)


@register("草木皆兵", 6)
def 草木皆兵(app, ctx):
    me = helpers.hero(app, ctx["side"])
    lost = me["max_hp"] - me["hp"]
    helpers.gain_block(app, me, lost)


@register("脂化反应", 1)
def 脂化反应(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_defense(app, me, -2, 3)
    me["max_hp"] = max(1, me["max_hp"] - 12)
    me["hp"] = min(me["hp"], me["max_hp"])
    helpers.gain_true_block(app, me, 14)
    helpers.gain_block(app, me, 10)


@register("永恒锻造", 4)
def 永恒锻造(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["base_def"] = me.get("base_def", 0) + 2
    me["def"] = me.get("def", 0) + 2


@register("菲比修斯的魔力护盾", 5)
def 菲比修斯的魔力护盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 6)
    helpers.add_status(app, me, "魔力防护", 2)


@register("强身健体", 8)
def 强身健体(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "强身健体", 3)


@register("血清", 3)
def 血清(app, ctx):
    me = helpers.hero(app, ctx["side"])
    _clear_one(app, me)
    helpers.add_status(app, me, "虚弱", 2)


@register("罗马防御", 5)
def 罗马防御(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_block(app, me, 30)
    helpers.add_status(app, me, "嘲讽", 1)


@register("群体疗法", 5)
def 群体疗法(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "群体疗法", 3)


@register("紧急包扎", 2)
def 紧急包扎(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.heal(app, me, 12)
    app._add_pending(1, lambda: helpers.damage_hp(app, me, 8))


@register("寒冰疗法🧊", 4)
def 寒冰疗法(app, ctx):
    helpers.add_status(app, helpers.hero(app, ctx["side"]), "寒冰疗法", 3)


@register("格挡反击", 2)
def 格挡反击(app, ctx):
    helpers.hero(app, ctx["side"])["格挡反击"] = True


def _clear_one(app, me):
    """清除一种状态或层数"""
    if me.get("statuses"):
        me["statuses"].pop(0)
        return
    for k in ("chill", "bleed", "poison", "charge", "snow"):
        if me.get(k, 0) > 0:
            me[k] = 0
            return
