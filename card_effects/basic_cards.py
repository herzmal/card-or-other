# -*- coding: utf-8 -*-
"""基本卡效果处理器"""
from . import register, helpers


@register("坚盾", 2)
def 坚盾(app, ctx):
    helpers.add_defense(app, helpers.hero(app, ctx["side"]), 3, 1)


@register("绝地反击", 0)
def 绝地反击(app, ctx):
    side = ctx["side"]
    me = helpers.hero(app, side)
    helpers.damage_hp(app, me, 12)
    if side == "mine":
        app.mana = min(app.MAX_MANA, app.mana + 2)
    else:
        app.enemy_mana = min(app.MAX_MANA, app.enemy_mana + 2)


@register("攻势一", 1, max_targets=1)
def 攻势一(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 4)


@register("掩体", 2)
def 掩体(app, ctx):
    helpers.hero(app, ctx["side"])["mask"] = 1


@register("治疗", 1)
def 治疗(app, ctx):
    helpers.heal(app, helpers.hero(app, ctx["side"]), 4)


@register("背刺", 2, max_targets=1)
def 背刺(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 5, true=True)


@register("血怒", 1)
def 血怒(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_attack(app, me, 4, 1)
    me["hp"] = max(0, me["hp"] - 8)
    me["max_hp"] = max(1, me["max_hp"] - 8)
    me["hp"] = min(me["hp"], me["max_hp"])
    helpers.add_status(app, me, "虚弱", 1)


@register("攻势二", 1, max_targets=1)
def 攻势二(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 4)
        if app.play_history and app.play_history[-1] == "攻势一":
            helpers.deal(app, me, t, 2)


@register("盾", 1)
def 盾(app, ctx):
    helpers.gain_block(app, helpers.hero(app, ctx["side"]), 4)


@register("回收利用", 1)
def 回收利用(app, ctx):
    side = ctx["side"]
    if app.played:
        card, px, py = app.played.pop()
        app._add_card_to_hand(side, card)
        app._show_notice(f"回收了【{card['name']}】")


@register("雪", 2, max_targets=1)
def 雪(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_chill(app, tdef, 4, helpers.target_owner_side(t))
        helpers.add_snow(app, tdef, 1, helpers.target_owner_side(t))


@register("血脉", 0)
def 血脉(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["hp"] = max(0, me["hp"] - 6)
    me["max_hp"] += 4
    me["hp"] = min(me["hp"], me["max_hp"])


@register("毒药🤢", 1, max_targets=1)
def 毒药(app, ctx):
    for t in ctx["targets"]:
        tdef = app._target_obj(t)
        helpers.add_stack(app, tdef, "poison", 5)


@register("攻势3", 2, max_targets=1)
def 攻势3(app, ctx):
    me = helpers.hero(app, ctx["side"])
    combo = (len(app.play_history) >= 2
             and app.play_history[-2] == "攻势一"
             and app.play_history[-1] == "攻势二")
    for t in ctx["targets"]:
        dmg = 8 + (4 if combo else 0)
        helpers.deal(app, me, t, dmg)
        if combo:
            helpers.add_stack(app, app._target_obj(t), "bleed", 5)
    # 可打断蓄力
    app._interrupt_charge(helpers.enemy_side(ctx["side"]))
