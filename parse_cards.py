# -*- coding: utf-8 -*-
"""
卡牌数据解析脚本
================
将 卡牌数据.txt 解析为 cards.json。
规则：按分类标题分段；条目以空行分隔；首行为卡名行（名称 + N费 + 可选回合/血量），
后续行为描述（可多行）。
"""
import json
import os
import re

CATEGORIES = ["基本卡", "攻击卡", "防御卡", "魔法卡", "状态卡", "装备卡", "造物卡"]
# 分类 → 卡牌类型（与游戏现有类型字段对应）
TYPE_MAP = {"装备卡": "equip", "造物卡": "craft"}

CN_NUM = {"一": 1, "两": 2, "二": 2, "三": 3, "四": 4, "五": 5,
          "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def cn_to_int(s):
    """中文数字/阿拉伯数字转 int；无限返回 -1；无法识别返回 0"""
    if s == "无限":
        return -1
    if s.isdigit():
        return int(s)
    if "十" in s:
        left, _, right = s.partition("十")
        return (CN_NUM.get(left, 1) if left else 1) * 10 + CN_NUM.get(right, 0)
    return CN_NUM.get(s, 0)


def parse_title_line(line):
    """解析卡名行：名称、费用、持续回合、血量。失败返回 None"""
    # 兼容「名称😈7费」「名称⚡️3费」等表情符号紧贴费用、无空格的写法
    m = re.match(r"^(.*?)(\d+)费(.*)$", line)
    if not m:
        return None
    info = {"name": m.group(1).strip(), "cost": int(m.group(2)),
            "duration": None, "health": None}
    rest = m.group(3)
    md = re.search(r"([\d一二两三四五六七八九十]+|无限)回合", rest)
    if md:
        info["duration"] = cn_to_int(md.group(1))
        rest = rest.replace(md.group(0), "", 1)
    mh = re.search(r"(\d+)(?:血|生命)", rest)
    if mh:
        info["health"] = int(mh.group(1))
        rest = rest.replace(mh.group(0), "", 1)
    # 卡名行剩余的混排文字（个别卡描述与卡名同行）并入描述
    info["extra"] = rest.strip(" ，,（）()。")
    return info


def parse(path):
    """解析 txt，返回 (卡牌列表, 错误列表)"""
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    sections = {}
    current = None
    buf = []
    for line in lines:
        s = line.strip()
        if s in CATEGORIES or s == "角色":
            if current and buf:
                sections[current] = buf
            current = s if s in CATEGORIES else None
            buf = []
        elif current:
            buf.append(line.rstrip())
    if current and buf:
        sections[current] = buf

    cards, errors = [], []
    for cat, buf in sections.items():
        # 条目切分：匹配"名称 N费"的行为卡名行，其后的行为描述（直至下一卡名行）
        entries, cur = [], []
        for line in buf:
            s = line.strip()
            if s == "":
                continue
            if re.match(r"^.+?\d+费", s):
                if cur:
                    entries.append(cur)
                cur = [s]
            elif cur:
                cur.append(s)
        if cur:
            entries.append(cur)
        for e in entries:
            info = parse_title_line(e[0])
            if info is None:
                errors.append(f"[{cat}] 无法解析：{e[0]}")
                continue
            info["category"] = cat
            info["type"] = TYPE_MAP.get(cat, "normal")
            desc_parts = []
            if info.get("extra"):
                desc_parts.append(info["extra"])
            desc_parts.extend(e[1:])
            info["desc"] = "\n".join(desc_parts)
            info.pop("extra", None)
            cards.append(info)
    return cards, errors


# ---------- 效果自动提取 ----------
# 含条件词的卡为复杂卡，本轮暂不提取效果（进未实装清单，后续逐个确认）
COND_WORDS = ("若", "如果", "再次", "下回合", "下个回合", "下下回合", "至多",
              "每回合", "立即", "下一张", "上一张", "前两",
              "随机", "蓄力", "触发", "处于", "存在", "消耗其", "复制", "翻倍",
              "链接", "召唤", "失效", "平均分配", "净化", "清除", "延迟", "暂停",
              "安放", "判定", "致盲", "束缚", "冻结", "嘲讽", "吸引", "吸取",
              "换取", "降低", "减少", "提升", "增加", "冷却", "选择", "手雷",
              "冲锋", "击退", "沉默", "耗尽", "腐蚀", "复活", "进化", "能量")

EFFECT_PATTERNS = [
    # (正则, 字段名, 值提取：int 取第一组数字，callable 接收 match)
    (r"对目标造成(\d+)点攻击", "attack", int),
    (r"造成(\d+)点攻击", "attack", int),
    (r"对目标造成(\d+)点伤害", "damage", int),
    (r"造成(\d+)点伤害", "damage", int),
    (r"对目标造成(\d+)点真实攻击", "true_attack", int),
    (r"造成(\d+)点真实攻击", "true_attack", int),
    (r"造成(\d+)点生命吸取", "lifesteal", int),
    (r"获得(\d+)点真实格挡", "gain_true_block", int),
    (r"获得(\d+)点(?:普通)?格挡", "gain_block", int),
    (r"恢复(\d+)点生命", "heal", int),
    (r"施加(\d+)层流血", "bleed", int),
    (r"施加(\d+)层寒冷", "chill", int),
    (r"施加(\d+)层毒", "poison", int),
    (r"施加(\d+)层电感", "charge", int),
    (r"获得掩体效果", "gain_mask", lambda m: 1),
    (r"破除目标(\d+)点格挡", "break_block", int),
    (r"对所有敌人造成(\d+)点攻击", "aoe_attack", int),
]


def _cast(match, cast):
    """按 cast 提取值：int 取第一组，callable 传 match"""
    if cast is int:
        return int(match.group(1))
    return cast(match)


def extract_effect(card):
    """从描述提取基础效果字段；含条件词或提取为空则返回 None"""
    desc = card["desc"]
    if any(w in desc for w in COND_WORDS):
        return None
    eff = {}
    for pattern, key, cast in EFFECT_PATTERNS:
        m = re.search(pattern, desc)
        if m:
            eff[key] = _cast(m, cast)
    return eff if eff else None


if __name__ == "__main__":
    base = os.path.dirname(os.path.abspath(__file__))
    cards, errors = parse(os.path.join(base, "卡牌数据.txt"))
    unknown = []
    for c in cards:
        c["effect"] = extract_effect(c)
        if c["effect"] is None:
            unknown.append(c["name"])
    out = os.path.join(base, "cards.json")
    with open(out, "w", encoding="utf-8") as f:
        json.dump(cards, f, ensure_ascii=False, indent=2)
    done = len(cards) - len(unknown)
    print(f"解析完成：{len(cards)} 张 → {out}")
    print(f"已提取效果：{done} 张；未实装（复杂卡）：{len(unknown)} 张")
    print("未实装清单：")
    for name in unknown:
        print("  " + name)
    if errors:
        print("\n无法解析：")
        for err in errors:
            print("  " + err)
