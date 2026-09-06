# -*- coding: utf-8 -*-
"""
卡牌对战窗口
============
运行方式：python card_viewer.py

流程与功能：
    1. 轮到自己回合时：先获得能量并抽 2 张卡牌（飞行动画），再进入打牌阶段
    2. 打牌阶段可出牌；点击"结束回合"时判定弃牌机制（手牌超 9 张需先弃牌）
    3. 双方共用全卡池抽牌堆（不再绘制牌堆图形，战场左侧改为战斗记录框，
       记录双方出牌与造成的伤害/回血/状态效果）；手牌重叠堆叠，鼠标悬停上移
    4. 装备栏：我方在手牌区正上方，敌方在手牌区下方（靠近中心区），
       悬停缩略块显示整张卡牌详情；手牌区下端为数据栏
       （生命/攻击/防御/格挡/状态，悬停状态栏显示效果说明）
    5. 战场单位：我方主角色框在记录栏右侧，敌方主角色框在画面右侧对立；
       站场造物围绕对应主角框生成（描述含名字/剩余回合/血量）
    6. 造物卡打出后围绕本方主角框站场（有攻击值/血量，无防御），
       在场且处于本回合即可点击进入攻击状态，每回合限攻击一次；
       已攻击过的造物变暗显示；造物有持续回合数，到期同装备一样
       弃置到出牌区（单位框随之消失）
    7. 造物实体显示血条（卡牌中偏下，按当前血量比例填充，绿→黄→红，
       中央显示 4/8 式血量数字）与剩余回合；攻击值显示在悬停放大详情中；
       卡牌左下/右下角不再显示数字，装备/造物的类型特征显示在卡牌右上角
    8. 目标选择交互：点击攻击卡（或可攻击的造物）后拖动光标出现指向箭头，
       悬停合法目标时目标框亮黄高亮；单目标卡点击目标直接施法；
       多目标卡点击目标分配一段攻击（同一目标可重复，至多 N 个目标，
       右键撤销最后一段），点「施法」结算；点空白或「取消」退出施法；
       除特殊卡外不能对友方单位使用
    9. 攻击伤害公式：对主角色每段伤害 = 攻击值 + 自身攻击力 - 对方防御力，
       受格挡抵挡；对造物为全额伤害（造物无防御/格挡）；
       造物攻击造物为单向伤害（目标不反击）；格挡每次轮到自己回合时清 0
    10. 装备提供攻击力/防御力加成（有时限，到期自动移除），
        数据栏以"0+1"格式显示加成；部分卡牌打出时获得格挡
    11. 状态伤害不受攻击力加成、受自身防御力减免，分"越过格挡"与"不越过格挡"两类
    12. 战斗特效：扣血红色数字显示在对应受击单位身上、回血绿色数字显示在
        回复者身上（自由落体渐隐）；格挡抵挡成功：盾牌震动（尚有剩余）/
        盾牌碎裂（仍有扣血）
    13. 左上角显示总回合数；对方回合由你代为操作；对方卡牌当前正面显示
"""
import ctypes
import json
import math
import os
import random
import re
import time
import tkinter as tk

from card_effects import merge_meta, resolve
from card_effects import helpers as _fx

# 提高 Windows 高分屏下的显示清晰度
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass

# 卡牌分类对应的主题颜色（边框、色带）
CATEGORY_COLORS = {
    "基本卡": "#9d9d9d",
    "攻击卡": "#e05555",
    "防御卡": "#4a90d9",
    "魔法卡": "#b45ce0",
    "状态卡": "#55b96a",
    "装备卡": "#ff9800",
    "造物卡": "#26c6da",
}

# 类型图标颜色（装备 / 造物）
TYPE_COLORS = {"equip": "#ff9800", "craft": "#26c6da"}
TYPE_NAMES = {"equip": "装备", "craft": "造物"}

# 状态效果定义：
#   hp            每回合基础伤害值（负数为扣血）
#   heal          每回合恢复的生命值（正数）
#   bypass_block  是否越过格挡直接扣血
#   atk           持续期间攻击力修正
# 状态伤害不受攻击力加成，但受持有者防御力减免
STATUS_EFFECTS = {
    "中毒": {"desc": "每回合造成 1 点伤害（受防御减免，越过格挡）",
             "hp": -1, "bypass_block": True},
    "灼烧": {"desc": "每回合造成 2 点伤害（受防御减免，不越过格挡）",
             "hp": -2, "bypass_block": False},
    "流血": {"desc": "每回合造成 3 点伤害（受防御减免，不越过格挡）",
             "hp": -3, "bypass_block": False},
    "虚弱": {"desc": "无法使用文字描述中会获得虚弱的卡牌"},
    "弱化": {"desc": "造成的攻击值降低 4 点"},
    "加强版弱化": {"desc": "造成的攻击值降低 6 点"},
    "低迷": {"desc": "获得格挡与恢复生命值效果减半"},
    "易伤": {"desc": "受到攻击时额外受到易伤层数的攻击"},
    "追击": {"desc": "每次造成攻击额外附带一段追击等级的攻击"},
    "致盲": {"desc": "无法使用攻击卡牌"},
    "冻结": {"desc": "每受到 4 层寒冷额外叠加 2 层寒冷"},
    "极寒": {"desc": "暂停寒冷层数自然消减，每回合获得 4 层寒冷"},
    "嘲讽": {"desc": "敌方单体攻击被强制吸引"},
    "死舞": {"desc": "生命值无论如何不会低于 1"},
    "束缚": {"desc": "仅能使用攻击卡与防御卡"},
    "荆刺": {"desc": "每使用一张卡牌便被施加 3 层毒"},
    "鬼毒": {"desc": "每回合被施加 8 层毒"},
    "放血": {"desc": "每回合结束自动触发 4 层流血"},
    "鬼链": {"desc": "每回合被吸取 3 点生命上限"},
    "蝠咬": {"desc": "受到的每次攻击来源 +4"},
    "筑梦": {"desc": "吸收效果发挥作用时获得 6 点格挡"},
    "魔力防护": {"desc": "不受到元素卡牌（🧊/🤢/⚡️）造成的攻击"},
    "庇护": {"desc": "生命值归 0 时立即复活并恢复 9 点生命"},
    "减伤": {"desc": "本回合受到的攻击减少 20%"},
    "治疗增效": {"desc": "本回合恢复生命卡牌耗能 -1"},
    "毒停滞": {"desc": "毒层自然消减暂停"},
    "净化免疫": {"desc": "免疫负面效果和状态"},
    "攻击提升": {"desc": "攻击力临时提升"},
    "攻击削减": {"desc": "攻击力临时削减"},
    "防御提升": {"desc": "防御力临时提升"},
    "防御削减": {"desc": "防御力临时削减"},
    "持续疗法": {"desc": "每回合恢复 8 点生命"},
    "强身健体": {"desc": "每回合生命上限 +8 并恢复 4 点生命"},
    "群体疗法": {"desc": "每回合恢复所有友方 5 点生命"},
    "寒冰疗法": {"desc": "每回合恢复 9 点生命并获得 6 层寒冷"},
    "炙阳": {"desc": "每回合对所有目标造成 6 点攻击"},
    "雷电乌云": {"desc": "每回合受到 7 点攻击并获得 2 层电感"},
    "亡灵的嚎哭": {"desc": "每回合攻击力 -3"},
    "狂热": {"desc": "3 个回合后减少 32 点生命上限"},
    "冰系强化": {"desc": "冰系卡牌攻击 +1"},
    "冰系节能": {"desc": "冰系卡牌耗能 -1"},
    "血红酒": {"desc": "😈系卡牌生命吸取 +3"},
    "兵书": {"desc": "《攻守兼备》/《穷追猛打》效果翻倍"},
    "掩体状态": {"desc": "受到的每次攻击变为 7 点"},
    "反制": {"desc": "受到超过 9 点伤害时反击所有敌人"},
    "法术沉淀": {"desc": "下一回合所有卡耗能 +1"},
}

def load_cards():
    """从 cards.json 加载卡牌数据（由 parse_cards.py 解析 卡牌数据.txt 生成）"""
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "cards.json")
    with open(path, encoding="utf-8") as f:
        return json.load(f)


# 全部卡牌（单一卡池，双方共用；字段：name/cost/category/type/desc/duration/health）
# 卡牌效果由 card_effects 包按卡名注册处理器；此处合并注册的元数据
CARDS = merge_meta(load_cards())
# 对方手牌是否背面显示（True 为背面，False 为正面，当前正面便于测试）
ENEMY_CARD_FACE_DOWN = False

MAX_MANA = 12           # 能量上限
TURN_MANA = 6           # 每个回合获得的能量
HAND_LIMIT = 9          # 手牌上限
DRAW_PER_TURN = 2       # 每回合抽牌数
INITIAL_HAND = 6        # 开局每方手牌数（双方各从全卡池发 6 张）

CARD_W, CARD_H = 150, 210           # 卡牌宽高
ZOOM_SCALE = 1.6                    # 选中放大倍数
HOVER_LIFT = 20                     # 悬停/选中卡牌上移像素
CANVAS_W, CANVAS_H = 1280, 1040     # 窗口尺寸

ROUND_BOX = (10, 2, 140, 30)        # 左上角总回合数
ENEMY_BOX = (40, 6, 1160, 282)      # 上方：对方手牌方框
ENEMY_Y = 22                        # 对方卡牌顶部纵坐标
BAR_E = (40, 292, 1160, 318)        # 敌方装备栏（对方手牌区下方，靠近中心区）
PLAY_AREA = (40, 320, 1160, 700)    # 中间：战场区

# 战场单位：我方主角色框在记录栏右侧，敌方主角色框在画面右侧对立；
# 站场造物围绕对应主角框排列（见 _craft_slots）
MINE_HERO_BOX = (235, 540, 435, 690)   # 我方主角色框（记录栏右侧）
ENEMY_HERO_BOX = (980, 350, 1160, 490)  # 敌方主角色框（右侧对立）
BOARD_GAP = 10                          # 造物实体间隙
BOARD_W, BOARD_H = 110, 154             # 造物实体尺寸（缩小版）
PLAYED_ANCHOR = (700, 400)              # 已出卡牌纪念堆中心（战场中央偏上）
BAR_M = (40, 708, 1160, 736)        # 我方装备栏（我方手牌区正上方）
HAND_BOX = (40, 742, 1160, 1018)    # 下方：我方手牌方框
HAND_Y = 758                        # 我方卡牌顶部纵坐标

ENERGY_BOX_E = (50, 44, 145, 104)   # 对方能量小方框（手牌区左侧）
ENERGY_BOX_M = (50, 750, 145, 810)  # 我方能量小方框（手牌区左侧）

LOG_BOX = (40, 340, 225, 690)       # 战斗记录框（原抽牌堆位置区域）
LOG_MAX = 40                        # 战斗记录最多保留条数

HAND_AREA = (160, 1120)             # 手牌卡牌区的左右边界

BTN_X1, BTN_X2 = 1180, 1260         # 右侧按钮区域
END_TURN_BTN = (1180, 60, 1260, 110)    # 结束回合按钮（全局常驻）
PLAY_BTN = (1180, 140, 1260, 190)       # 打出按钮
CANCEL_BTN = (1180, 210, 1260, 260)     # 取消按钮

ANIM_FRAMES = 25                    # 抽牌动画总帧数
ANIM_INTERVAL = 20                  # 每帧间隔（毫秒）


def darken(hex_color, factor=0.55):
    """将十六进制颜色按比例变暗"""
    hex_color = hex_color.lstrip("#")
    r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
    r, g, b = (int(c * factor) for c in (r, g, b))
    return f"#{r:02x}{g:02x}{b:02x}"


def card_positions(n, area_x1, area_x2):
    """计算 n 张卡牌的横坐标列表：少时完全展开，多时重叠排列"""
    if n <= 1:
        return [area_x1]
    gap = min(150, (area_x2 - area_x1 - CARD_W) / (n - 1))
    return [area_x1 + i * gap for i in range(n)]


def needs_target(card):
    """判断卡牌是否需要选择目标：恢复自身类与群体类（含所有）不需要"""
    if "needs_target" in card:
        return bool(card["needs_target"])
    # 装备卡/造物卡：打出后进入装备栏/棋盘，永远不需要选择目标
    # （它们的描述常含"目标/对指定"等字样，之前会被关键词误判）
    cat = card.get("category", "")
    if cat in ("装备卡", "造物卡"):
        return False
    desc = card.get("desc", "")
    if desc.startswith("恢复") or "所有" in desc:
        return False
    return ("目标" in desc or "对敌" in desc or "对指定" in desc)


# 多目标卡：卡名 -> 可同时选择的目标数上限（描述无法稳定解析时的显式覆盖）
MULTI_TARGET_OVERRIDE = {
    "血响之刃 😈": 3,
    "降维打击": 2,
    "连锁闪电⚡️": 2,
    "冰霜打击🧊": 3,
    "双重打击": 2,
    "火花四溅⚡️": 3,
}

