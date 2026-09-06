# -*- coding: utf-8 -*-
"""
卡牌效果引擎
============
统一注册与调度所有卡牌的效果处理器。

设计：
  - HANDLERS[(名称, 费用)] -> 处理器函数 fn(app, ctx)
  - CARD_META[(名称, 费用)] -> 元数据（max_targets / hits / friendly_target / needs_target）
  - resolve(app, card, side, targets) 为统一调度入口，返回是否已实装
"""

HANDLERS = {}   # (name, cost) -> fn
CARD_META = {}  # (name, cost) -> {"max_targets":.., "hits":.., ...}


def register(name, cost, **meta):
    """装饰器：注册卡牌效果处理器及其元数据"""
    def deco(fn):
        HANDLERS[(name, cost)] = fn
        CARD_META[(name, cost)] = meta
        return fn
    return deco


def lookup(card):
    """根据卡牌字典查找处理器，找不到返回 None"""
    return HANDLERS.get((card["name"], card.get("cost")))


def meta_of(card):
    """取得卡牌元数据（无则空 dict）"""
    return CARD_META.get((card["name"], card.get("cost")), {})


def merge_meta(cards):
    """把注册的元数据合并进卡牌列表（load_cards 后调用）"""
    for c in cards:
        meta = meta_of(c)
        for k, v in meta.items():
            c.setdefault(k, v)
    return cards


def resolve(app, card, side, targets):
    """统一调度：执行卡牌效果，返回 True 表示已实装。"""
    fn = lookup(card)
    if fn is None:
        return False
    ctx = {"card": card, "side": side, "targets": list(targets)}
    # 记录当前结算的卡牌/阵营，供伤害结算读取元素、装备联动等信息
    prev_card = getattr(app, "_current_card", None)
    prev_side = getattr(app, "_current_side", None)
    app._current_card = card
    app._current_side = side
    try:
        fn(app, ctx)
    finally:
        app._current_card = prev_card
        app._current_side = prev_side
    app._check_game_over()
    return True


# 导入各分类模块，触发装饰器注册
from . import helpers  # noqa: E402,F401
from . import basic_cards  # noqa: E402,F401
from . import attack_cards  # noqa: E402,F401
from . import defense_cards  # noqa: E402,F401
from . import magic_cards  # noqa: E402,F401
from . import status_cards  # noqa: E402,F401
from . import equip_cards  # noqa: E402,F401
from . import craft_cards  # noqa: E402,F401
