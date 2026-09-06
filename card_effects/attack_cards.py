# -*- coding: utf-8 -*-
"""攻击卡效果处理器"""
from . import register, helpers


def _t(app, t):
    return app._target_obj(t)


@register("斩杀", 5, max_targets=1)
def 斩杀(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        if tdef["hp"] < 24 and not helpers.has_status(tdef, "死舞"):
            tdef["hp"] = 0
            app._spawn_dmg_fx("-斩杀", t)
            app._spawn_unit_shake(("hero", t[1]) if t[0] == "hero" else ("board", t[1], t[2]))
        else:
            helpers.deal(app, me, t, 12)


@register("穷追猛打", 3, max_targets=1)
def 穷追猛打(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 7)
        helpers.add_status(app, _t(app, t), "低迷", 2)
    app._interrupt_charge(helpers.enemy_side(ctx["side"]))


@register("沉痛打击", 3, max_targets=1)
def 沉痛打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        cnt = len(tdef.get("statuses", []))
        for k in ("chill", "bleed", "poison", "charge", "snow", "block",
                  "true_block", "absorb", "immune", "mask", "vuln"):
            if tdef.get(k, 0) > 0:
                cnt += 1
        helpers.deal(app, me, t, 6 + cnt * 5)


@register("x光刃", 6, max_targets=1)
def x光刃(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 12)
        if tdef.get("block", 0) > 0 or tdef.get("true_block", 0) > 0:
            helpers.deal(app, me, t, 18)


@register("三连击", 3, max_targets=1)
def 三连击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        for dmg in (6, 2, 2):
            helpers.deal(app, me, t, dmg)


@register("恶魔爪击👿", 3)
def 恶魔爪击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    es = helpers.enemy_side(ctx["side"])
    # 计算攻击加成：敌人生命上限低于初始上限，每低 4 点攻击 +2
    def calc(hero_obj):
        lost = hero_obj.get("base_max_hp", hero_obj["max_hp"]) - hero_obj["max_hp"]
        return max(0, lost // 4) * 2
    ehero = helpers.enemy_hero(app, ctx["side"])
    bonus = calc(ehero)
    helpers.deal(app, me, ("hero", es), 6 + bonus)
    ehero["max_hp"] = max(1, ehero["max_hp"] - 4)
    ehero["hp"] = min(ehero["hp"], ehero["max_hp"])
    for i in range(len(helpers.enemy_board(app, ctx["side"]))):
        u = helpers.enemy_board(app, ctx["side"])[i]
        helpers.deal(app, me, ("board", es, i), 6 + calc(u))
        u["max_hp"] = max(1, u.get("max_hp", u["hp"]) - 4)
        u["hp"] = min(u["hp"], u["max_hp"])
    app._interrupt_charge(helpers.enemy_side(ctx["side"]))


@register("破碎重击", 2, max_targets=1)
def 破碎重击(app, ctx):
    for t in ctx["targets"]:
        tdef = _t(app, t)
        tdef["block"] = max(0, tdef.get("block", 0) - 12)
        tdef["absorb"] = max(0, tdef.get("absorb", 0) - 1)


@register("蝠咬😈", 3, max_targets=1)
def 蝠咬(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 3, lifesteal=True)
        helpers.add_status(app, _t(app, t), "蝠咬", 1)


@register("背水一战", 3, max_targets=1)
def 背水一战(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tside = t[1]
        energy = helpers.energy_of(app, tside)
        helpers.deal(app, me, t, energy * 3)
    app.energy_penalty[ctx["side"]] += 2


@register("血响之刃 😈", 7, max_targets=3, hits=3)
def 血响之刃(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        if tdef["hp"] < 24 and not helpers.has_status(tdef, "死舞"):
            tdef["hp"] = 0
            app._spawn_dmg_fx("-斩杀", t)
        else:
            helpers.deal(app, me, t, 14, lifesteal=True)
        helpers.add_stack(app, tdef, "bleed", 7)


@register("攻坚榴弹", 7, max_targets=1)
def 攻坚榴弹(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2)
        before = tdef.get("block", 0)
        tdef["block"] = max(0, before - 24)
        if before > 0 and tdef["block"] == 0:
            tdef["def"] = max(0, tdef["def"] - 6)


@register("RMA长钉", 2, max_targets=1)
def RMA长钉(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        dmg = helpers.deal(app, me, t, 6, ignore_def=True)
        if dmg <= 0:
            app._add_card_to_hand(ctx["side"], ctx["card"])


@register("锐爪", 4, max_targets=1)
def 锐爪(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        dmg = helpers.deal(app, me, t, 8)
        if dmg > 0:
            helpers.deal(app, me, t, 12)


@register("攻守兼备", 3, max_targets=1)
def 攻守兼备(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 8)
    helpers.gain_block(app, me, 8)


@register("重斩", 3, max_targets=1)
def 重斩(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        no_block = tdef.get("block", 0) <= 0
        tdef["block"] = max(0, tdef.get("block", 0) - 12)
        helpers.deal(app, me, t, 4 + (6 if no_block else 0))


@register("破伤箭", 4, max_targets=1)
def 破伤箭(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6, true=True, ignore_def=True, ignore_block=True)
        helpers.add_stack(app, _t(app, t), "bleed", 14)


@register("毒藤🤢", 4, max_targets=1)
def 毒藤(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6)
        helpers.add_stack(app, _t(app, t), "poison", 9)


@register("降维打击", 3, max_targets=2, hits=2)
def 降维打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6)
        helpers.add_status(app, _t(app, t), "弱化", 2)


@register("碎冰击🧊", 3, max_targets=1)
def 碎冰击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6)
        tdef = _t(app, t)
        # 冰爆：造成寒冷层数-4的攻击，并消除寒冷
        chill = tdef.get("chill", 0)
        helpers.deal(app, me, t, max(0, chill - 4))
        helpers.remove_chill(app, tdef, chill)


@register("幻影链😈", 4, max_targets=1)
def 幻影链(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 4, lifesteal=True)
        if helpers.has_status(tdef, "蝠咬"):
            helpers.deal(app, me, t, 4, lifesteal=True)
            helpers.add_status(app, tdef, "弱化", 1)


@register("坠冰🧊", 3, max_targets=1)
def 坠冰(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6)
        helpers.add_chill(app, _t(app, t), 9, t[1])


@register("处决", 7, max_targets=1)
def 处决(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 22, true=True, ignore_def=True)


@register("岩崩锤", 2, max_targets=1)
def 岩崩锤(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, me["def"] * 3)
    me["def"] = max(0, me["def"] - 1)
    if me["def"] > 2:
        app._add_card_to_hand(ctx["side"], ctx["card"])


@register("回旋", 5, max_targets=1)
def 回旋(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 4)
        helpers.add_status(app, _t(app, t), "低迷", 1)
        # 下回合对同一目标再造成 10 点，若造成伤害再造成 14 点
        target = t
        app._add_pending(1, lambda: _回旋_followup(app, me, target))


def _回旋_followup(app, me, target):
    dmg = helpers.deal(app, me, target, 10)
    if dmg > 0:
        helpers.deal(app, me, target, 14)


@register("箭雨", 4, max_targets=1)
def 箭雨(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        for _ in range(4):
            helpers.deal(app, me, t, 2)


@register("噩梦撕咬😈", 3, max_targets=1)
def 噩梦撕咬(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2, lifesteal=True)
        helpers.add_stack(app, tdef, "bleed", 6)
        helpers.add_status(app, tdef, "蝠咬", 1)


@register("肉斩骨断😈", 4)
def 肉斩骨断(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_status(app, me, "死舞", 1)
    # 状态结束后获得 3 回合虚弱（借由死舞结束的联动，见 _tick_statuses）


@register("祭祀😈", 1, max_targets=1)
def 祭祀(app, ctx):
    me = helpers.hero(app, ctx["side"])
    lost = me.get("base_max_hp", me["max_hp"]) - me["max_hp"]
    me["max_hp"] = max(1, me["max_hp"] - 4)
    me["hp"] = min(me["hp"], me["max_hp"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 4 + (lost // 4), lifesteal=True)


@register("双面刃", 4, max_targets=1)
def 双面刃(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 8)
        helpers.deal(app, me, t, 6, true=True)


@register("莫诺的制裁", 12, max_targets=1)
def 莫诺的制裁(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 52)


@register("弱点重击", 1, max_targets=1)
def 弱点重击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2)
        if helpers.has_status(tdef, "虚弱") or helpers.has_status(tdef, "低迷"):
            helpers.deal(app, me, t, 10)


@register("追加打击", 2, max_targets=1)
def 追加打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2)
        if tdef.get("damaged_this_turn", False):
            helpers.deal(app, me, t, 10)


@register("冰锥🧊", 1, max_targets=1)
def 冰锥(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2)
        if tdef.get("chill", 0) > 0:
            helpers.add_chill(app, tdef, 6, t[1])


@register("趁人之危", 2, max_targets=1)
def 趁人之危(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.lose_energy(app, t[1], 1)
        if helpers.has_status(tdef, "虚弱"):
            helpers.deal(app, me, t, 10)


@register("强袭", 4, max_targets=2, hits=2)
def 强袭(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 11, true=True)
        tdef["vuln"] = tdef.get("vuln", 0) + 2


@register("骨钉", 2, max_targets=1)
def 骨钉(app, ctx):
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.add_status(app, tdef, "低迷", 1)
        helpers.add_stack(app, tdef, "bleed", 8)


@register("冰连刺🧊", 4, max_targets=1)
def 冰连刺(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        bonus = 4 if tdef.get("chill", 0) > 0 else 0
        for _ in range(2):
            helpers.deal(app, me, t, 6 + bonus)


@register("正义审判", 3, max_targets=1)
def 正义审判(app, ctx):
    me = helpers.hero(app, ctx["side"])
    base_max = me.get("base_max_hp", me["max_hp"])
    for t in ctx["targets"]:
        helpers.deal(app, me, t, me["max_hp"] - base_max)


@register("星辰穿刺", 6, max_targets=1)
def 星辰穿刺(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        # 破除一件装备与一种有益效果（简化：清除一个正向状态）
        tside = t[1]
        equips = app.hero_equips if tside == "mine" else app.enemy_equips
        if equips:
            equips.pop()
        for st in list(tdef.get("statuses", [])):
            if st["name"] in ("攻击提升", "防御提升", "免疫", "嘲讽", "追击", "死舞"):
                tdef["statuses"].remove(st)
                break
        helpers.deal(app, me, t, 8, true=True)


@register("连锁闪电⚡️", 3, max_targets=3, hits=3)
def 连锁闪电(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        dmg = helpers.deal(app, me, t, 7)
        if dmg > 0:
            helpers.add_charge(app, tdef, 1, 1)


@register("毒针🤢", 2, max_targets=1)
def 毒针(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 2)
        helpers.add_stack(app, tdef, "poison", 3)
        # 引爆一次毒伤
        _引爆毒伤(app, tdef, t)


@register("十万伏特⚡️", 5, max_targets=1)
def 十万伏特(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        for _ in range(5):
            helpers.deal(app, me, t, 1)


@register("冰霜打击🧊", 8, max_targets=3, hits=3)
def 冰霜打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 16)
        helpers.add_chill(app, tdef, 8, t[1])
        helpers.add_status(app, tdef, "弱化", 2)
        helpers.add_status(app, tdef, "低迷", 2)


@register("闪电 ⚡️", 9, max_targets=1)
def 闪电(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 18)
        helpers.add_charge(app, tdef, 5, 1)
        helpers.add_defense(app, tdef, -2, 3)


@register("离子反应⚡️", 3)
def 离子反应(app, ctx):
    me = helpers.hero(app, ctx["side"])
    es = helpers.enemy_side(ctx["side"])
    for t in helpers.enemy_units(app, ctx["side"]):
        tdef = _t(app, t)
        if tdef.get("charge", 0) > 0:
            helpers.deal(app, me, t, 3)
            # 下回合若仍处电感再造成 5 点
            target = t
            app._add_pending(1, lambda: _离子后续(app, me, target))


def _离子后续(app, me, target):
    tdef = _t(app, target)
    if tdef.get("charge", 0) > 0:
        helpers.deal(app, me, target, 5)


@register("破伤风穿刺", 3, max_targets=1)
def 破伤风穿刺(app, ctx):
    for t in ctx["targets"]:
        tdef = _t(app, t)
        # 触发 7 层流血：消耗 7 层造成 7 点
        n = min(7, tdef.get("bleed", 0))
        if n > 0:
            tdef["bleed"] -= n
            helpers.damage_hp(app, tdef, n)
        if tdef.get("bleed", 0) > 0:
            helpers.add_stack(app, tdef, "bleed", 14)


@register("铁棘刺爪", 4, max_targets=1)
def 铁棘刺爪(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 4)
        helpers.add_stack(app, tdef, "bleed", 12)
        helpers.add_status(app, tdef, "放血", 2)


@register("梦魇之刺😈", 7, max_targets=1)
def 梦魇之刺(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 5, lifesteal=True)
        helpers.add_stack(app, tdef, "bleed", 25)
        helpers.add_status(app, tdef, "致盲", 1)


@register("鬼魂勾😈", 6, max_targets=1)
def 鬼魂勾(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 4, lifesteal=True)
        helpers.add_status(app, tdef, "鬼链", 2)
        if helpers.has_status(tdef, "虚弱"):
            helpers.deal(app, me, t, 6, lifesteal=True)
    app._interrupt_charge(helpers.enemy_side(ctx["side"]))


@register("暗影伏击😈", 4, max_targets=1)
def 暗影伏击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        target = t
        # 若下回合未受伤害，下下回合造成 8 点攻击 + 16 流血（简化：延迟两回合触发）
        app._add_pending(2, lambda: _暗影伏击触发(app, me, target))


def _暗影伏击触发(app, me, target):
    tdef = _t(app, target)
    if not tdef.get("damaged_this_turn", False):
        helpers.deal(app, me, target, 8)
        helpers.add_stack(app, tdef, "bleed", 16)


@register("死亡镰刀😈", 3, max_targets=1)
def 死亡镰刀(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 7)
        helpers.add_stack(app, tdef, "bleed", 9)
        helpers.add_defense(app, tdef, -2, 1)


@register("迅捷打击", 3, max_targets=1)
def 迅捷打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    helpers.add_pursuit(app, me, 3, 2)
    for t in ctx["targets"]:
        helpers.deal(app, me, t, 6)
    app._interrupt_charge(helpers.enemy_side(ctx["side"]))


@register("双重打击", 3, max_targets=2, hits=2)
def 双重打击(app, ctx):
    me = helpers.hero(app, ctx["side"])
    targets = ctx["targets"]
    if targets:
        dmg = helpers.deal(app, me, targets[0], 5)
        if dmg > 0 and len(targets) > 1:
            helpers.deal(app, me, targets[1], 6)


@register("寒霜刺🧊", 4, max_targets=1)
def 寒霜刺(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        tdef = _t(app, t)
        helpers.deal(app, me, t, 6)
        if tdef.get("chill", 0) > 8:
            helpers.remove_chill(app, tdef, 7)
            helpers.deal(app, me, t, 7)
            helpers.add_snow(app, tdef, 1, t[1])


@register("毒针🤢", 3, max_targets=1)
def 毒针_3费(app, ctx):
    for t in ctx["targets"]:
        tdef = _t(app, t)
        if tdef.get("def", 0) == 0 and tdef.get("block", 0) <= 0:
            helpers.add_stack(app, tdef, "poison", 6)
            helpers.add_status(app, tdef, "毒停滞", 1)
            if tdef.get("bleed", 0) > 0:
                helpers.add_status(app, tdef, "放血", 2)


@register("延时性破片手雷", 3, max_targets=1)
def 延时性破片手雷(app, ctx):
    me = helpers.hero(app, ctx["side"])
    for t in ctx["targets"]:
        target = t
        app._add_pending(1, lambda: _手雷引爆(app, me, target))


def _手雷引爆(app, me, target):
    tdef = _t(app, target)
    helpers.deal(app, me, target, 4)
    if tdef.get("bleed", 0) > 0:
        # 触发其所有流血
        n = tdef.get("bleed", 0)
        tdef["bleed"] = 0
        helpers.damage_hp(app, tdef, n)
    else:
        helpers.add_stack(app, tdef, "bleed", 12)


def _引爆毒伤(app, tdef, target):
    """引爆一次毒伤：立即造成毒层攻击并 -3 层毒"""
    if tdef.get("poison", 0) > 0:
        dmg = tdef["poison"]
        helpers.damage_hp(app, tdef, dmg)
        tdef["poison"] = max(0, tdef["poison"] - 3)
