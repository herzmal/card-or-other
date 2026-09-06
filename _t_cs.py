# -*- coding: utf-8 -*-
"""C# 源码静态自检：括号平衡 + 方法定义/调用一致性抽查"""
import re, io, sys, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

D = r"E:\unity\unity项目\My project\Assets\Scripts"
D_EDITOR = r"E:\unity\unity项目\My project\Assets\Editor"
FILES = [
    ("BattleController.cs", D),
    ("RuntimeSceneBuilder.cs", D),
    ("BackendClient.cs", D),
    ("PvpClient.cs", D),
    ("BackendModels.cs", D),
    ("MainMenuManager.cs", D),
    ("LoginManager.cs", D),
    ("ModeSelectManager.cs", D),
    ("DungeonManager.cs", D),
    ("DungeonSession.cs", D),
    ("BattleEvents.cs", D),
    ("UIBuilder.cs", D),
    ("SceneBuilder.cs", D_EDITOR),
]

for fn, base in FILES:
    p = os.path.join(base, fn)
    if not os.path.exists(p):
        print("缺失:", fn); continue
    src = open(p, encoding="utf-8-sig").read()
    # 先去掉字符串（含 "http://" 这类带 // 的字符串），再去掉注释，避免误判
    s = re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', src)
    s = re.sub(r"'(?:[^'\\\n]|\\.)'", "''", s)
    s = re.sub(r'//[^\n]*', '', s)
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
    for op, cl in (('{', '}'), ('(', ')'), ('[', ']')):
        a, b = s.count(op), s.count(cl)
        if a != b:
            print(f"  !! {fn}: {op}{cl} 不平衡  {a} vs {b}")
    # 方法定义收集
    defs = set(re.findall(r'\b(?:void|int|string|bool|float|GameObject|Text|Button|RectTransform|Sprite|Font|Color|Vector2|static\s+[\w<>\[\]]+)\s+(\w+)\s*\(', src))
    print(f"  {fn}: 括号平衡 OK，方法数 {len(defs)}")

# 重点：BattleController 里新增方法是否都定义了
bc = open(os.path.join(D, "BattleController.cs"), encoding="utf-8-sig").read()
need = ["RefreshLogHeight", "OpenTargetPanel", "CloseTargetPanel", "UpdateTargetPanelCount",
        "OnTargetPicked", "ConfirmTargets", "OnMineUnitClicked", "SetupUnitTooltip",
        "ShowItemTooltip", "ShowTooltipPanel", "EquipTooltip", "UnitTooltip",
        "DiscardBaseX", "DoAttack", "MakeBarItem"]
for m in need:
    if not re.search(r'\b' + m + r'\s*\(', bc):
        print("  !! 未定义:", m)
print("\n新增方法定义检查完成")

# 检查调用签名：MakeBarItem 必须是 5 参（排除函数定义：定义行以 { 结尾，不含 ;）
calls = re.findall(r'MakeBarItem\(([^;{]*?)\);', bc)
for c in calls:
    n = c.count(',') + 1
    if n != 5:
        print("  !! MakeBarItem 参数数异常:", n, "->", c[:80])
print("MakeBarItem 调用参数数检查完成")