_CN_NUM = {"一": 1, "二": 2, "两": 2, "三": 3, "四": 4, "五": 5,
           "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}


def max_targets(card):
    """返回该卡一次施法可选择的目标数上限（1=单目标，0=无需选目标）。

    解析顺序：显式字段 > 显式覆盖表 > 描述正则 > 默认 1。
    """
    if "max_targets" in card:
        return int(card["max_targets"])
    name = card.get("name", "")
    if name in MULTI_TARGET_OVERRIDE:
        return MULTI_TARGET_OVERRIDE[name]
    if not needs_target(card):
        return 0
    desc = card.get("desc", "")
    m = re.search(r"(?:至多|最多)\s*(\d+|[一二两三四五六七八九十])\s*个", desc)
    if m:
        tok = m.group(1)
        return int(tok) if tok.isdigit() else _CN_NUM.get(tok, 1)
    if "再次选择一个目标" in desc:
        return 2
    return 1


def fmt_stat(base, total):
    """属性显示格式：基础值+加成（如 0+1；无加成只显示基础值）"""
    bonus = total - base
    if bonus > 0:
        return f"{base}+{bonus}"
    if bonus < 0:
        return str(total)
    return str(base)


def wrap_text(text, max_units=26):
    """按显示宽度折行（中文/emoji 计 2 单位，ASCII 计 1 单位）"""
    lines, cur, w = [], "", 0
    for ch in text:
        cw = 1 if ord(ch) < 128 else 2
        if w + cw > max_units:
            lines.append(cur)
            cur, w = ch, cw
        else:
            cur += ch
            w += cw
    if cur:
        lines.append(cur)
    return lines


class CardApp:
    """卡牌对战窗口主程序"""

    def __init__(self, root):
        self.root = root
        self.MAX_MANA = MAX_MANA
        self.CARDS = CARDS
        self.turn = "mine"          # 当前回合："mine" 我方 / "enemy" 对方
        self.round = 1              # 总回合数（双方各结束一个回合 +1）
        self.mana = TURN_MANA       # 我方能量（第一回合已获得）
        self.enemy_mana = 0         # 对方能量（其回合开始时获得）

        # 双方人物数据：生命 100；true_block 真实格挡 / absorb 吸收 /
        # immune 免疫伤害 / mask 掩体 / chill 寒冷 / bleed 流血 /
        # poison 毒 / charge 电感 / snow 雪 / pursuit 追击 均为层数或等级
        def _new_hero():
            return {"hp": 100, "max_hp": 100, "base_max_hp": 100,
                    "base_atk": 0, "atk": 0, "base_def": 0, "def": 0,
                    "block": 0, "true_block": 0, "absorb": 0, "immune": 0,
                    "mask": 0, "chill": 0, "bleed": 0, "poison": 0,
                    "charge": 0, "charge_rounds": 0, "snow": 0,
                    "vuln": 0, "pursuit": 0, "statuses": []}
        self.hero = _new_hero()
        self.enemy_hero = _new_hero()

        # 双方共用状态
        self.energy_penalty = {"mine": 0, "enemy": 0}   # 下回合能量获取惩罚
        self.play_history = []                          # 双方出牌记录（卡名）
        self.pending = []                               # 延迟效果 [{"turns":N,"fn":callable}]
        self._demon_played = {"mine": False, "enemy": False}  # 本回合已用😈卡

        # 手牌/抽牌堆：全卡池（包含全部卡牌，各一张）洗牌后先发双方手牌，
        # 其余全部进入共用抽牌堆，保证每张卡都会出现在牌局中
        pool = list(range(len(CARDS)))
        random.shuffle(pool)
        self.hand = [("mine", i) for i in pool[:INITIAL_HAND]]
        self.enemy_hand = [("enemy", i)
                           for i in pool[INITIAL_HAND:INITIAL_HAND * 2]]
        self.deck = [("mine", i) for i in pool[INITIAL_HAND * 2:]]
        self.log = []           # 战斗记录（双方出牌与造成的效果）
        self.played = []            # 战场上的卡牌 [(卡牌字典, x, y), ...]

        # 装备栏（元素为 {"card": 卡牌字典, "rounds": 剩余回合数}）
        self.hero_equips = []
        self.enemy_equips = []
        # 战场站场造物：元素为 {"card": 卡牌字典, "hp": 当前血量,
        #                      "atk": 攻击值, "can_attack": 本回合可否攻击,
        #                      "x": 横坐标, "y": 纵坐标}
        self.board_mine = []
        self.board_enemy = []

        self.selected = None        # 选中的手牌 ("mine"/"enemy", 位置索引)
        # 施法目标选择状态：None 或 {"src": 攻击来源, "mouse": 光标位置,
        #   "hover_target": 悬停目标}；src 为 ("hand", 位置) 或 ("board", 方, 索引)
        self.targeting = None
        self.board_hover = None     # 鼠标悬停的战场造物 ("mine"/"enemy", 索引)
        self.discard = None         # 弃牌模式 ("mine"/"enemy", 需弃几张)
        self.anim = None            # 抽牌动画状态
        self.fx = []                # 战斗特效列表
        self.game_over = None       # 游戏结束："win" 胜利 / "lose" 失败
        self.flash_msg = None       # 短暂显示的提示文字
        self.hand_hover = None      # 鼠标悬停的手牌 ("mine"/"enemy", 位置)
        self.hover_status = None    # 鼠标悬停的状态栏 "mine"/"enemy"
        self.hover_item = None      # 鼠标悬停的装备/造物 ("side", "kind", 索引)
        self.bar_item_rects = []    # 装备/造物缩略块矩形
        self.hand_rects = []        # 我方手牌矩形区域
        self.enemy_rects = []       # 对方手牌矩形区域
        self.buttons = []           # 当前按钮 [(x1, y1, x2, y2, 动作)]
        self.zoom_rect = None       # 放大卡牌的矩形区域

        self.root.title("卡牌对战")
        self.root.geometry(f"{CANVAS_W}x{CANVAS_H}")
        self.root.resizable(False, False)

        self.canvas = tk.Canvas(self.root, width=CANVAS_W, height=CANVAS_H,
                                bg="#1e1e1e", highlightthickness=0)
        self.canvas.pack()
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)
        self.canvas.bind("<Motion>", self.on_motion)

        # 开局我方第一回合：先抽 2 张卡牌（带动画），再进入打牌阶段
        self.draw()
        self._start_draw_animation("mine")

    # ---------- 数据辅助 ----------
    def _card_of(self, entry):
        """根据 (卡池, 索引) 取得卡牌数据字典（单一卡池）"""
        _, idx = entry
        return CARDS[idx]

    def _hand_over(self, side):
        """返回指定方手牌超出上限的张数（未超出为 0）"""
        hand = self.hand if side == "mine" else self.enemy_hand
        return max(0, len(hand) - HAND_LIMIT)

    def _bar_groups(self, side):
        """返回指定方的 (装备列表, 站场造物列表)"""
        if side == "mine":
            return self.hero_equips, self.board_mine
        return self.enemy_equips, self.board_enemy

    # ---------- 绘制入口 ----------
    def draw(self):
        """统一重绘整个画面"""
        self.canvas.delete("all")
        self.hand_rects = []
        self.enemy_rects = []
        self.buttons = []
        self.bar_item_rects = []
        self.zoom_rect = None

        # 左上角总回合数
        self._draw_round_counter()

        # 装备栏（我方在手牌区正上方，敌方在手牌区下方靠近中心区）
        self._draw_bars(BAR_E, self.enemy_equips, "enemy")
        self._draw_bars(BAR_M, self.hero_equips, "mine")

        self._draw_hand_box(ENEMY_BOX, "对方手牌", self.turn == "enemy")
        self._draw_hand_box(HAND_BOX, "我的手牌", self.turn == "mine")
        self._draw_mana_box(*ENERGY_BOX_E, self.enemy_mana,
                            self.turn == "enemy")
        self._draw_mana_box(*ENERGY_BOX_M, self.mana, self.turn == "mine")
        self._draw_status_bar(ENEMY_BOX, self.enemy_hero)
        self._draw_status_bar(HAND_BOX, self.hero)

        # 战斗记录框（原抽牌堆位置，记录双方出牌与效果）
        self._draw_log()

        # 对方手牌（选中或施法目标选择中时整体变暗）
        dim = self.selected is not None or self.targeting is not None
        self._draw_hand(self.enemy_hand, ENEMY_Y, dim, self.enemy_rects,
                        face_down=ENEMY_CARD_FACE_DOWN, side="enemy")

        # 我方手牌
        self._draw_hand(self.hand, HAND_Y, dim, self.hand_rects,
                        face_down=False, side="mine")

        # 战场区：已打出的随从卡与弃置的牌（正面朝上堆叠，持续显示）
        for card, px, py in self.played:
            self.draw_card(self.canvas, px, py, CARD_W, CARD_H, card)

        # 战场单位：双方主角色框 + 站场造物实体（含施法目标高亮）
        self._draw_board_units()

        # 抽牌动画：飞行中的卡牌
        self._draw_animation()

        # 选中状态：放大卡牌
        if self.selected is not None:
            side, pos = self.selected
            entry = (self.hand if side == "mine" else self.enemy_hand)[pos]
            if side == "enemy" and ENEMY_CARD_FACE_DOWN:
                self._draw_zoomed_card(None, back=True)
            else:
                self._draw_zoomed_card(self._card_of(entry))
        # 施法目标选择中：放大当前选中的卡牌（便于看清）
        if self.targeting is not None and self.targeting["src"][0] == "hand":
            pos = self.targeting["src"][1]
            hand = self.hand if self.turn == "mine" else self.enemy_hand
            if pos < len(hand):
                self._draw_zoomed_card(self._card_of(hand[pos]))

        self._draw_all_buttons()

        # 悬停浮层：状态栏说明 / 装备造物整卡详情
        self._draw_status_tooltip()
        self._draw_item_detail()

        # 战斗特效（扣血数字、盾牌震动/碎裂）
        self._draw_fx()

        # 战场造物悬停放大详情
        self._draw_board_detail()

        # 施法目标选择：指向箭头（最上层）
        self._draw_target_arrow()

        # 短暂提示（如"能量不足"）
        if self.flash_msg is not None:
            self.canvas.create_text(
                (PLAY_AREA[0] + PLAY_AREA[2]) / 2, PLAY_AREA[1] + 40,
                text=self.flash_msg, fill="#ff5555",
                font=("Microsoft YaHei", -22, "bold"))

        # 底部提示文字
        turn_name = "我方" if self.turn == "mine" else "对方"
        if self.discard is not None:
            side, need = self.discard
            who = "我方" if side == "mine" else "对方"
            tip = f"【{who}】手牌超出 {HAND_LIMIT} 张上限，请在弹出的窗口中完成弃牌（需弃 {need} 张）"
        elif self.targeting is not None:
            if self._max_targets() > 1:
                n = len(self.targeting["targets"])
                tip = (f"目标选择中：点击敌方单位分配一段攻击（已选 {n}/{self._src_hits()} 段，"
                       f"至多 {self._max_targets()} 个目标，同一目标可重复点击），"
                       f"右键撤销最后一段，点「施法」结算；点空白或「取消」退出")
            else:
                tip = "目标选择中：移动光标选择敌方单位（金色高亮），点击目标确定施法；点击空白或「取消」按钮退出"
        elif self.anim is not None:
            tip = f"当前回合：{turn_name} | 正在抽取 {len(self.anim['entries'])} 张卡牌……"
        elif self._hand_over(self.turn) > 0:
            tip = (f"当前回合：{turn_name} | 手牌已超过 {HAND_LIMIT} 张上限，"
                   f"本回合仍可出牌，点击结束回合时需弃掉超出部分")
        else:
            tip = (f"当前回合：{turn_name} | 每回合 +{TURN_MANA} 能量（上限 "
                   f"{MAX_MANA}）并抽 {DRAW_PER_TURN} 张 | 手牌上限 {HAND_LIMIT} "
                   f"| 悬停查看状态效果与装备详情")
        self.canvas.create_text(CANVAS_W / 2, CANVAS_H - 14, text=tip,
                                fill="#888888", font=("Microsoft YaHei", -12))

        # 游戏结束画面（最上层）
        if self.game_over is not None:
            self.canvas.create_rectangle(0, 0, CANVAS_W, CANVAS_H,
                                         fill="#000000", stipple="gray50",
                                         outline="")
            if self.game_over == "win":
                text, col = "游戏胜利！", "#ffd700"
            else:
                text, col = "游戏失败！", "#ff5555"
            self.canvas.create_text(CANVAS_W / 2, CANVAS_H / 2 - 40,
                                    text=text, fill=col,
                                    font=("Microsoft YaHei", -64, "bold"))
            self.canvas.create_text(CANVAS_W / 2, CANVAS_H / 2 + 30,
                                    text="对局结束，请关闭窗口",
                                    fill="#cccccc",
                                    font=("Microsoft YaHei", -15))

    def _draw_round_counter(self):
        """绘制左上角的总回合数"""
        x1, y1, x2, y2 = ROUND_BOX
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#ffd700",
                                     fill="#1a1a1a", width=1)
        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                text=f"回合 {self.round}", fill="#ffd700",
                                font=("Microsoft YaHei", -15, "bold"))

    def _draw_hand(self, hand_list, y, dim, rect_store, face_down, side):
        """绘制一组手牌（重叠排列；悬停的卡牌上移并绘制在最上层）"""
        if not hand_list:
            return
        xs = card_positions(len(hand_list), *HAND_AREA)
        hover_pos = None
        if (self.hand_hover is not None and self.hand_hover[0] == side
                and not dim and self.discard is None and self.anim is None):
            hover_pos = self.hand_hover[1]

        # 先记录矩形（索引与手牌位置一一对应）
        for i in range(len(hand_list)):
            y_draw = y - (HOVER_LIFT if i == hover_pos else 0)
            rect_store.append((xs[i], y_draw, xs[i] + CARD_W,
                               y_draw + CARD_H))
        # 绘制顺序：先画普通卡牌，最后画悬停卡牌（最上层）
        order = [i for i in range(len(hand_list)) if i != hover_pos]
        if hover_pos is not None:
            order.append(hover_pos)
        for i in order:
            x = xs[i]
            y_draw = rect_store[i][1]
            entry = hand_list[i]
            if face_down:
                self.draw_card_back(self.canvas, x, y_draw, CARD_W, CARD_H,
                                    dim=dim)
            else:
                self.draw_card(self.canvas, x, y_draw, CARD_W, CARD_H,
                               self._card_of(entry), dim=dim)

    def _draw_hand_box(self, box, title, is_active):
        """绘制手牌方框（is_active 表示当前回合方，边框高亮）"""
        x1, y1, x2, y2 = box
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#242424",
                                     outline="#ffd700" if is_active else "#555555",
                                     width=2)
        title_text = title + ("（当前回合）" if is_active else "")
        self.canvas.create_text(x1 + 12, y1 + 4, text=title_text,
                                anchor="nw",
                                fill="#ffd700" if is_active else "#888888",
                                font=("Microsoft YaHei", -13))

    def _draw_mana_box(self, x1, y1, x2, y2, current, is_active):
        """绘制手牌区左侧的能量小方框"""
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#1a1a1a",
                                     outline="#ffd700" if is_active else "#555555",
                                     width=2)
        self.canvas.create_text((x1 + x2) / 2, y1 + (y2 - y1) * 0.28,
                                text="能量", fill="#888888",
                                font=("Microsoft YaHei", -12))
        self.canvas.create_text((x1 + x2) / 2, y1 + (y2 - y1) * 0.72,
                                text=f"{current}/{MAX_MANA}",
                                fill="#4fc3f7" if is_active else "#888888",
                                font=("Arial", -17, "bold"))

    def _draw_status_bar(self, box, hero):
        """绘制手牌区下端的角色数据栏（生命/攻击/防御/格挡/状态）"""
        x1, y1, x2, y2 = box
        by = y2 - 28    # 数据栏中心线
        # 分隔线
        self.canvas.create_line(x1 + 8, y2 - 52, x2 - 8, y2 - 52,
                                fill="#444444")
        # 左侧：基础属性（攻击/防御显示"基础+装备加成"）
        txt = (f"生命 {hero['hp']}/{hero['max_hp']}   "
               f"攻击 {fmt_stat(hero['base_atk'], hero['atk'])}   "
               f"防御 {fmt_stat(hero['base_def'], hero['def'])}   "
               f"格挡 {hero['block']}")
        if hero["true_block"] > 0:
            txt += f"   真格挡 {hero['true_block']}"
        if hero["absorb"] > 0:
            txt += f"   吸收 {hero['absorb']}"
        if hero["immune"] > 0:
            txt += f"   免疫 {hero['immune']}"
        if hero["mask"] > 0:
            txt += "   掩体"
        self.canvas.create_text(x1 + 14, by, text=txt, anchor="w",
                                fill="#e0e0e0",
                                font=("Microsoft YaHei", -14, "bold"))
        # 右侧：状态栏（显示状态名 + 剩余回合数）
        sx2 = x2 - 14
        sx1 = sx2 - 320
        self.canvas.create_rectangle(sx1, by - 17, sx2, by + 17,
                                     outline="#555555", fill="#1a1a1a")
        parts = [f"{st['name']}({st['rounds']})" for st in hero["statuses"]]
        for key, label in (("chill", "寒冷"), ("bleed", "流血"),
                           ("poison", "毒"), ("charge", "电感"),
                           ("vuln", "易伤")):
            if hero[key] > 0:
                parts.append(f"{label}{hero[key]}")
        status_txt = " ".join(parts) if parts else "无"
        self.canvas.create_text((sx1 + sx2) / 2, by,
                                text=f"状态：{status_txt}",
                                fill="#4fc3f7" if hero["statuses"] else "#888888",
                                font=("Microsoft YaHei", -13))

    def _draw_status_tooltip(self):
        """鼠标悬停状态栏时绘制状态效果详情浮层"""
        if self.hover_status is None:
            return
        hero = self.hero if self.hover_status == "mine" else self.enemy_hero
        if not hero["statuses"]:
            return
        lines = [f"{st['name']}：{STATUS_EFFECTS[st['name']]['desc']}"
                 f"（剩余 {st['rounds']} 回合）"
                 for st in hero["statuses"]]
        w, lh = 400, 24
        h = lh * len(lines) + 16
        cx = CANVAS_W / 2
        if self.hover_status == "mine":
            cy = BAR_M[1] - h / 2 - 6     # 我方：浮层在装备栏上方
        else:
            cy = BAR_E[3] + h / 2 + 6     # 对方：浮层在装备栏下方
        x1, y1 = cx - w / 2, cy - h / 2
        self.canvas.create_rectangle(x1, y1, x1 + w, y1 + h,
                                     fill="#333333", outline="#777777")
        for i, line in enumerate(lines):
            self.canvas.create_text(cx, y1 + 14 + i * lh, text=line,
                                    fill="#ffcc80",
                                    font=("Microsoft YaHei", -13))

    def _draw_item_detail(self):
        """鼠标悬停装备/造物缩略块时显示整张卡牌详情"""
        if self.hover_item is None or self.board_hover is not None:
            return
        side, kind, idx = self.hover_item
        equips, crafts = self._bar_groups(side)
        group = equips if kind == "equip" else crafts
        if idx >= len(group):
            return
        card = group[idx]["card"]
        # 放大 1.5 倍的整卡详情浮层
        dw, dh = CARD_W * 1.5, CARD_H * 1.5
        cx = CANVAS_W / 2
        if side == "mine":
            cy = BAR_M[1] - dh / 2 - 6
        else:
            cy = BAR_E[3] + dh / 2 + 6
        x1, y1 = cx - dw / 2, cy - dh / 2
        # 阴影
        self.rounded_rect(self.canvas, x1 + 8, y1 + 10, x1 + dw + 8,
                          y1 + dh + 10, dh * 0.09, fill="#101010",
                          outline="")
        self.draw_card(self.canvas, x1, y1, dw, dh, card)
        # 金色外框
        self.rounded_rect(self.canvas, x1 - 4, y1 - 4, x1 + dw + 4,
                          y1 + dh + 4, dh * 0.09 + 4, fill="",
                          outline="#ffd700", width=2)

    def _draw_bars(self, bar_rect, equips, side):
        """绘制装备栏（整行显示装备，悬停缩略块显示整张卡牌详情）"""
        x1, y1, x2, y2 = bar_rect
        cy = (y1 + y2) / 2
        # 外框
        self.canvas.create_rectangle(x1, y1, x2, y2, outline="#555555")
        self.canvas.create_text(x1 + 30, cy, text="装备",
                                fill=TYPE_COLORS["equip"],
                                font=("Microsoft YaHei", -13, "bold"))
        self._draw_bar_items(x1 + 62, cy, equips, side, "equip")

    def _draw_bar_items(self, start_x, cy, items, side, kind):
        """在栏内排列绘制装备/造物缩略块（名称 + 右上角小圆：回合数或血量）"""
        x = start_x
        for i, item in enumerate(items):
            card = item["card"]
            color = CATEGORY_COLORS.get(card.get("category"), "#9d9d9d")
            w, h = 68, 24
            self.canvas.create_rectangle(x, cy - h / 2, x + w, cy + h / 2,
                                         outline=color, fill="#1a1a1a")
            # 名称（左对齐，最多 4 字）
            self.canvas.create_text(x + 4, cy, text=card["name"][:4],
                                    anchor="w", fill="#cccccc",
                                    font=("Microsoft YaHei", -11))
            # 右上角：剩余回合数小圆（装备/造物均有回合制）
            rcx = x + w - 12
            self.canvas.create_oval(rcx - 8, cy - 8, rcx + 8, cy + 8,
                                    fill="#1e1e1e", outline=color, width=1)
            self.canvas.create_text(rcx, cy, text=str(item["rounds"]),
                                    fill="#ffffff",
                                    font=("Arial", -11, "bold"))
            # 记录缩略块矩形，供悬停检测使用
            self.bar_item_rects.append(
                (side, kind, i, (x, cy - h / 2, x + w, cy + h / 2)))
            x += w + 8

    def _draw_log(self):
        """在战斗记录框内显示双方出牌与效果记录（最新条目显示在最下方）"""
        x1, y1, x2, y2 = LOG_BOX
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#141414",
                                     outline="#555555", width=1)
        self.canvas.create_text((x1 + x2) / 2, y1 + 14, text="战斗记录",
                                fill="#8ab0dc",
                                font=("Microsoft YaHei", -13, "bold"))
        self.canvas.create_line(x1 + 6, y1 + 28, x2 - 6, y1 + 28,
                                fill="#444444")
        # 底部显示最近若干条（按行折行，超出部分裁掉）
        all_lines = []
        for msg in self.log:
            all_lines.extend(wrap_text(msg))
        max_lines = max(1, (y2 - y1 - 40) // 16)
        visible = all_lines[-max_lines:] if all_lines else []
        ty = y1 + 42
        if not visible:
            self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                                    text="（暂无记录）", fill="#666666",
                                    font=("Microsoft YaHei", -11))
            return
        for line in visible:
            self.canvas.create_text(x1 + 8, ty, text=line, anchor="w",
                                    fill="#cccccc",
                                    font=("Microsoft YaHei", -10))
            ty += 16

    # ---------- 战场单位 ----------
    def _draw_board_units(self):
        """绘制战场单位：双方主角色框 + 围绕主角框排列的站场造物实体"""
        self._draw_hero_box(ENEMY_HERO_BOX, "enemy")
        self._draw_hero_box(MINE_HERO_BOX, "mine")
        self._draw_board_row(self.board_enemy, "enemy")
        self._draw_board_row(self.board_mine, "mine")
        # 施法目标选择中：已分配攻击段的目标金色常驻框，悬停目标亮黄高亮
        if self.targeting is not None:
            for target in self.targeting.get("targets", []):
                x1, y1, x2, y2 = self._target_rect(target)
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             outline="#ffd700", width=3)
            target = self.targeting.get("hover_target")
            if target is not None:
                x1, y1, x2, y2 = self._target_rect(target)
                self.canvas.create_rectangle(x1, y1, x2, y2,
                                             outline="#fff176", width=4)

    def _target_rect(self, target):
        """返回目标单位的矩形区域（用于高亮与点击检测）"""
        if target[0] == "hero":
            return ENEMY_HERO_BOX if target[1] == "enemy" else MINE_HERO_BOX
        side, idx = target[1], target[2]
        unit = (self.board_enemy if side == "enemy" else self.board_mine)[idx]
        return (unit["x"], unit["y"], unit["x"] + BOARD_W, unit["y"] + BOARD_H)

    def _target_center(self, target):
        """返回目标单位矩形中心坐标；无法定位返回 None"""
        if target is None:
            return None
        try:
            x1, y1, x2, y2 = self._target_rect(target)
        except Exception:
            return None
        return ((x1 + x2) / 2, (y1 + y2) / 2)

    def _draw_hero_box(self, box, side):
        """绘制主角色框（可被选中的单位）：名字/生命/攻击/防御/格挡"""
        hero = self.hero if side == "mine" else self.enemy_hero
        x1, y1, x2, y2 = box
        dx, _ = self._shake_offset(("hero", side))
        x1 += dx
        x2 += dx
        active = self.turn == side
        self.canvas.create_rectangle(x1, y1, x2, y2, fill="#1a1a1a",
                                     outline="#ffd700" if active else "#555555",
                                     width=2)
        name = "我方主角" if side == "mine" else "敌方主角"
        self.canvas.create_text((x1 + x2) / 2, y1 + 20, text=name,
                                fill="#ffd700" if active else "#888888",
                                font=("Microsoft YaHei", -15, "bold"))
        self.canvas.create_text((x1 + x2) / 2, y1 + 58,
                                text=f"生命 {hero['hp']}/{hero['max_hp']}",
                                fill="#f4a6a6",
                                font=("Microsoft YaHei", -14, "bold"))
        self.canvas.create_text((x1 + x2) / 2, y1 + 86,
                                text=(f"攻击 {fmt_stat(hero['base_atk'], hero['atk'])}"
                                      f"  防御 {fmt_stat(hero['base_def'], hero['def'])}"),
                                fill="#e0e0e0",
                                font=("Microsoft YaHei", -12))
        self.canvas.create_text((x1 + x2) / 2, y1 + 112,
                                text=f"格挡 {hero['block']}",
                                fill="#4fc3f7" if hero["block"] > 0 else "#888888",
                                font=("Microsoft YaHei", -12))

    def _craft_slots(self, side):
        """返回该方造物的排列行：(起始 x, y, 方向, 边界)。方向 1 向右 / -1 向左"""
        if side == "mine":
            # 围绕我方主角框：右侧行（向右）→ 上方行（避开中央纪念堆）
            return [(MINE_HERO_BOX[2] + 10, MINE_HERO_BOX[1] + 8, 1, 840),
                    (MINE_HERO_BOX[2] + 10,
                     MINE_HERO_BOX[1] - BOARD_H - 10, 1, 585)]
        # 围绕敌方主角框：左侧行（向左）→ 下方行
        x0 = ENEMY_HERO_BOX[0] - BOARD_W - 10
        return [(x0, ENEMY_HERO_BOX[1] + 8, -1, 740),
                (x0, ENEMY_HERO_BOX[3] + 10, -1, 740)]

    def _craft_positions(self, side, count):
        """计算该方造物位置列表：围绕主角框按行排列，行满换下一行"""
        pos = []
        for sx, sy, d, lim in self._craft_slots(side):
            x = sx
            while (d == 1 and x <= lim) or (d == -1 and x >= lim):
                pos.append((x, sy))
                if len(pos) >= count:
                    return pos
                x += d * (BOARD_W + BOARD_GAP)
        # 兜底：行容量用尽仍有剩余造物，叠放在最后一个位置
        if pos:
            last = pos[-1]
            while len(pos) < count:
                pos.append(last)
        return pos

    def _draw_board_row(self, board, side):
        """绘制一方站场造物实体（围绕主角框排列；缩小卡牌 + 剩余回合 + 底部血条；
        已攻击过变暗）"""
        pos = self._craft_positions(side, len(board))
        for i, unit in enumerate(board):
            x, y = pos[i]
            dx, _ = self._shake_offset(("board", side, i))
            unit["x"] = x + dx
            unit["y"] = y
            card = unit["card"]
            # 己方回合中已攻击过的造物变暗显示
            dim = self.turn == side and not unit["can_attack"]
            self.draw_card(self.canvas, x, y, BOARD_W, BOARD_H, card,
                           dim=dim, atk_info=False, board=True)
            # 剩余回合（无限回合显示 ∞）
            rounds_txt = ("∞" if unit["rounds"] in (None, -1)
                          else f"剩 {unit['rounds']} 回合")
            self.canvas.create_text(x + BOARD_W / 2, y + BOARD_H * 0.79,
                                    text=rounds_txt, fill="#26c6da",
                                    font=("Microsoft YaHei", -9, "bold"))
            # 血条（卡牌底部）：按当前血量比例填充，不遮挡文字描述
            bx1, by1 = x + BOARD_W * 0.12, y + BOARD_H * 0.88
            bx2, by2 = x + BOARD_W * 0.88, y + BOARD_H * 0.96
            self._draw_hp_bar(self.canvas, bx1, by1, bx2, by2,
                              unit["hp"], card["health"])

    def _draw_hp_bar(self, canvas, x1, y1, x2, y2, hp, max_hp):
        """绘制血量条：深色外框 + 按比例填充（绿→黄→红）+ 血量数字"""
        canvas.create_rectangle(x1, y1, x2, y2, outline="#888888",
                                fill="#1a1a1a", width=1)
        # 血量数字（如 4/8）
        canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2,
                           text=f"{hp}/{max_hp}",
                           fill="#ffffff",
                           font=("Arial", -max(8, int((y2 - y1) * 0.7)),
                                 "bold"))
        if max_hp <= 0:
            return
        ratio = max(0.0, min(1.0, hp / max_hp))
        if ratio <= 0:
            return
        if ratio > 0.5:
            color = "#4caf50"
        elif ratio > 0.25:
            color = "#ffc107"
        else:
            color = "#f44336"
        fx2 = x1 + (x2 - x1) * ratio
        canvas.create_rectangle(x1 + 2, y1 + 2, fx2 - 2, y2 - 2,
                                fill=color, outline="")

    def _draw_target_arrow(self):
        """施法目标选择中：从攻击来源到光标的指向箭头"""
        if self.targeting is None:
            return
        src = self.targeting["src"]
        if src[0] == "hand":
            pos = src[1]
            hand = self.hand if self.turn == "mine" else self.enemy_hand
            xs = card_positions(len(hand), *HAND_AREA)
            y = HAND_Y if self.turn == "mine" else ENEMY_Y
            x1 = xs[pos] + CARD_W / 2
            y1 = y - HOVER_LIFT + CARD_H / 2
        else:
            side, idx = src[1], src[2]
            unit = (self.board_mine if side == "mine"
                    else self.board_enemy)[idx]
            x1 = unit["x"] + BOARD_W / 2
            y1 = unit["y"] + BOARD_H / 2
        mx, my = self.targeting["mouse"]
        self.canvas.create_line(x1, y1, mx, my, fill="#ffd700", width=2,
                                arrow=tk.LAST, dash=(6, 4))

    def _draw_board_detail(self):
        """鼠标悬停战场造物时显示放大卡详情浮层（含当前攻/血）"""
        if self.board_hover is None or self.targeting is not None:
            return
        side, idx = self.board_hover
        board = self.board_mine if side == "mine" else self.board_enemy
        if idx >= len(board):
            return
        unit = board[idx]
        dw, dh = CARD_W * 1.5, CARD_H * 1.5
        cx = CANVAS_W / 2
        if side == "mine":
            cy = BAR_M[1] - dh / 2 - 6
        else:
            cy = BAR_E[3] + dh / 2 + 6
        x1, y1 = cx - dw / 2, cy - dh / 2
        # 阴影
        self.rounded_rect(self.canvas, x1 + 8, y1 + 10, x1 + dw + 8,
                          y1 + dh + 10, dh * 0.09, fill="#101010",
                          outline="")
        self.draw_card(self.canvas, x1, y1, dw, dh, unit["card"],
                       clip_desc=False)
        # 血条（中偏下）与攻击值（血条左上方）
        self._draw_hp_bar(self.canvas, x1 + dw * 0.12, y1 + dh * 0.72,
                          x1 + dw * 0.88, y1 + dh * 0.80,
                          unit["hp"], unit["card"]["health"])
        self.canvas.create_text(x1 + dw * 0.13, y1 + dh * 0.69,
                                text=f"攻击值 {unit['atk']}", anchor="w",
                                fill="#ffd966",
                                font=("Arial", -int(dw * 0.10), "bold"))
        # 金色外框
        self.rounded_rect(self.canvas, x1 - 4, y1 - 4, x1 + dw + 4,
                          y1 + dh + 4, dh * 0.09 + 4, fill="",
                          outline="#ffd700", width=2)

    # ---------- 按钮 ----------
    def _draw_all_buttons(self):
        """绘制所有按钮：施法中仅显示取消，结束回合全局常驻，打出/取消选中时显示"""
        # 弃牌模式或动画中不显示任何按钮
        if self.discard is not None or self.anim is not None:
            return
        if self.targeting is not None:
            # 施法目标选择中：多目标卡显示施法按钮，取消按钮常驻
            if self._max_targets() > 1:
                self._draw_button(*PLAY_BTN, "施 法", "#4caf50", "cast")
            self._draw_button(*CANCEL_BTN, "取 消", "#666666", "cancel_target")
            return
        # 结束回合按钮（始终显示）
        self._draw_button(*END_TURN_BTN, "结束回合", "#3f6fbf", "end_turn")
        # 打出 / 取消：仅当选中了当前回合方的手牌时显示
        if self.selected is not None and self.selected[0] == self.turn:
            self._draw_button(*PLAY_BTN, "打 出", "#4caf50", "play")
            self._draw_button(*CANCEL_BTN, "取 消", "#666666", "cancel")

    def _draw_button(self, x1, y1, x2, y2, text, color, action):
        """绘制单个按钮并记录其区域"""
        self.rounded_rect(self.canvas, x1, y1, x2, y2, 10, fill=color,
                          outline="")
        self.canvas.create_text((x1 + x2) / 2, (y1 + y2) / 2, text=text,
                                fill="#ffffff",
                                font=("Microsoft YaHei", -17, "bold"))
        self.buttons.append((x1, y1, x2, y2, action))

    # ---------- 放大卡牌 ----------
    def _draw_zoomed_card(self, card, back=False):
        """在战场中央绘制放大版卡牌（带阴影与金色外框）"""
        zw, zh = CARD_W * ZOOM_SCALE, CARD_H * ZOOM_SCALE
        cx = (PLAY_AREA[0] + PLAY_AREA[2]) / 2
        cy = (PLAY_AREA[1] + PLAY_AREA[3]) / 2
        zx, zy = cx - zw / 2, cy - zh / 2

        # 阴影
        self.rounded_rect(self.canvas, zx + 9, zy + 11, zx + zw + 9,
                          zy + zh + 11, zh * 0.09, fill="#101010", outline="")
        # 卡牌本体（背面或正面；放大显示完整描述）
        if back:
            self.draw_card_back(self.canvas, zx, zy, zw, zh)
        else:
            self.draw_card(self.canvas, zx, zy, zw, zh, card,
                           clip_desc=False)
        # 金色高亮外框
        self.rounded_rect(self.canvas, zx - 5, zy - 5, zx + zw + 5,
                          zy + zh + 5, zh * 0.09 + 5, fill="",
                          outline="#ffd700", width=3)

        self.zoom_rect = (zx, zy, zx + zw, zy + zh)

    # ---------- 战斗特效（按真实时间驱动，到期必然消失） ----------
    def _spawn_dmg_fx(self, text, target=None):
        """生成红色扣血数字特效（默认战场中央，传 target 则显示在对应单位身上）"""
        cx, cy = self._fx_anchor(target)
        self.fx.append({"type": "dmg", "text": text, "x": cx, "y": cy,
                        "t0": time.time(), "dur": 1.1})
        # 兜底：到期后自动清理重绘，保证特效必然消失
        self.root.after(1150, self._fx_cleanup)

    def _spawn_heal_fx(self, text, target=None):
        """生成绿色回血数字特效 + 周围绿色加号粒子（默认中央，可定位到单位）"""
        cx, cy = self._fx_anchor(target)
        self.fx.append({"type": "heal", "text": text, "x": cx, "y": cy,
                        "t0": time.time(), "dur": 1.1})
        for _ in range(6):
            ang = random.uniform(0, 2 * math.pi)
            self.fx.append({"type": "plus", "x": cx, "y": cy,
                            "vx": math.cos(ang) * 55,
                            "vy": math.sin(ang) * 40 - 35,
                            "t0": time.time(), "dur": 0.9})
        self.root.after(1150, self._fx_cleanup)

    def _fx_anchor(self, target):
        """返回特效锚点坐标：有目标则定位到该单位中心，否则在战场中央"""
        if target is not None:
            c = self._target_center(target)
            if c is not None:
                return (c[0] + random.randint(-16, 16),
                        c[1] + random.randint(-16, 16))
        return ((PLAY_AREA[0] + PLAY_AREA[2]) / 2 + random.randint(-40, 40),
                (PLAY_AREA[1] + PLAY_AREA[3]) / 2 - 60)

    def _spawn_unit_shake(self, target):
        """生成单位受击震动特效（target 为 ("hero", side) 或 ("board", side, idx)）"""
        self.fx.append({"type": "unit_shake", "target": target,
                        "t0": time.time(), "dur": 0.4})
        self.root.after(450, self._fx_cleanup)

    def _shake_offset(self, target):
        """返回目标当前受击震动偏移，无震动为 (0, 0)"""
        now = time.time()
        for f in self.fx:
            if f["type"] == "unit_shake" and f["target"] == target:
                t = (now - f["t0"]) / f["dur"]
                if t < 1:
                    return (math.sin((now - f["t0"]) * 60) * 6 * (1 - t), 0)
        return (0, 0)

    def _spawn_block_fx(self, mode, target):
        """生成格挡特效：shield 震动（剩余格挡）/ 碎裂（仍有扣血），
        显示在被格挡单位身上（target 为目标元组，无法定位时回退战场中央）"""
        c = self._target_center(target) if target is not None else None
        if c is None:
            c = self._fx_anchor(None)
        x, y = c
        dur = 0.7 if mode == "shake" else 0.45
        self.fx.append({"type": "shield", "mode": mode, "x": x, "y": y,
                        "t0": time.time(), "dur": dur})
        if mode == "break":
            # 盾牌碎裂：碎片向四周飞散
            for ang in (-150, -90, -30, 30, 90, 150):
                rad = math.radians(ang)
                self.fx.append({"type": "shard", "x": x, "y": y,
                                "vx": math.cos(rad) * 110,
                                "vy": math.sin(rad) * 80 - 50,
                                "t0": time.time(), "dur": 0.9})
        self.root.after(950, self._fx_cleanup)

    def _fx_cleanup(self):
        """清理已到期的特效（按真实时间判定，保证特效必然消失）"""
        now = time.time()
        before = len(self.fx)
        self.fx = [f for f in self.fx if now - f["t0"] < f["dur"]]
        if len(self.fx) != before:
            self.draw()

    def _draw_fx(self):
        """绘制战斗特效（按真实时间推进）"""
        now = time.time()
        for f in self.fx:
            t = min(1.0, (now - f["t0"]) / f["dur"])
            if f["type"] in ("dmg", "heal"):
                # 扣血红色/回血绿色数字：从中间弹出，自由落体渐隐
                y = f["y"] + 130 * t * t
                base = "#4caf50" if f["type"] == "heal" else "#ff3333"
                col = darken(base, 1 - 0.78 * t)
                self.canvas.create_text(f["x"], y, text=f["text"],
                                        fill=col,
                                        font=("Arial", -30, "bold"))
            elif f["type"] == "shield":
                # 盾牌：震动（左右抖动）或碎裂（变暗）
                x = f["x"] + math.sin((now - f["t0"]) * 40) * 6
                col = ("#ffd700" if f["mode"] == "shake"
                       else darken("#ffd700", 0.55))
                self.canvas.create_oval(x - 18, f["y"] - 18, x + 18,
                                        f["y"] + 18, outline=col, width=3,
                                        fill="#1e1e1e")
                self.canvas.create_text(x, f["y"], text="盾", fill=col,
                                        font=("Microsoft YaHei", -18,
                                              "bold"))
            elif f["type"] == "shard":
                # 碎片：抛物线飞散并渐隐
                sec = now - f["t0"]
                x = f["x"] + f["vx"] * sec
                y = f["y"] + f["vy"] * sec + 350 * sec * sec
                col = darken("#8a9bb8", 1 - 0.65 * t)
                self.canvas.create_rectangle(x - 4, y - 4, x + 4, y + 4,
                                             fill=col, outline="")
            elif f["type"] == "plus":
                # 绿色加号粒子：飘散渐隐
                sec = now - f["t0"]
                x = f["x"] + f["vx"] * sec
                y = f["y"] + f["vy"] * sec + 120 * sec * sec
                col = darken("#66bb6a", 1 - 0.7 * t)
                self.canvas.create_text(x, y, text="+", fill=col,
                                        font=("Arial", -16, "bold"))

    # ---------- 抽牌动画 ----------
    def _start_draw_animation(self, side):
        """从共用抽牌堆抽牌并启动飞行动画：卡牌从战场中心飞入对应手牌区"""
        hand = self.hand if side == "mine" else self.enemy_hand
        y_target = HAND_Y if side == "mine" else ENEMY_Y

        if not self.deck:
            self.flash_msg = "牌库已空，无法继续抽牌"
            self.root.after(1200, self._clear_notice)
            self.draw()
            return

        # 抽牌（从共用抽牌堆顶部抽取）
        entries = []
        while len(entries) < DRAW_PER_TURN and self.deck:
            entries.append(self.deck.pop())

        # 计算动画起止位置：起点在战场中心并排，终点为新牌在手牌区的位置
        n = len(hand)
        xs = card_positions(n + len(entries), *HAND_AREA)
        cx = (PLAY_AREA[0] + PLAY_AREA[2]) / 2
        cy = (PLAY_AREA[1] + PLAY_AREA[3]) / 2 - CARD_H / 2
        starts = [(cx - CARD_W - 10, cy), (cx + 10, cy)]
        ends = [(xs[n + i], y_target) for i in range(len(entries))]
        # 对方抽牌时飞行过程显示背面，落位后按显示规则渲染
        backs = [side == "enemy"] * len(entries)

        self.anim = {"entries": entries, "backs": backs,
                     "starts": starts, "ends": ends,
                     "frame": 0, "total": ANIM_FRAMES, "side": side}
        self._tick_animation()

    def _tick_animation(self):
        """动画帧推进：每帧重绘，到达最后一帧时把卡牌加入手牌"""
        if self.anim is None:
            return
        self.anim["frame"] += 1
        self.draw()
        if self.anim["frame"] >= self.anim["total"]:
            side = self.anim["side"]
            entries = self.anim["entries"]
            hand = self.hand if side == "mine" else self.enemy_hand
            hand.extend(entries)
            self.anim = None
            self.draw()
        else:
            self.root.after(ANIM_INTERVAL, self._tick_animation)

    def _draw_animation(self):
        """绘制动画中正在飞行的卡牌"""
        if self.anim is None:
            return
        t = self.anim["frame"] / self.anim["total"]
        for i, entry in enumerate(self.anim["entries"]):
            sx, sy = self.anim["starts"][i]
            ex, ey = self.anim["ends"][i]
            x = sx + (ex - sx) * t
            y = sy + (ey - sy) * t
            if self.anim["backs"][i]:
                self.draw_card_back(self.canvas, x, y, CARD_W, CARD_H)
            else:
                self.draw_card(self.canvas, x, y, CARD_W, CARD_H,
                               self._card_of(entry))

    # ---------- 单张卡牌绘制（按宽高比例缩放） ----------
    def rounded_rect(self, canvas, x1, y1, x2, y2, r, **kwargs):
        """在指定画布上绘制圆角矩形，返回图形 id"""
        points = [x1 + r, y1, x2 - r, y1, x2, y1, x2, y1 + r,
                  x2, y2 - r, x2, y2, x2 - r, y2, x1 + r, y2,
                  x1, y2, x1, y2 - r, x1, y1 + r, x1, y1]
        return canvas.create_polygon(points, smooth=True, **kwargs)

    def draw_card(self, canvas, x1, y1, w, h, card, dim=False, atk_info=True,
                  clip_desc=True, board=False):
        """在指定画布矩形内绘制卡牌正面，内部元素按宽高比例缩放
        clip_desc=True 时过长描述截断（放大查看时传 False 显示全文）
        board=True 时为棋盘缩小造物卡：不绘制底部文字（由血条替代）"""
        color = CATEGORY_COLORS.get(card.get("category"), "#9d9d9d")
        if dim:
            color = darken(color)

        r = max(8, w * 0.09)    # 圆角半径
        # 卡牌底色与边框
        self.rounded_rect(canvas, x1, y1, x1 + w, y1 + h, r,
                          fill="#2f2f2f" if dim else "#3a3a3a",
                          outline=color, width=max(2, int(w * 0.015)))
        # 顶部稀有度色带
        band_h = h * 0.13
        self.rounded_rect(canvas, x1 + 2, y1 + 2, x1 + w - 2, y1 + band_h,
                          r - 2, fill=color, outline="")
        # 费用徽章（色带中央偏左，圆形）
        d = w * 0.16
        cx, cy = x1 + d * 0.8, y1 + band_h / 2
        canvas.create_oval(cx - d / 2, cy - d / 2, cx + d / 2, cy + d / 2,
                           fill="#1e1e1e", outline="")
        canvas.create_text(cx, cy, text=str(card["cost"]),
                           fill="#ffffff",
                           font=("Arial", -int(w * 0.085), "bold"))

        ctype = card.get("type", "normal")
        if ctype == "normal":
            self._draw_normal_card(canvas, x1, y1, w, h, card, color, dim,
                                   clip_desc)
        else:
            self._draw_typed_card(canvas, x1, y1, w, h, card, color, dim,
                                  ctype, atk_info, clip_desc, board)

    def _draw_normal_card(self, canvas, x1, y1, w, h, card, color, dim,
                          clip_desc=True):
        """绘制随从卡的内容（名称/职业/描述/攻击段数/生命/效果/稀有度）"""
        # 卡牌名称
        canvas.create_text(x1 + w / 2, y1 + h * 0.30, text=card["name"],
                           fill="#ffffff" if not dim else darken("#ffffff", 0.5),
                           font=("Microsoft YaHei", -int(w * 0.088), "bold"))
        # 职业（新卡池显示分类）
        canvas.create_text(x1 + w / 2, y1 + h * 0.40,
                           text=card.get("category", ""),
                           fill="#bbbbbb" if not dim else darken("#bbbbbb", 0.5),
                           font=("Microsoft YaHei", -int(w * 0.062)))
        # 描述与攻击信息（合并显示，自动换行，不超出卡牌；desc 可含 \n 多行）
        hits = card.get("hits", 1)
        mt = card.get("max_targets", 1)
        atk = card.get("attack")
        if atk is not None:
            if mt > 1:
                atk_info = (f"攻击 {hits} 段 · 至多 {mt} 个目标"
                            f"\n每段造成 {atk} 点伤害")
            elif hits > 1:
                atk_info = f"攻击 {hits} 段 · 每段 {atk} 点伤害"
            else:
                atk_info = f"造成 {atk} 点伤害"
            text = card["desc"] + "\n" + atk_info
        else:
            text = card["desc"]
        # 描述过长时截断，防止超出卡牌（放大查看时显示全文）
        if clip_desc and len(text) > 56:
            text = text[:56] + "…"
        canvas.create_text(x1 + w / 2, y1 + h * 0.48,
                           text=text, anchor="n",
                           fill="#cccccc" if not dim else darken("#cccccc", 0.5),
                           font=("Microsoft YaHei", -int(w * 0.05)),
                           width=w * 0.84, justify="center")
        # 效果文字（战吼状态 / 获得格挡）
        eff_lines = []
        st = card.get("status_on_play")
        if st:
            eff_lines.append(f"战吼：敌方{st['name']} {st['rounds']}回合")
        if card.get("gain_block", 0) > 0:
            eff_lines.append(f"战吼：获得 {card['gain_block']} 格挡")
        for i, line in enumerate(eff_lines):
            canvas.create_text(x1 + w / 2, y1 + h * (0.75 + i * 0.065),
                               text=line,
                               fill="#4fc3f7" if not dim else darken("#4fc3f7"),
                               font=("Microsoft YaHei", -int(w * 0.055)))
        # 稀有度文字（新卡池显示分类，底部）
        canvas.create_text(x1 + w / 2, y1 + h * 0.96,
                           text=card.get("category", ""), fill=color,
                           font=("Microsoft YaHei", -int(w * 0.06), "bold"))

    def _draw_typed_card(self, canvas, x1, y1, w, h, card, color, dim,
                         ctype, atk_info=True, clip_desc=True, board=False):
        """绘制装备/造物卡的内容（类型区分在右上角小方块；装备显示时限与加成）
        board=True 时为棋盘缩小造物卡：不绘制底部文字，由血条替代"""
        icon_color = TYPE_COLORS[ctype]
        type_name = TYPE_NAMES[ctype]
        if dim:
            icon_color = darken(icon_color)

        d = w * 0.16
        band_h = h * 0.13
        cy = y1 + band_h / 2
        # 右上角：类型小方块（区分装备/造物）+ 持续回合数小圆
        # （board=True 的缩小造物不画小圆，剩余回合由 _draw_board_row 绘制）
        tx = x1 + w - d * 0.55              # 回合数小圆中心（最右端）
        if ctype in ("equip", "craft") and not board:
            canvas.create_oval(tx - d * 0.4, cy - d * 0.4, tx + d * 0.4,
                               cy + d * 0.4, fill="#1e1e1e",
                               outline=icon_color, width=2)
            canvas.create_text(tx, cy,
                               text="∞" if card["duration"] in (None, -1)
                               else str(card["duration"]),
                               fill="#ffffff",
                               font=("Arial", -int(d * 0.48), "bold"))
        bx1 = tx - d * 1.15                 # 类型小方块（回合数左侧）
        self.rounded_rect(canvas, bx1, cy - d * 0.34, bx1 + d * 0.72,
                          cy + d * 0.34, 4, fill=icon_color, outline="")
        canvas.create_text(bx1 + d * 0.36, cy,
                           text=type_name[0], fill="#1e1e1e",
                           font=("Microsoft YaHei", -int(d * 0.44), "bold"))
        # 名称
        canvas.create_text(x1 + w / 2, y1 + h * 0.28, text=card["name"],
                           fill="#ffffff" if not dim else darken("#ffffff", 0.5),
                           font=("Microsoft YaHei", -int(w * 0.088), "bold"))
        if ctype == "craft":
            # 描述（自动换行；放大查看时显示全文）
            text = card["desc"]
            if clip_desc and len(text) > 56:
                text = text[:56] + "…"
            canvas.create_text(x1 + w / 2, y1 + h * 0.44, text=text,
                               anchor="n",
                               fill="#cccccc" if not dim else darken("#cccccc", 0.5),
                               font=("Microsoft YaHei", -int(w * 0.055)),
                               width=w * 0.84, justify="center")
        else:
            # 描述
            canvas.create_text(x1 + w / 2, y1 + h * 0.46, text=card["desc"],
                           fill="#cccccc" if not dim else darken("#cccccc", 0.5),
                           font=("Microsoft YaHei", -int(w * 0.058)),
                           width=w * 0.82, justify="center")
        if ctype == "equip":
            # 属性加成文字（有加成时显示）
            bonus_lines = []
            if card.get("atk_bonus", 0) > 0:
                bonus_lines.append(f"攻击 +{card['atk_bonus']}")
            if card.get("def_bonus", 0) > 0:
                bonus_lines.append(f"防御 +{card['def_bonus']}")
            for i, line in enumerate(bonus_lines):
                canvas.create_text(x1 + w / 2, y1 + h * (0.74 + i * 0.075),
                                   text=line, fill="#a5d6a7",
                                   font=("Microsoft YaHei", -int(w * 0.058),
                                         "bold"))
        if board:
            return
        # 底部：装备显示持续回合数，造物显示生命值（无限回合显示 ∞）
        dur_txt = ("∞" if card["duration"] in (None, -1)
                   else card["duration"])
        if ctype == "equip":
            bottom = f"{type_name} · 持续 {dur_txt} 回合"
        elif card["health"] is not None:
            bottom = f"{type_name} · 生命 {card['health']}"
        else:
            bottom = type_name
        canvas.create_text(x1 + w / 2, y1 + h * 0.97,
                           text=bottom,
                           fill=icon_color,
                           font=("Microsoft YaHei", -int(w * 0.065), "bold"))

    def draw_card_back(self, canvas, x1, y1, w, h, dim=False):
        """在指定画布矩形内绘制卡牌背面（深蓝底 + 菱形花纹 + 问号）"""
        r = max(8, w * 0.09)
        fill = darken("#1e2a44", 0.7) if dim else "#1e2a44"
        outline = darken("#3a5a8a") if dim else "#3a5a8a"
        pattern = darken("#2c4266") if dim else "#2c4266"
        border = darken("#5a82b8") if dim else "#5a82b8"

        # 卡牌底色与边框
        self.rounded_rect(canvas, x1, y1, x1 + w, y1 + h, r,
                          fill=fill, outline=outline,
                          width=max(2, int(w * 0.015)))
        # 内边框
        self.rounded_rect(canvas, x1 + w * 0.10, y1 + h * 0.10,
                          x1 + w * 0.90, y1 + h * 0.90, r * 0.6, fill="",
                          outline=border, width=1)
        # 中央菱形花纹
        cx, cy = x1 + w / 2, y1 + h / 2
        s = min(w, h) * 0.28
        canvas.create_polygon(cx, cy - s, cx + s, cy,
                              cx, cy + s, cx - s, cy,
                              fill=pattern, outline=border, width=2)
        # 菱形中央问号
        canvas.create_text(cx, cy, text="?", fill="#8ab0dc",
                           font=("Arial", -int(w * 0.20), "bold"))

    # ---------- 游戏逻辑 ----------
    def _in_rect(self, x, y, rect):
        """判断坐标是否在矩形内"""
        x1, y1, x2, y2 = rect
        return x1 <= x <= x2 and y1 <= y <= y2

    def _random_played_pos(self):
        """生成已出卡牌纪念堆的随机错位坐标（战场中央偏上，避开造物行）"""
        cx = PLAYED_ANCHOR[0] - CARD_W / 2
        cy = PLAYED_ANCHOR[1] - CARD_H / 2
        return cx + random.randint(-70, 70), cy + random.randint(-40, 40)

    def _show_notice(self, text):
        """显示短暂提示，约 1.5 秒后自动消失"""
        self.flash_msg = text
        self.draw()
        self.root.after(1500, self._clear_notice)

    def _clear_notice(self):
        """清除短暂提示"""
        if self.flash_msg is not None:
            self.flash_msg = None
            self.draw()

    # ---------- 目标解析 / 延迟效果 ----------
    def _target_obj(self, target):
        """根据目标元组返回实际角色/造物字典：("hero", side) 或 ("board", side, idx)"""
        if target[0] == "hero":
            return self.hero if target[1] == "mine" else self.enemy_hero
        board = self.board_mine if target[1] == "mine" else self.board_enemy
        idx = target[2]
        if 0 <= idx < len(board):
            return board[idx]
        return None

    def _unit_target(self, obj):
        """根据单位对象（主角色/造物）反推其 target 元组，无法识别返回 None"""
        if obj is self.hero:
            return ("hero", "mine")
        if obj is self.enemy_hero:
            return ("hero", "enemy")
        for i, u in enumerate(self.board_mine):
            if u is obj:
                return ("board", "mine", i)
        for i, u in enumerate(self.board_enemy):
            if u is obj:
                return ("board", "enemy", i)
        return None

    def _side_label(self, obj):
        """返回单位所属方文字（我方/敌方），中立或无法识别返回空字符串"""
        t = self._unit_target(obj)
        if t is None:
            return ""
        return "我方" if t[1] == "mine" else "敌方"

    def _target_label(self, target):
        """返回目标单位的文字描述，如「敌方主角」「我方造物」"""
        if target[0] == "hero":
            return "我方主角" if target[1] == "mine" else "敌方主角"
        return "我方造物" if target[1] == "mine" else "敌方造物"

    def _log(self, msg):
        """追加一条战斗记录，最多保留 LOG_MAX 条"""
        self.log.append(msg)
        if len(self.log) > LOG_MAX:
            self.log = self.log[-LOG_MAX:]

    def _add_card_to_hand(self, side, card):
        """将卡牌加入指定方手牌"""
        hand = self.hand if side == "mine" else self.enemy_hand
        try:
            idx = CARDS.index(card)
        except ValueError:
            idx = random.randrange(len(CARDS))
        hand.append((side, idx))

    def _add_pending(self, turns, fn, tag=None, side=None):
        """登记延迟效果：turns 次回合切换后触发；side 用于按方过滤（如蓄力打断）"""
        self.pending.append({"turns": turns, "fn": fn, "tag": tag,
                             "side": side})

    def _interrupt_charge(self, side):
        """打断蓄力：取消指定方蓄力卡对应的延迟效果"""
        hero = self.hero if side == "mine" else self.enemy_hero
        hero["charging"] = False
        before = len(self.pending)
        self.pending = [p for p in self.pending
                        if not (p.get("tag") == "charge"
                                and p.get("side") == side)]
        if len(self.pending) != before:
            self._show_notice("蓄力被打断！")

    def _process_pending(self):
        """回合切换时结算延迟效果（turns 递减，归零触发）"""
        if not self.pending:
            return
        keep = []
        for p in self.pending:
            p["turns"] -= 1
            if p["turns"] <= 0:
                try:
                    p["fn"]()
                except Exception:
                    pass
            else:
                keep.append(p)
        self.pending = keep

    # ---------- 装备辅助 ----------
    def _equips_of(self, hero):
        """返回角色装备栏；中立来源（炙阳/雪崩等无主伤害）无装备"""
        if hero is self.hero:
            return self.hero_equips
        if hero is self.enemy_hero:
            return self.enemy_equips
        return []

    def _has_equip(self, hero, name):
        return any(e["card"]["name"] == name for e in self._equips_of(hero))

    def _board_of_side(self, side):
        return self.board_mine if side == "mine" else self.board_enemy

    # ---------- 伤害结算 ----------
    def _deal_target(self, attacker_hero, target, amount, true=False,
                     ignore_def=False, ignore_block=False, lifesteal=False,
                     force=False):
        """统一伤害结算入口。返回实际造成的伤害值（扣除格挡/吸收后）。

        flags：
          true          真实攻击（不受普通格挡影响，仍受真实格挡影响）
          ignore_def    无视防御力
          ignore_block  无视格挡（含真实格挡）
          lifesteal     生命吸取（不受攻击/防御影响，按实际伤害回血）
          force         无视效果（强制伤害，等同斩杀，仍受死舞约束）
        """
        defender = self._target_obj(target)
        if defender is None:
            return 0
        if amount <= 0 and not force:
            return 0
        target_side = target[1]
        is_unit = target[0] == "board"

        # 免疫伤害：免疫一次即将受到的伤害（force 无视免疫）
        if not force and defender.get("immune", 0) > 0:
            defender["immune"] -= 1
            return 0

        card = getattr(self, "_current_card", None)
        # 计算最终攻击值
        if force:
            total = amount
        elif lifesteal:
            total = amount
            # 血红酒：😈 系生命吸取 +3
            if card is not None and _fx.has_element(card, "😈") and \
                    any(st["name"] == "血红酒"
                        for st in attacker_hero.get("statuses", [])):
                total += 3
            # 德古拉的斗篷：😈 系生命吸取 +1
            if card is not None and _fx.has_element(card, "😈") and \
                    self._has_equip(attacker_hero, "德古拉的斗篷😈"):
                total += 1
        else:
            total = amount + attacker_hero.get("atk", 0)
            # 攻击方寒冷：每层使攻击值 -1，攻击后寒冷 -2
            chill = attacker_hero.get("chill", 0)
            if chill > 0:
                total -= chill
                attacker_hero["chill"] = max(0, chill - 2)
            # 攻击方弱化 / 亡灵的嚎哭
            total -= _fx.weaken_amount(self, attacker_hero)
            if any(st["name"] == "亡灵的嚎哭"
                   for st in attacker_hero.get("statuses", [])):
                total -= 3
            # 元素强化 / 装备加成
            elem = _fx.card_element(card) if card is not None else None
            if elem == "🧊" and any(st["name"] == "冰系强化"
                                    for st in attacker_hero.get("statuses", [])):
                total += 1
            if elem == "⚡️" and self._has_equip(attacker_hero, "电击棒⚡️"):
                total += 3
            if elem == "😈" and self._has_equip(attacker_hero, "德古拉的斗篷😈"):
                total += 2
            if self._has_equip(attacker_hero, "指挥军刀"):
                total += 1
            # 莫诺的望远镜：下一张卡附带 5+追击 的攻击
            nb = attacker_hero.get("next_attack_bonus", 0)
            if nb > 0:
                total += nb
                attacker_hero["next_attack_bonus"] = 0
            # 追击：每次造成攻击额外附带追击等级的攻击
            total += attacker_hero.get("pursuit", 0)
            if not ignore_def:
                total -= defender.get("def", 0)
            # 蝠咬：受到的每次攻击来源 +4
            if any(st["name"] == "蝠咬"
                   for st in defender.get("statuses", [])):
                total += 4
            # 减伤：本回合受到的攻击减少 20%
            if any(st["name"] == "减伤"
                   for st in defender.get("statuses", [])):
                total = int(total * 0.8)
        total = max(0, total)

        # 易伤：受到攻击时额外受到易伤层数的攻击
        if not force:
            total += defender.get("vuln", 0)
        # 掩体：受到的每次攻击都变为 7 点
        if not force and (defender.get("mask", 0) > 0 or any(
                st["name"] == "掩体状态"
                for st in defender.get("statuses", []))):
            total = 7

        # 格挡吸收（造物无格挡）
        absorbed = 0
        if not force and not ignore_block:
            if not true:
                b1 = min(defender.get("block", 0), total)
                defender["block"] = defender.get("block", 0) - b1
                absorbed = b1
            if absorbed < total:
                b2 = min(defender.get("true_block", 0), total - absorbed)
                defender["true_block"] = defender.get("true_block", 0) - b2
                absorbed += b2
        dmg = total - absorbed
        # 吸收：格挡被首次打破时消耗一层，免疫该段攻击
        if (dmg > 0 and defender.get("absorb", 0) > 0
                and not force and not ignore_block):
            defender["absorb"] -= 1
            dmg = 0

        before = defender["hp"]
        defender["hp"] = max(0, defender["hp"] - dmg)
        actual = before - defender["hp"]

        # 流血：每受到一段攻击消耗 3 层造成 3 点伤害
        if defender.get("bleed", 0) >= 3 and total > 0:
            defender["bleed"] -= 3
            defender["hp"] = max(0, defender["hp"] - 3)
            actual += 3
            self._spawn_dmg_fx("-3", target)

        # 死舞锁血 / 庇护复活
        self._clamp_dead_dance(defender)
        self._maybe_revive(defender)

        # 生命吸取：按实际伤害回血
        if lifesteal and actual > 0:
            attacker_hero["hp"] = min(attacker_hero["max_hp"],
                                      attacker_hero["hp"] + actual)
            self._spawn_heal_fx(f"+{actual}", self._unit_target(attacker_hero))
            self._log(f"{self._side_label(attacker_hero) or '单位'} +{actual}")

        # 特效
        if absorbed > 0:
            self._spawn_block_fx("shake" if dmg == 0 else "break", target)
        if dmg > 0:
            self._spawn_dmg_fx(f"-{dmg}", target)
            if is_unit:
                self._spawn_unit_shake(("board", target_side, target[2]))
            else:
                self._spawn_unit_shake(("hero", target_side))

        # 标记本回合受过伤害
        if actual > 0:
            defender["damaged_this_turn"] = True
            self._log(f"{self._target_label(target)} -{actual}")
            self._on_deal_hooks(attacker_hero, defender, target, actual,
                                target_side)

        # 反制：受到超过 9 点伤害时反击所有敌人
        if actual > 9 and any(st["name"] == "反制"
                              for st in defender.get("statuses", [])):
            self._trigger_counter(defender)

        # 造物死亡移除
        if is_unit and defender["hp"] <= 0:
            board = self._board_of_side(target_side)
            self._remove_unit(board, defender)
        return actual

    def _deal_direct(self, hero, dmg, side):
        """纯伤害：越过格挡直接扣血（受防御减免后的值）"""
        if dmg <= 0:
            return
        hero["hp"] = max(0, hero["hp"] - dmg)
        self._spawn_dmg_fx(f"-{dmg}", self._unit_target(hero))
        self._log(f"{self._side_label(hero) or '单位'} -{dmg}")
        self._clamp_dead_dance(hero)
        self._maybe_revive(hero)

    def _clamp_dead_dance(self, hero):
        """死舞：生命值无论如何不会低于 1"""
        if any(st["name"] == "死舞" for st in hero.get("statuses", [])):
            if hero["hp"] < 1:
                hero["hp"] = 1

    def _maybe_revive(self, hero):
        """庇护：生命值归 0 时立即复活并恢复 9 点生命，获 6 回合虚弱"""
        if hero["hp"] <= 0:
            for st in list(hero.get("statuses", [])):
                if st["name"] == "庇护":
                    hero["statuses"].remove(st)
                    hero["hp"] = 9
                    self._apply_status(hero, {"name": "虚弱", "rounds": 6})
                    self._spawn_heal_fx("+9 复活", self._unit_target(hero))
                    self._log(f"{self._side_label(hero) or '单位'} +9 复活")
                    break

    def _trigger_counter(self, defender):
        """反制：对所有敌人施加虚弱/弱化/低迷/束缚各 1 回合"""
        target_side = "enemy" if defender is self.hero else "mine"
        # 所有敌人 = 与受击方敌对的一方
        enemy_side = "enemy" if target_side == "mine" else "mine"
        for t in _fx.enemy_units(self, enemy_side):
            tdef = self._target_obj(t)
            for name in ("虚弱", "弱化", "低迷", "束缚"):
                self._apply_status(tdef, {"name": name, "rounds": 1})
        # 清除反制状态
        defender["statuses"] = [st for st in defender.get("statuses", [])
                                if st["name"] != "反制"]

    def _on_deal_hooks(self, attacker_hero, defender, target, dmg,
                       target_side):
        """造成伤害时的装备/造物联动效果"""
        # 饮血剑：每造成 1 点伤害恢复 1 点生命
        if self._has_equip(attacker_hero, "饮血剑😈"):
            attacker_hero["hp"] = min(attacker_hero["max_hp"],
                                      attacker_hero["hp"] + dmg)
            self._spawn_heal_fx(f"+{dmg}", self._unit_target(attacker_hero))
            self._log(f"{self._side_label(attacker_hero) or '单位'} +{dmg}")
        # 寒冰剑：每造成一次伤害施加 6 层寒冷
        if self._has_equip(attacker_hero, "寒冰剑🧊") and not target[0] == "board":
            _fx.add_chill(self, defender, 6, target_side)
        # 锯齿：每段攻击额外施加 2 层流血
        if self._has_equip(attacker_hero, "锯齿"):
            _fx.add_stack(defender, "bleed", 2)
        # 铁血指虎：每段攻击给予 4 层流血（触发的流血层数 +2）
        if self._has_equip(attacker_hero, "铁血指虎"):
            _fx.add_stack(defender, "bleed", 6)
        # 冰冻鱼叉：攻击处于雪的目标额外叠加 2 层寒冷
        if self._has_equip(attacker_hero, "冰冻鱼叉🧊") and \
                defender.get("snow", 0) > 0:
            _fx.add_chill(self, defender, 2, target_side)
        # 狂刀战斧：每造成 8 点伤害使目标 -1 能量（一回合最多 3 次）
        if self._has_equip(attacker_hero, "狂刀战斧") and dmg >= 8:
            for e in self._equips_of(attacker_hero):
                if e["card"]["name"] == "狂刀战斧":
                    if e.get("triggers", 0) < 3:
                        e["triggers"] = e.get("triggers", 0) + 1
                        _fx.lose_energy(self, target_side, 1)

    def _chill_penalty(self, hero):
        """攻击方寒冷结算：每层使本次攻击值-1，攻击后寒冷层数-2（保留兼容）"""
        chill = hero.get("chill", 0)
        if chill <= 0:
            return 0
        hero["chill"] = max(0, chill - 2)
        return chill

    def _can_play(self, card, side):
        """出牌限制：虚弱 / 致盲 / 束缚"""
        hero = self.hero if side == "mine" else self.enemy_hero
        if (any(st["name"] == "虚弱" for st in hero["statuses"])
                and "获得虚弱" in card.get("desc", "")):
            self._show_notice("虚弱状态下无法使用该卡")
            return False
        if (any(st["name"] == "致盲" for st in hero["statuses"])
                and _fx.is_attack_card(card)):
            self._show_notice("致盲状态下无法使用攻击卡")
            return False
        if (any(st["name"] == "束缚" for st in hero["statuses"])
                and card.get("category") not in ("攻击卡", "防御卡")):
            self._show_notice("束缚状态下仅能使用攻击卡与防御卡")
            return False
        return True

    def _check_void(self, card, side):
        """返回 True 表示该卡效果被失效（没落/禁言/禁令）"""
        hero = self.hero if side == "mine" else self.enemy_hero
        if hero.get("card_void", 0) > 0:
            hero["card_void"] -= 1
            self._show_notice(f"【{card['name']}】效果被失效")
            return True
        if hero.get("next_card_void"):
            hero["next_card_void"] = False
            self._show_notice(f"【{card['name']}】效果被失效")
            return True
        return False

    def _check_game_over(self):
        """胜负判定：敌方血量归 0 胜利，自身血量归 0 失败"""
        if self.game_over is not None:
            return
        if self.enemy_hero["hp"] <= 0:
            self.game_over = "win"
        elif self.hero["hp"] <= 0:
            self.game_over = "lose"
        if self.game_over is not None:
            self.selected = None

    def _apply_status(self, hero, st):
        """给角色施加状态（同状态叠加刷新持续时间）"""
        hero.setdefault("statuses", [])
        for old in hero["statuses"]:
            if old["name"] == st["name"]:
                old["rounds"] = max(old["rounds"], st["rounds"])
                return
        hero["statuses"].append({"name": st["name"], "rounds": st["rounds"]})
        self._log(f"{self._side_label(hero) or '单位'} 获得「{st['name']}」"
                  f"{st['rounds']}回合")

    def _expire_statuses(self, hero):
        """单方回合结束时结算该方状态：rounds -1，到期移除并触发到期效果。
        （从 _tick_statuses 拆出，改为按「受影响方自己的回合」扣减，修复
        致盲等 1 回合状态在敌方回合结束即被提前扣没的问题。）"""
        keep = []
        # 快照遍历：到期触发的追加状态（如死舞/筑梦结束加虚弱）不参与本轮扣减
        for st in list(hero.get("statuses", [])):
            st["rounds"] -= 1
            if st["rounds"] > 0:
                keep.append(st)
                continue
            name = st["name"]
            if name in ("攻击提升", "攻击削减"):
                hero["atk"] -= st.get("amount", 0)
            elif name in ("防御提升", "防御削减"):
                hero["def"] -= st.get("amount", 0)
            elif name == "追击":
                hero["pursuit"] = max(0, hero.get("pursuit", 0)
                                      - st.get("level", 0))
            elif name == "死舞":
                self._apply_status(hero, {"name": "虚弱", "rounds": 3})
            elif name == "筑梦":
                self._apply_status(hero, {"name": "虚弱", "rounds": 2})
        hero["statuses"] = keep

    def _tick_statuses(self):
        """大回合结束：双方状态/层数结算"""
        msgs = []
        for label, hero, side, board in (
                ("我方", self.hero, "mine", self.board_mine),
                ("对方", self.enemy_hero, "enemy", self.board_enemy)):
            poison_stall = any(st["name"] == "毒停滞"
                               for st in hero.get("statuses", []))
            # 毒：回合结束受毒层攻击（受防御减免，越过格挡），毒层自然 -5
            if hero.get("poison", 0) > 0:
                dmg = max(0, hero["poison"] - hero.get("def", 0))
                if dmg > 0:
                    self._deal_direct(hero, dmg, side)
                    msgs.append(f"{label} 毒 -{dmg}")
                if not poison_stall:
                    hero["poison"] = max(0, hero["poison"] - 5)
            # 层数自然衰减
            hero["chill"] = max(0, hero.get("chill", 0) - 5)
            hero["bleed"] = max(0, hero.get("bleed", 0) - 3)
            hero["absorb"] = max(0, hero.get("absorb", 0) - 1)
            # 电感：层数取最长回合，回合结束自然 -2，回合耗尽消失
            if hero.get("charge_rounds", 0) > 0:
                hero["charge_rounds"] -= 1
                if hero["charge_rounds"] <= 0:
                    hero["charge"] = 0
                else:
                    hero["charge"] = max(0, hero["charge"] - 2)
            else:
                hero["charge"] = 0
            hero["mask"] = 0
            hero["vuln"] = 0
            hero["damaged_this_turn"] = False
            hero["格挡反击"] = False

            # 状态每回合效果
            neutral = {"atk": 0, "chill": 0, "statuses": []}
            for st in hero["statuses"]:
                name = st["name"]
                if name == "极寒":
                    hero["chill"] = hero.get("chill", 0) + 4
                elif name == "放血":
                    hero["bleed"] = hero.get("bleed", 0) + 4
                elif name == "鬼链":
                    hero["max_hp"] = max(1, hero["max_hp"] - 3)
                    hero["hp"] = min(hero["hp"], hero["max_hp"])
                elif name == "持续疗法":
                    _fx.heal(self, hero, 8)
                elif name == "强身健体":
                    hero["max_hp"] += 8
                    _fx.heal(self, hero, 4)
                elif name == "群体疗法":
                    _fx.heal(self, hero, 5)
                    for u in board:
                        u["hp"] = min(u.get("max_hp", u["card"]["health"]),
                                      u["hp"] + 5)
                elif name == "寒冰疗法":
                    _fx.heal(self, hero, 9)
                    hero["chill"] = hero.get("chill", 0) + 6
                elif name == "炙阳":
                    self._deal_target(neutral, ("hero", side), 6)
                elif name == "雷电乌云":
                    self._deal_target(neutral, ("hero", side), 7)
                    _fx.add_charge(self, hero, 2, 1)
                elif name == "亡灵的嚎哭":
                    pass  # 已在伤害结算中按 -3 处理

        if msgs:
            self.flash_msg = "状态结算：" + "，".join(msgs)
            self.root.after(1800, self._clear_notice)

    def _tick_equips(self):
        """大回合结束：装备/造物回合数 -1，到期弃置（移除加成、返还能量）"""
        groups = [(self.hero_equips, self.hero, "mine"),
                  (self.enemy_equips, self.enemy_hero, "enemy")]
        for group, hero, side in groups:
            # 装备每回合效果（树人图腾/护身的古老符文/冰息铠甲）
            for item in group:
                name = item["card"]["name"]
                if name == "树人图腾":
                    _fx.gain_true_block(self, hero, 4)
                    _fx.gain_block(self, hero, 5)
                elif name == "护身的古老符文":
                    _fx.heal(self, hero, 3)
                elif name == "冰息铠甲🧊":
                    hero["chill"] = hero.get("chill", 0) + 8
                    _fx.gain_true_block(self, hero, 8)
            keep = []
            for item in group:
                if item["rounds"] in (None, -1):
                    keep.append(item)
                    continue
                item["rounds"] -= 1
                if item["rounds"] <= 0:
                    card = item["card"]
                    hero["atk"] -= card.get("atk_bonus", 0)
                    hero["def"] -= card.get("def_bonus", 0)
                    # 德古拉的斗篷：装备结束后提升 8 点生命上限
                    if card["name"] == "德古拉的斗篷😈":
                        hero["max_hp"] += 8
                        hero["hp"] = min(hero["hp"], hero["max_hp"])
                    px, py = self._random_played_pos()
                    self.played.append((card, px, py))
                else:
                    keep.append(item)
            group[:] = keep

        # 造物时限到期
        for board, side in ((self.board_mine, "mine"),
                            (self.board_enemy, "enemy")):
            keep = []
            for unit in board:
                if unit["rounds"] in (None, -1):
                    keep.append(unit)
                    continue
                unit["rounds"] -= 1
                if unit["rounds"] <= 0:
                    kind = unit.get("craft_kind")
                    if kind == "能量玩偶":
                        _fx.gain_energy(self, side, 3)
                    elif kind == "十字军":
                        _fx.gain_energy(self, side, 1)
                    px, py = self._random_played_pos()
                    self.played.append((unit["card"], px, py))
                else:
                    keep.append(unit)
            board[:] = keep

    # ---------- 弃牌窗口 ----------
    def _open_discard_window(self, after_discard):
        """弹出弃牌窗口：显示全部手牌，点击选中（上移），确认后弃掉"""
        side, need = self.discard
        hand = self.hand if side == "mine" else self.enemy_hand
        who = "我方" if side == "mine" else "对方"

        win = tk.Toplevel(self.root)
        win.title(f"{who}弃牌")
        win.configure(bg="#2b2b2b")
        win.resizable(False, False)
        win.transient(self.root)

        # 顶部提示
        tk.Label(win, text=f"【{who}】手牌超出 {HAND_LIMIT} 张上限，"
                           f"请点击选中要弃的卡牌（共需弃 {need} 张，再次点击取消选中）",
                 bg="#2b2b2b", fg="#ffd700",
                 font=("Microsoft YaHei", -13)).pack(pady=(12, 6))

        # 卡牌展示画布
        cw, ch = 1000, 270
        canvas = tk.Canvas(win, width=cw, height=ch, bg="#1e1e1e",
                           highlightthickness=0)
        canvas.pack()

        # 底部栏：提示 + 计数 + 确认按钮
        bottom = tk.Frame(win, bg="#2b2b2b")
        bottom.pack(fill="x", padx=16, pady=(6, 12))

        count_label = tk.Label(bottom, text=f"0/{need}", bg="#2b2b2b",
                               fg="#4fc3f7",
                               font=("Arial", -20, "bold"))
        count_label.pack(side="right")          # 右下角：选中数/需弃数
        confirm_btn = tk.Button(bottom, text="确认弃牌", bg="#4caf50",
                                fg="#ffffff", activebackground="#66bb6a",
                                activeforeground="#ffffff",
                                font=("Microsoft YaHei", -13),
                                command=None)
        confirm_btn.pack(side="right", padx=(0, 16))
        hint = tk.Label(bottom, text="", bg="#2b2b2b", fg="#ff5555",
                        font=("Microsoft YaHei", -11))
        hint.pack(side="left")

        sel = set()     # 已选中的手牌位置

        def redraw():
            canvas.delete("all")
            xs = card_positions(len(hand), 20, cw - 20)
            # 先画未选中的卡牌，再画选中的（最上层，向上位移 20 像素）
            order = [i for i in range(len(hand)) if i not in sel]
            order += sorted(sel)
            for i in order:
                x = xs[i]
                y = 40 - (HOVER_LIFT if i in sel else 0)
                self.draw_card(canvas, x, y, CARD_W, CARD_H,
                               self._card_of(hand[i]))

        def on_click(event):
            # 重叠卡牌从右到左检测（最上层优先）
            xs = card_positions(len(hand), 20, cw - 20)
            for i in range(len(hand) - 1, -1, -1):
                x = xs[i]
                y = 40 - (HOVER_LIFT if i in sel else 0)
                if x <= event.x <= x + CARD_W and y <= event.y <= y + CARD_H:
                    # 切换选中状态
                    if i in sel:
                        sel.discard(i)
                    else:
                        sel.add(i)
                    break
            redraw()
            count_label.config(text=f"{len(sel)}/{need}")

        def confirm():
            if len(sel) != need:
                hint.config(text=f"还需选择 {need - len(sel)} 张卡牌")
                return
            # 弃掉选中的卡牌：堆叠到战场区
            for pos in sorted(sel, reverse=True):
                entry = hand.pop(pos)
                px, py = self._random_played_pos()
                self.played.append((self._card_of(entry), px, py))
            self.discard = None
            win.destroy()
            # 弃牌完成后执行真正的回合结束
            if after_discard is not None:
                after_discard()

        canvas.bind("<Button-1>", on_click)
        confirm_btn.config(command=confirm)
        redraw()
        win.grab_set()      # 模态：完成弃牌前无法操作主窗口

    # ---------- 出牌 / 回合 ----------
    # ---------- 出牌 / 回合 ----------
    def _effective_cost(self, card, side):
        """计算实际耗能（冰系节能 / 治疗增效 / 恶魂十字架 / 科学怪人研究）"""
        cost = card["cost"]
        hero = self.hero if side == "mine" else self.enemy_hero
        elem = _fx.card_element(card)
        if elem == "🧊" and any(st["name"] == "冰系节能"
                                for st in hero.get("statuses", [])):
            cost -= 1
        if "恢复" in card.get("desc", "") and any(
                st["name"] == "治疗增效" for st in hero.get("statuses", [])):
            cost -= 1
        if (elem == "😈" and self._has_equip(hero, "恶魂十字架😈")
                and hero["hp"] == hero["max_hp"]
                and not self._demon_played[side]):
            cost -= 1
        for u in self._board_of_side(side):
            if u.get("craft_kind") == "科学怪人":
                r = u.get("research", 0)
                if r >= 1 and card.get("category") == "装备卡":
                    cost -= 1
                if r >= 2 and card.get("category") == "魔法卡":
                    cost -= 1
        return max(0, cost)

    def _craft_atk(self, card):
        """根据造物卡名返回其攻击值（可手动攻击的造物）"""
        return {"十字军": 4, "亡灵石像😈": 6, "蜉蝣电击器⚡️": 2,
                "幽影蝙蝠😈": 2, "死亡毒蛛🤢": 2,
                "极寒冰龙 🧊": 6}.get(card["name"], 0)

    def _on_play_hooks(self, card, side, attacker):
        """打出卡牌时的装备/状态联动"""
        elem = _fx.card_element(card)
        if elem == "😈":
            self._demon_played[side] = True
            # 恶灵的契约：😈 卡损失 1 点生命上限，每损失 4 点获得 1 能量
            for e in self._equips_of(attacker):
                if e["card"]["name"] == "恶灵的契约😈":
                    attacker["max_hp"] = max(1, attacker["max_hp"] - 1)
                    attacker["hp"] = min(attacker["hp"], attacker["max_hp"])
                    e["lost"] = e.get("lost", 0) + 1
                    if e["lost"] % 4 == 0:
                        _fx.gain_energy(self, side, 1)

    def _play_selected(self):
        """将选中卡牌从手牌打出，扣除能量并统一调度效果"""
        side, pos = self.selected
        if side == "mine":
            hand_list, cost_attr = self.hand, "mana"
        else:
            hand_list, cost_attr = self.enemy_hand, "enemy_mana"
        card = self._card_of(hand_list[pos])

        if not self._can_play(card, side):
            return

        cost = self._effective_cost(card, side)
        if cost > getattr(self, cost_attr):
            self._show_notice("能量不足")
            return

        # 扣费并打出
        setattr(self, cost_attr, getattr(self, cost_attr) - cost)
        hand_list.pop(pos)

        voided = self._check_void(card, side)
        attacker = self.hero if side == "mine" else self.enemy_hero
        ctype = card.get("type", "normal")
        who = "我方" if side == "mine" else "敌方"

        if ctype == "equip":
            # 先记「打出」，再记装备生效，保证记录栏顺序：动作 → 效果
            self._log(f"{who} 打出「{card['name']}」")
            group = (self.hero_equips if side == "mine"
                     else self.enemy_equips)
            rounds = card.get("duration") or 0
            group.append({"card": card, "rounds": rounds})
            attacker["atk"] += card.get("atk_bonus", 0) or 0
            attacker["def"] += card.get("def_bonus", 0) or 0
            tail = f"（持续{rounds}回合）" if rounds > 0 else "（永久）"
            self._log(f"{who} 装备「{card['name']}」{tail}")
            if not voided:
                resolve(self, card, side, [])
        elif ctype == "craft":
            self._log(f"{who} 打出「{card['name']}」")
            if card.get("health"):
                board = self._board_of_side(side)
                unit = {"card": card, "hp": card["health"],
                        "max_hp": card["health"],
                        "atk": self._craft_atk(card),
                        "can_attack": True, "rounds": card["duration"],
                        "x": 0, "y": 0}
                board.append(unit)
                if not voided:
                    resolve(self, card, side, [])
                if unit.get("craft_kind") == "亡灵石像":
                    unit["can_attack"] = False
                self._log(f"{who} 召唤「{card['name']}」"
                          f" 攻{unit['atk']}/血{unit['hp']}"
                          f"（位置 {len(board)}）")
            else:
                self._show_notice(f"【{card['name']}】效果尚未实装")
                px, py = self._random_played_pos()
                self.played.append((card, px, py))
        else:
            # normal 无目标卡（恢复自身 / 群体类）
            self._log(f"{who} 打出「{card['name']}」")
            if not voided:
                ok = resolve(self, card, side, [])
                if not ok:
                    self._show_notice(f"【{card['name']}】效果尚未实装")
            px, py = self._random_played_pos()
            self.played.append((card, px, py))

        self.play_history.append(card["name"])
        self._on_play_hooks(card, side, attacker)

        self._check_game_over()
        self.selected = None
        self.draw()

    def _resolve_target_attack(self, src, targets):
        """施法目标确定：结算攻击（手牌攻击卡可多目标，站场造物单目标）"""
        if src[0] == "hand":
            side = self.turn
            hand = self.hand if side == "mine" else self.enemy_hand
            card = self._card_of(hand[src[1]])
            cost_attr = "mana" if side == "mine" else "enemy_mana"
            cost = self._effective_cost(card, side)
            if cost > getattr(self, cost_attr):
                self._show_notice("能量不足")
                self.targeting = None
                return
            if not self._can_play(card, side):
                self.targeting = None
                return
            setattr(self, cost_attr, getattr(self, cost_attr) - cost)
            hand.pop(src[1])
            attacker = self.hero if side == "mine" else self.enemy_hero
            voided = self._check_void(card, side)
            # 先记「打出 → 目标」，再结算效果，保证记录栏顺序：动作 → 效果
            who = "我方" if side == "mine" else "敌方"
            tgt = "、".join(self._target_label(t) for t in targets)
            self._log(f"{who} 打出「{card['name']}」→ {tgt}")
            if not voided:
                ok = resolve(self, card, side, targets)
                if not ok:
                    self._show_notice(f"【{card['name']}】效果尚未实装")
            self.play_history.append(card["name"])
            self._on_play_hooks(card, side, attacker)
            px, py = self._random_played_pos()
            self.played.append((card, px, py))
        else:
            # 站场造物攻击：每回合限一次
            side, idx = src[1], src[2]
            board = self.board_mine if side == "mine" else self.board_enemy
            unit = board[idx]
            self._deal_unit_damage(unit, targets[0], side)
            self._log(f"{'我方' if side == 'mine' else '敌方'}「{unit['card']['name']}」攻击")
            unit["can_attack"] = False
            if unit["hp"] <= 0:
                self._remove_unit(board, unit)
        self._check_game_over()
        self.targeting = None
        self.draw()

    def _deal_unit_damage(self, unit, target, side):
        """站场造物攻击目标的结算（互撞 / 攻击主角色）"""
        attacker_hero = self.hero if side == "mine" else self.enemy_hero
        dmg = unit.get("atk", 0)
        if dmg <= 0:
            return
        # 造物攻击视为「攻击」，受攻击方攻击力加成与防御减免
        self._deal_target(attacker_hero, target, dmg)

    def _remove_unit(self, board, unit):
        """移除死亡造物：从战场移除并堆叠到纪念堆"""
        if unit in board:
            board.remove(unit)
        px, py = self._random_played_pos()
        self.played.append((unit["card"], px, py))

    def _end_turn(self):
        """点击结束回合：先判定弃牌机制，无超限或弃完后再切换回合"""
        side = self.turn
        self.selected = None
        self.targeting = None
        over = self._hand_over(side)
        if over > 0:
            # 自身回合结束时检查：超上限则弹出弃牌窗口，弃完后自动完成回合结束
            self.discard = (side, over)
            self.draw()
            self._open_discard_window(after_discard=self._finish_turn)
        else:
            self._finish_turn()

    def _tick_crafts(self, side):
        """回合边界：结算该方造物的被动回合效果"""
        board = self.board_mine if side == "mine" else self.board_enemy
        hero = self.hero if side == "mine" else self.enemy_hero
        eside = "enemy" if side == "mine" else "mine"
        for unit in board:
            kind = unit.get("craft_kind")
            if kind == "制冷机":
                unit["phase"] = unit.get("phase", 0) + 1
                for t in _fx.enemy_units(self, side):
                    _fx.add_chill(self, self._target_obj(t), 7, t[1])
                if unit["phase"] % 2 == 0:
                    for t in _fx.enemy_units(self, side):
                        _fx.add_snow(self, self._target_obj(t), 1, t[1])
            elif kind == "能量玩偶":
                _fx.gain_energy(self, side, 1)
            elif kind == "九翼天使":
                if unit.get("reviving", False):
                    unit["revive_rounds"] = unit.get("revive_rounds", 0) - 1
                    if unit["revive_rounds"] <= 0:
                        unit["reviving"] = False
                        unit["hp"] = 12
                else:
                    _fx.heal(self, hero, 6)
            elif kind == "科学怪人":
                unit["research"] = min(2, unit.get("research", 0) + 1)
            elif kind == "亡灵石像":
                if unit.get("inactive", 0) > 0:
                    unit["inactive"] -= 1
                    if unit["inactive"] <= 0:
                        unit["can_attack"] = True
            elif kind == "天外来物":
                eb = self.board_enemy if side == "mine" else self.board_mine
                if eb:
                    self._remove_unit(eb, eb[0])
                    _fx.heal(self, hero, 6)
                else:
                    self._deal_target(hero, ("hero", eside), 8, force=True)
                    _fx.heal(self, hero, 6)

    def _finish_turn(self):
        """真正结束回合：切换回合方，加能量，结算，新回合方先抽牌"""
        # 回合结束方：临时格挡（仅存半回合）到期
        end_hero = self.hero if self.turn == "mine" else self.enemy_hero
        if end_hero.get("temp_block"):
            end_hero["block"] = 0
            end_hero["temp_block"] = False
        # 回合结束方：其状态回合数 -1（致盲/束缚/虚弱等按其自身回合计持续）
        self._expire_statuses(end_hero)

        self.turn = "enemy" if self.turn == "mine" else "mine"
        board = self.board_mine if self.turn == "mine" else self.board_enemy
        for unit in board:
            if unit.get("craft_kind") == "亡灵石像" and unit.get("inactive", 0) > 0:
                unit["can_attack"] = False
            else:
                unit["can_attack"] = True

        # 新回合方获得能量（扣除能量惩罚）
        penalty = self.energy_penalty.get(self.turn, 0)
        gain = max(0, TURN_MANA - penalty)
        self.energy_penalty[self.turn] = 0
        if self.turn == "mine":
            self.mana = min(MAX_MANA, self.mana + gain)
            # 双方各结束一个回合 = 一个完整回合
            self.round += 1
            self._tick_equips()
            self._tick_statuses()
            self._tick_crafts("mine")
            self._tick_crafts("enemy")
            self._check_game_over()
        else:
            self.enemy_mana = min(MAX_MANA, self.enemy_mana + gain)

        # 格挡清 0（修补：延迟一回合持续时间）
        new_hero = self.hero if self.turn == "mine" else self.enemy_hero
        if not new_hero.get("block_persist"):
            new_hero["block"] = 0
        else:
            new_hero["block_persist"] = False

        # 结算延迟效果（下回合触发）
        self._process_pending()
        self._check_game_over()

        # 重置本回合 😈 卡标记
        self._demon_played[self.turn] = False

        self.draw()
        self._start_draw_animation(self.turn)

    # ---------- 交互 ----------
    def _hit_hand(self, x, y, rects):
        """重叠手牌从右到左检测（最上层优先），返回位置索引或 None"""
        for i in range(len(rects) - 1, -1, -1):
            if self._in_rect(x, y, rects[i]):
                return i
        return None

    def _src_side(self, src):
        """返回攻击来源所属方：手牌来源为当前回合方，造物来源为造物所属方"""
        if src[0] == "hand":
            return self.turn
        return src[1]

    def _friendly_allowed(self):
        """是否允许选择友方单位为目标（特殊卡机制，当前卡池无此类卡）"""
        src = self.targeting["src"]
        if src[0] == "hand":
            hand = self.hand if self.turn == "mine" else self.enemy_hand
            return bool(self._card_of(hand[src[1]]).get("friendly_target"))
        return False

    def _src_card(self):
        """返回当前施法来源的卡牌数据（手牌攻击卡或造物卡）"""
        src = self.targeting["src"]
        if src[0] == "hand":
            hand = self.hand if self.turn == "mine" else self.enemy_hand
            return self._card_of(hand[src[1]])
        side, idx = src[1], src[2]
        unit = (self.board_mine if side == "mine"
                else self.board_enemy)[idx]
        return unit["card"]

    def _src_hits(self):
        """返回当前施法来源的攻击段数（决定最多分配几段）"""
        return self._src_card().get("hits", 1)

    def _max_targets(self):
        """返回当前施法来源至多可选的目标数（默认为 1）"""
        return self._src_card().get("max_targets", 1)

    def _find_target_at(self, x, y, attacker_side):
        """返回坐标处的合法攻击目标（敌方主角色/敌方造物），无则返回 None"""
        enemy_side = "enemy" if attacker_side == "mine" else "mine"
        # 敌方主角色
        box = ENEMY_HERO_BOX if enemy_side == "enemy" else MINE_HERO_BOX
        if self._in_rect(x, y, box):
            return ("hero", enemy_side)
        # 敌方战场造物
        board = self.board_enemy if enemy_side == "enemy" else self.board_mine
        for idx, unit in enumerate(board):
            rect = (unit["x"], unit["y"], unit["x"] + BOARD_W,
                    unit["y"] + BOARD_H)
            if self._in_rect(x, y, rect):
                return ("board", enemy_side, idx)
        # 特殊卡可指定友方单位（机制预留）
        if self._friendly_allowed():
            box2 = MINE_HERO_BOX if enemy_side == "enemy" else ENEMY_HERO_BOX
            if self._in_rect(x, y, box2):
                return ("hero", attacker_side)
            board2 = (self.board_mine if enemy_side == "enemy"
                      else self.board_enemy)
            for idx, unit in enumerate(board2):
                rect = (unit["x"], unit["y"], unit["x"] + BOARD_W,
                        unit["y"] + BOARD_H)
                if self._in_rect(x, y, rect):
                    return ("board", attacker_side, idx)
        return None

    def on_click(self, event):
        """处理鼠标点击"""
        # 0. 游戏结束、动画或弃牌模式中禁止交互（弃牌由弹窗处理）
        if (self.game_over is not None or self.anim is not None
                or self.discard is not None):
            return

        # 1. 施法目标选择模式：取消/施法按钮 / 点目标分配攻击段 / 点空白退出
        if self.targeting is not None:
            for (bx1, by1, bx2, by2, action) in self.buttons:
                if self._in_rect(event.x, event.y, (bx1, by1, bx2, by2)):
                    if action == "cancel_target":
                        self.targeting = None
                        self.draw()
                    elif action == "cast" and self.targeting["targets"]:
                        self._resolve_target_attack(self.targeting["src"],
                                                    self.targeting["targets"])
                    return
            src = self.targeting["src"]
            side = self._src_side(src)
            target = self._find_target_at(event.x, event.y, side)
            if target is not None:
                if self._max_targets() <= 1:
                    # 单目标卡：点击目标直接施法
                    self._resolve_target_attack(src, [target])
                else:
                    # 多目标卡：点击目标分配一段攻击（同一目标可重复分配）
                    targets = self.targeting["targets"]
                    distinct = set(targets)
                    if (target not in distinct
                            and len(distinct) >= self._max_targets()):
                        self._show_notice(f"至多选择 {self._max_targets()} 个目标")
                        return
                    targets.append(target)
                    if len(targets) >= self._src_hits():
                        # 攻击段数用尽：自动施法
                        self._resolve_target_attack(src, targets)
                    else:
                        self.draw()
            else:
                # 点击空白处：退出施法
                self.targeting = None
                self.draw()
            return

        # 2. 按钮
        for (bx1, by1, bx2, by2, action) in self.buttons:
            if self._in_rect(event.x, event.y, (bx1, by1, bx2, by2)):
                if action == "end_turn":
                    self._end_turn()
                elif action == "play":
                    self._play_selected()   # 内部自行重绘或显示提示
                else:   # cancel
                    self.selected = None
                    self.draw()
                return

        # 3. 放大卡牌本身：点击取消选中
        if self.selected is not None and self.zoom_rect is not None:
            if self._in_rect(event.x, event.y, self.zoom_rect):
                self.selected = None
                self.draw()
                return

        # 4. 我方战场造物：可攻击则进入攻击施法，否则提示
        for idx, unit in enumerate(self.board_mine):
            rect = (unit["x"], unit["y"], unit["x"] + BOARD_W,
                    unit["y"] + BOARD_H)
            if self._in_rect(event.x, event.y, rect):
                if self.turn == "mine" and unit["can_attack"]:
                    self.targeting = {"src": ("board", "mine", idx),
                                      "mouse": (event.x, event.y),
                                      "hover_target": None, "targets": []}
                else:
                    self._show_notice("该造物本回合无法攻击")
                self.draw()
                return

        # 5. 对方战场造物（代操作对称）
        for idx, unit in enumerate(self.board_enemy):
            rect = (unit["x"], unit["y"], unit["x"] + BOARD_W,
                    unit["y"] + BOARD_H)
            if self._in_rect(event.x, event.y, rect):
                if self.turn == "enemy" and unit["can_attack"]:
                    self.targeting = {"src": ("board", "enemy", idx),
                                      "mouse": (event.x, event.y),
                                      "hover_target": None, "targets": []}
                else:
                    self._show_notice("该造物本回合无法攻击")
                self.draw()
                return

        # 6. 我方手牌：攻击卡（当前回合）进入施法，其余选中/取消选中
        hit = self._hit_hand(event.x, event.y, self.hand_rects)
        if hit is not None:
            card = self._card_of(self.hand[hit])
            if (self.turn == "mine" and card.get("type", "normal") == "normal"
                    and needs_target(card)):
                # 需选目标的卡：进入施法目标选择模式（拖动光标指向目标）
                self.selected = None
                self.targeting = {"src": ("hand", hit),
                                  "mouse": (event.x, event.y),
                                  "hover_target": None, "targets": []}
            else:
                self.selected = (None if self.selected == ("mine", hit)
                                 else ("mine", hit))
            self.draw()
            return

        # 7. 对方手牌（代操作对称）
        hit = self._hit_hand(event.x, event.y, self.enemy_rects)
        if hit is not None:
            card = self._card_of(self.enemy_hand[hit])
            if (self.turn == "enemy" and card.get("type", "normal") == "normal"
                    and needs_target(card)):
                self.selected = None
                self.targeting = {"src": ("hand", hit),
                                  "mouse": (event.x, event.y),
                                  "hover_target": None, "targets": []}
            else:
                self.selected = (None if self.selected == ("enemy", hit)
                                 else ("enemy", hit))
            self.draw()
            return

        # 8. 空白处：取消选中
        if self.selected is not None:
            self.selected = None
            self.draw()

    def on_right_click(self, event):
        """右键：撤销施法中最后分配的一段攻击"""
        if self.targeting is None or self._max_targets() <= 1:
            return
        if self.targeting["targets"]:
            self.targeting["targets"].pop()
            self.draw()

    def on_motion(self, event):
        """鼠标移动：施法中更新箭头与悬停目标；否则更新各类悬停（变化时才重绘）"""
        if (self.game_over is not None or self.anim is not None
                or self.discard is not None):
            return

        # 施法目标选择中：更新箭头终点与悬停目标（高亮），仍可查看状态栏说明
        if self.targeting is not None:
            self.targeting["mouse"] = (event.x, event.y)
            side = self._src_side(self.targeting["src"])
            self.targeting["hover_target"] = self._find_target_at(
                event.x, event.y, side)
            new_status = None
            for s, box in (("enemy", ENEMY_BOX), ("mine", HAND_BOX)):
                sx1, sy1 = box[2] - 334, box[3] - 45
                sx2, sy2 = box[2] - 14, box[3] - 11
                if sx1 <= event.x <= sx2 and sy1 <= event.y <= sy2:
                    new_status = s
                    break
            self.hover_status = new_status
            self.draw()
            return

        # 战场造物悬停（优先于缩略块判定，避免浮层重叠）
        new_board = None
        for side, board in (("enemy", self.board_enemy),
                            ("mine", self.board_mine)):
            for idx, unit in enumerate(board):
                rect = (unit["x"], unit["y"], unit["x"] + BOARD_W,
                        unit["y"] + BOARD_H)
                if self._in_rect(event.x, event.y, rect):
                    new_board = (side, idx)
                    break
            if new_board is not None:
                break

        # 手牌悬停（从右到左，最上层优先）
        new_hover = None
        if new_board is None:
            hit = self._hit_hand(event.x, event.y, self.hand_rects)
            if hit is not None:
                new_hover = ("mine", hit)
            else:
                hit = self._hit_hand(event.x, event.y, self.enemy_rects)
                if hit is not None:
                    new_hover = ("enemy", hit)

        # 状态栏悬停
        new_status = None
        for side, box in (("enemy", ENEMY_BOX), ("mine", HAND_BOX)):
            sx1, sy1 = box[2] - 334, box[3] - 45
            sx2, sy2 = box[2] - 14, box[3] - 11
            if sx1 <= event.x <= sx2 and sy1 <= event.y <= sy2:
                new_status = side
                break

        # 装备/造物缩略块悬停（战场造物悬停优先）
        new_item = None
        if new_board is None:
            for side, kind, idx, rect in self.bar_item_rects:
                if self._in_rect(event.x, event.y, rect):
                    new_item = (side, kind, idx)
                    break

        if (new_hover != self.hand_hover
                or new_status != self.hover_status
                or new_item != self.hover_item
                or new_board != self.board_hover):
            self.hand_hover = new_hover
            self.hover_status = new_status
            self.hover_item = new_item
            self.board_hover = new_board
            self.draw()


if __name__ == "__main__":
    root = tk.Tk()
    CardApp(root)
    root.mainloop()
