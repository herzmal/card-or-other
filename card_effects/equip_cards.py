# -*- coding: utf-8 -*-
"""装备卡效果处理器（仅处理装备时的立即效果与状态标注，持续效果见 card_viewer 钩子）"""
from . import register, helpers


def _eq(app, side):
    g = app.hero_equips if side == "mine" else app.enemy_equips
    return g[-1] if g else None


@register("狂刀战斧", 4)
def 狂刀战斧(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["triggers"] = 0


@register("饮血剑😈", 4)
def 饮血剑(app, ctx):
    pass


@register("圣光盾", 4)
def 圣光盾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.gain_true_block(app, me, 12)
    helpers.add_status(app, me, "嘲讽", 2)


@register("鬼魂锁😈", 4)
def 鬼魂锁(app, ctx):
    ehero = helpers.enemy_hero(app, ctx["side"])
    helpers.add_status(app, ehero, "鬼链", 3)


@register("悟言盾", 5)
def 悟言盾(app, ctx):
    helpers.gain_block(app, helpers.hero(app, ctx["side"]), 10)


@register("冰冻鱼叉🧊", 4)
def 冰冻鱼叉(app, ctx):
    pass


@register("恶魂十字架😈", 2)
def 恶魂十字架(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["first_demon"] = True


@register("元防", 5)
def 元防(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["def_bonus"] = 3
        helpers.hero(app, ctx["side"])["def"] += 3


@register("寒冰剑🧊", 3)
def 寒冰剑(app, ctx):
    pass


@register("荆棘甲", 6)
def 荆棘甲(app, ctx):
    helpers.gain_true_block(app, helpers.hero(app, ctx["side"]), 8)


@register("树人图腾", 7)
def 树人图腾(app, ctx):
    pass


@register("所罗门的指环", 7)
def 所罗门的指环(app, ctx):
    pass


@register("护身的古老符文", 8)
def 护身的古老符文(app, ctx):
    pass


@register("七字刀", 4)
def 七字刀(app, ctx):
    pass


@register("毒牙匕首🤢", 2)
def 毒牙匕首(app, ctx):
    pass


@register("闪电匕首⚡️", 2)
def 闪电匕首(app, ctx):
    pass


@register("电击棒⚡️", 3)
def 电击棒(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["atk_bonus"] = 3
        helpers.hero(app, ctx["side"])["atk"] += 3


@register("铁血指虎", 4)
def 铁血指虎(app, ctx):
    pass


@register("锯齿", 3)
def 锯齿(app, ctx):
    pass


@register("德古拉的斗篷😈", 6)
def 德古拉的斗篷(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["atk_bonus"] = 2
        helpers.hero(app, ctx["side"])["atk"] += 2


@register("恶灵的契约😈", 3)
def 恶灵的契约(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["lost"] = 0


@register("冰息铠甲🧊", 4)
def 冰息铠甲(app, ctx):
    pass


@register("β.火箭发射器", 4)
def β火箭发射器(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["ammo"] = 0


@register("指挥军刀", 3)
def 指挥军刀(app, ctx):
    e = _eq(app, ctx["side"])
    if e:
        e["atk_bonus"] = 4
        helpers.hero(app, ctx["side"])["atk"] += 4
