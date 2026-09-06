# -*- coding: utf-8 -*-
"""造物卡效果处理器（站场单位的立即效果与状态标注，回合效果见 card_viewer 钩子）"""
from . import register, helpers


def _u(app, side):
    b = app.board_mine if side == "mine" else app.board_enemy
    return b[-1] if b else None


def _add_extra(app, side, base, n):
    """为多召唤造物补充额外同款单位"""
    b = app.board_mine if side == "mine" else app.board_enemy
    for _ in range(n):
        b.append(dict(base))


@register("高效制冷机🧊", 8)
def 高效制冷机(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "制冷机"
        u["phase"] = 0


@register("十字军", 7)
def 十字军(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "十字军"
        _add_extra(app, ctx["side"], u, 1)


@register("亡灵石像😈", 7)
def 亡灵石像(app, ctx):
    me = helpers.hero(app, ctx["side"])
    me["hp"] = max(0, me["hp"] - 8)
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "亡灵石像"
        u["inactive"] = 3


@register("能量玩偶", 4)
def 能量玩偶(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "能量玩偶"


@register("蜉蝣电击器⚡️", 2)
def 蜉蝣电击器(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "蜉蝣电击器"


@register("死亡毒蛛🤢", 4)
def 死亡毒蛛(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "死亡毒蛛"


@register("幽影蝙蝠😈", 4)
def 幽影蝙蝠(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "幽影蝙蝠"
        _add_extra(app, ctx["side"], u, 3)


@register("极寒冰龙 🧊", 6)
def 极寒冰龙(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "极寒冰龙"


@register("九翼天使", 6)
def 九翼天使(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "九翼天使"


@register("天外来物", 5)
def 天外来物(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "天外来物"
        u["beacon"] = False


@register("科学怪人", 4)
def 科学怪人(app, ctx):
    u = _u(app, ctx["side"])
    if u:
        u["craft_kind"] = "科学怪人"
        u["research"] = 1
