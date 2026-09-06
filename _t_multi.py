# -*- coding: utf-8 -*-
"""多目标出牌 + 造物互击 的端到端验证"""
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from headless_engine import BattleEngine
import card_viewer as cv

e = BattleEngine()
app = e.app

# 敌方先站一个造物，制造多目标场景
ci = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '能量玩偶'))
app.board_enemy.append({"card": cv.CARDS[ci], "hp": 11, "max_hp": 11,
                        "atk": 0, "can_attack": True, "rounds": 3, "x": 0, "y": 0})

# 我方上「血响之刃 😈」（至多 3 目标）
bi = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '血响之刃 😈'))
app.hand.append(("mine", bi))
app.mana = 12

print("敌方造物数:", len(app.board_enemy), " 敌方 hp:", app.enemy_hero['hp'])
r = e.play(len(app.hand) - 1, [["hero", "enemy"], ["board", "enemy", 0]])
print("\n=== 多目标出牌（选 2 个：敌方英雄 + 敌方造物）===")
print("error:", r.get('error'))
if r.get('state'):
    print("敌方 hp:", r['state']['enemy']['hp'])
    print("敌方造物:", [(u['name'], u['hp']) for u in r['state']['board_enemy']])
    print("log:")
    for m in r['state']['log']:
        print("   ", m)

# 超上限应被拒绝
e2 = BattleEngine()
a2 = e2.app
a2.hand.append(("mine", bi))
a2.mana = 12
r2 = e2.play(len(a2.hand) - 1, [["hero", "enemy"]] * 4)
print("\n超上限（选 4 个，最多 3）:", r2.get('error'))

# 我方造物打敌方造物
e3 = BattleEngine()
a3 = e3.app
ti = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '十字军'))
a3.hand.append(("mine", ti))
a3.mana = 12
a3.board_enemy.append({"card": cv.CARDS[ci], "hp": 11, "max_hp": 11,
                       "atk": 0, "can_attack": True, "rounds": 3, "x": 0, "y": 0})
e3.play(len(a3.hand) - 1)
r3 = e3.attack(0, [["board", "enemy", 0]])
print("\n=== 我方造物打敌方造物 ===")
print("error:", r3.get('error'))
if r3.get('state'):
    print("敌方造物剩余:", [(u['name'], u['hp']) for u in r3['state']['board_enemy']])
    print("log:", r3['state']['log'][-3:])
