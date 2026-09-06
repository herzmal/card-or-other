# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from headless_engine import BattleEngine
import card_viewer as cv

e = BattleEngine()
app = e.app
# 手动塞一张造物卡进手牌（手牌条目格式：(side, 卡池索引)）
ci = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '能量玩偶'))
app.hand.append(("mine", ci))
app.mana = 12
idx = len(app.hand) - 1
print("造物卡:", cv.CARDS[ci]['name'], "health:", cv.CARDS[ci].get('health'))
r = e.play(idx)
print("error:", r.get('error'))
st = r['state']
print("board_mine:", st['board_mine'])
print("log:", st['log'])

# 造物攻击
if st['board_mine']:
    print("\n>>> 造物攻击敌方英雄")
    app._resolve_target_attack(("board", "mine", 0), [("hero", "enemy")])
    st2 = e.state()
    print("enemy hp:", st2['enemy']['hp'])
    print("log:", st2['log'])
    print("board_mine:", st2['board_mine'])
