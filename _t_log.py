# -*- coding: utf-8 -*-
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
from headless_engine import BattleEngine
import card_viewer as cv

e = BattleEngine()
st = e.state()
print("手牌:")
for i, c in enumerate(st["hand"]):
    print(f"  [{i}] {c['name']} 费{c['cost']} {c['category']} 需目标={c['needs_target']} desc={c['desc'][:40]}")
print("初始log:", st["log"])

done = False
for i, c in enumerate(st["hand"]):
    if c["needs_target"] and c["cost"] <= st["mana"]:
        print(f"\n>>> 打出 [{i}] {c['name']} 目标=敌方英雄")
        r = e.play(i, [["hero", "enemy"]])
        if "error" in r:
            print("ERR", r["error"])
            continue
        print("log 之后:")
        for m in r["state"]["log"]:
            print("   ", m)
        print("events:", r["state"]["events"])
        done = True
        break
if not done:
    print("没有可打的需目标卡")
    for i, c in enumerate(st["hand"]):
        if c["cost"] <= st["mana"]:
            print(f"\n>>> 打出 [{i}] {c['name']} ({c['category']})")
            r = e.play(i)
            if "error" in r:
                print("ERR", r["error"])
                continue
            for m in r["state"]["log"]:
                print("   ", m)
            print("board_mine:", r["state"]["board_mine"])
            print("equips_mine:", r["state"]["equips_mine"])
            break
