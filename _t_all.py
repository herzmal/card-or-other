# -*- coding: utf-8 -*-
import sys, io, json
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from headless_engine import BattleEngine
import card_viewer as cv

e = BattleEngine()
app = e.app

# 1) 多目标解析
print("=== 多目标卡 max_targets ===")
for n in ("血响之刃 😈", "降维打击", "冰霜打击🧊", "双重打击", "弱点重击", "坚盾", "能量玩偶"):
    c = next((x for x in cv.CARDS if x['name'] == n), None)
    if c:
        print(f"  {n}: needs_target={cv.needs_target(c)} max={cv.max_targets(c)}")

# 2) 造物上场 + 攻击（用十字军，有 atk 4）
ci = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '十字军'))
app.hand.append(("mine", ci))
app.mana = 12
r = e.play(len(app.hand) - 1)
print("\n=== 造物上场 ===")
print("error:", r.get('error'))
print("board_mine:", json.dumps(r['state']['board_mine'], ensure_ascii=False))
print("log:", r['state']['log'])

# 3) 造物攻击接口
r2 = e.attack(0, [["hero", "enemy"]])
print("\n=== 造物攻击 ===")
print("error:", r2.get('error'))
if r2.get('state'):
    print("敌方 hp:", r2['state']['enemy']['hp'])
    print("log:", r2['state']['log'])
    print("board_mine:", json.dumps(r2['state']['board_mine'], ensure_ascii=False))
# 再次攻击应被拒绝
r3 = e.attack(0, [["hero", "enemy"]])
print("重复攻击:", r3.get('error'))

# 4) 攻击卡日志顺序
e2 = BattleEngine()
a2 = e2.app
ai = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '弱点重击'))
a2.hand.append(("mine", ai))
a2.mana = 12
r4 = e2.play(len(a2.hand) - 1, [["hero", "enemy"]])
print("\n=== 攻击卡日志 ===")
print("log:", r4['state']['log'])

# 5) 多目标出牌（血响之刃，至多3）
e3 = BattleEngine()
a3 = e3.app
bi = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '血响之刃 😈'))
a3.hand.append(("mine", bi))
a3.mana = 12
r5 = e3.play(len(a3.hand) - 1, [["hero", "enemy"]])
print("\n=== 多目标卡（选1个目标）===")
print("error:", r5.get('error'))
if r5.get('state'):
    print("敌方 hp:", r5['state']['enemy']['hp'], "我方 hp:", r5['state']['hero']['hp'])
    print("log:", r5['state']['log'])

# 6) 装备详情字段
e4 = BattleEngine()
a4 = e4.app
ei = cv.CARDS.index(next(c for c in cv.CARDS if c['name'] == '电击棒⚡️'))
a4.hand.append(("mine", ei))
a4.mana = 12
r6 = e4.play(len(a4.hand) - 1)
print("\n=== 装备上场 ===")
print("equips_mine:", json.dumps(r6['state']['equips_mine'], ensure_ascii=False))
print("log:", r6['state']['log'])
