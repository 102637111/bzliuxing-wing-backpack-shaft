"""尺寸示意图: 正视图 + 过轴剖面 (单位 mm)

SPAN_DEG 默认 160 (8 齿 -> 20°/齿); TAG 控制输出文件名; OUT 控制输出目录
"""
import os
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib import font_manager
from matplotlib.patches import Circle, Rectangle, Polygon

CJK = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
if not os.path.exists(CJK):                       # 其他发行版/系统自动找
    import glob
    _c = glob.glob("/usr/share/fonts/**/NotoSansCJK*Regular*", recursive=True)
    CJK = _c[0] if _c else CJK
try:
    font_manager.fontManager.addfont(CJK)
    plt.rcParams["font.family"] = "Noto Sans CJK SC"
except Exception as e:
    print("font warn:", e)
plt.rcParams["axes.unicode_minus"] = False

OUT = os.environ.get("OUT", ".")   # 输出目录 (默认当前目录)

# ---- 参数 (与 build_connector_v3.py 一致) ----
TEETH_N = 8
SPAN_DEG = float(os.environ.get("SPAN_DEG", "160"))
TAG = os.environ.get("TAG", "model")
CENTER_DEG = 180.0        # 扇区中心 = 与轴相反
TIP_OD = 12.0
ROOT_OD = 10.2
GEAR_T = 2.0
UPPER_OD = 9.0
UPPER_T = 2.0
BORE = float(os.environ.get("BORE_D", 5.0))
SHAFT_D = float(os.environ.get("SHAFT_D", 5.0))
SHAFT_L = 11.0
SHAFT_FLUSH = os.environ.get("SHAFT_FLUSH", "0") == "1"
FLUSH_CLEAR = 0.1
TOTAL = GEAR_T + UPPER_T
AXIS_Z = TOTAL / 2

R_TIP, R_ROOT = TIP_OD / 2, ROOT_OD / 2
PITCH = np.radians(SPAN_DEG) / TEETH_N
HALF = PITCH / 2
W_TIP, W_ROOT = 0.22 * HALF, 0.28 * HALF
SPAN = np.radians(SPAN_DEG) / 2


def gear_radius(th):
    d = (th - np.radians(CENTER_DEG) + np.pi) % (2 * np.pi) - np.pi
    r = np.full_like(d, R_ROOT)
    m = np.abs(d) <= SPAN
    di = d[m]
    k = np.clip(np.round(di / PITCH + (TEETH_N - 1) / 2), 0, TEETH_N - 1)
    u = np.abs(di - (k - (TEETH_N - 1) / 2) * PITCH)
    t = np.clip((u - W_TIP) / (HALF - W_ROOT - W_TIP), 0, 1)
    rr = R_TIP + (R_ROOT - R_TIP) * 0.5 * (1 - np.cos(np.pi * t))
    rr = np.where(u <= W_TIP, R_TIP, rr)
    rr = np.where(u >= HALF - W_ROOT, R_ROOT, rr)
    r[m] = rr
    return r

C_GEAR = "#8ea6c0"
C_RING = "#5f7f9e"
C_SHAFT = "#d99a6c"
C_EDGE = "#243447"
TXT = "#1f2a36"

fig = plt.figure(figsize=(15, 6.8))
gs = fig.add_gridspec(1, 2, width_ratios=[29.0, 29.5], wspace=0.05)
ax1 = fig.add_subplot(gs[0, 0])
ax2 = fig.add_subplot(gs[0, 1])

# ================= 正视图 =================
th = np.linspace(0, 2 * np.pi, 1800)
r = gear_radius(th)
ax1.add_patch(Polygon(np.c_[r * np.cos(th), r * np.sin(th)], closed=True,
                      fc=C_GEAR, ec=C_EDGE, lw=1.4, zorder=2))
ax1.add_patch(Circle((0, 0), UPPER_OD / 2, fc=C_RING, ec=C_EDGE, lw=1.2, zorder=3))
ax1.add_patch(Circle((0, 0), BORE / 2, fc="white", ec=C_EDGE, lw=1.2, zorder=4))
# 轴: 中面高度, 半透明表示在圆环前表面之后
ax1.add_patch(Rectangle((R_ROOT - 1.0, -SHAFT_D / 2), SHAFT_L + 1.0, SHAFT_D,
                        fc=C_SHAFT, ec=C_EDGE, lw=1.0, alpha=0.6, zorder=5))
ax1.plot([0, R_ROOT + SHAFT_L], [0, 0], ls=":", color="#555", lw=0.9, zorder=6)

def dim_h(ax, y, x0, x1, label, color=TXT, fs=10.5, va="bottom", dy=0.25):
    ax.annotate("", xy=(x0, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.15))
    ax.text((x0 + x1) / 2, y + (dy if va == "bottom" else -dy), label,
            ha="center", va=va, fontsize=fs, color=color,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

def dim_v(ax, x, z0, z1, label, color=TXT, fs=10.5, side="right"):
    ax.annotate("", xy=(x, z0), xytext=(x, z1),
                arrowprops=dict(arrowstyle="<->", color=color, lw=1.15))
    ax.text(x + (0.35 if side == "right" else -0.35), (z0 + z1) / 2, label,
            rotation=90, ha="left" if side == "right" else "right", va="center",
            fontsize=fs, color=color,
            bbox=dict(fc="white", ec="none", alpha=0.85, pad=1))

# 正视图标注
dim_h(ax1, 8.0, -R_TIP, R_TIP, "齿顶 Ø12")
dim_h(ax1, 6.6, -UPPER_OD / 2, UPPER_OD / 2, "上层圆环 Ø9", color="#2f4a63")
dim_v(ax1, 0, -BORE / 2, BORE / 2, "通孔 Ø5", side="right")
dim_h(ax1, -6.2, R_ROOT, R_ROOT + SHAFT_L, f"轴 Ø{SHAFT_D:g} × 长 11", color="#9a5a22")
ax1.text(1.5, -10.4, "轴与齿盘中心孔垂直 (径向), 位于厚度中面",
         ha="center", va="top", fontsize=9.5, color="#555")

ax1.set_title(f"正视图 (Front, 扇形齿 8 个 / {SPAN_DEG:.0f}°)", fontsize=13, color=TXT)
ax1.set_xlim(-9.5, 19.5)
ax1.set_ylim(-11.8, 10.2)
ax1.set_aspect("equal")
ax1.axis("off")
ax1.text(1.5, -7.4, "环带 (Ø9→Ø12) 1.5 = 光滑台肩 0.6 + 齿高 0.9",
         ha="center", va="top", fontsize=9.5, color="#555")
ax1.text(1.5, -8.9, f"齿根圆 Ø10.2 — 扇区外 {360 - SPAN_DEG:.0f}° 为光滑圆边",
         ha="center", va="top", fontsize=9.5, color="#555")

# ================= 剖面图 =================
def box(x0, z0, x1, z1, fc, z=2, alpha=1.0, ec=C_EDGE, lw=1.3):
    ax2.add_patch(Rectangle((x0, z0), x1 - x0, z1 - z0, fc=fc, ec=ec,
                            lw=lw, zorder=z, alpha=alpha))

# 底层齿轮层 0..2: 剖面 y=0 在齿侧落在齿槽, 另一侧是扇区外的光滑圆边 (同为齿根圆)
box(-R_ROOT, 0, -BORE / 2, GEAR_T, C_GEAR)
box(BORE / 2, 0, R_ROOT, GEAR_T, C_GEAR)
ax2.add_patch(Rectangle((-R_TIP, 0), R_TIP - R_ROOT, GEAR_T, fill=False,
                        ec=C_EDGE, lw=1.0, ls=(0, (4, 3)), zorder=2))
ax2.text(-(R_TIP + R_ROOT) / 2, -0.45, "齿顶虚线", ha="center", va="top",
         fontsize=8.5, color="#555")
# 上层圆环 2..4
box(-UPPER_OD / 2, GEAR_T, -BORE / 2, TOTAL, C_RING)
box(BORE / 2, GEAR_T, UPPER_OD / 2, TOTAL, C_RING)
# 轴 (中面伸出 11mm)
z_lo, z_hi = (FLUSH_CLEAR, TOTAL - FLUSH_CLEAR) if SHAFT_FLUSH else (AXIS_Z - SHAFT_D / 2, AXIS_Z + SHAFT_D / 2)
ax2.add_patch(Rectangle((R_ROOT, z_lo), SHAFT_L, z_hi - z_lo,
                        fc=C_SHAFT, ec=C_EDGE, lw=1.2, zorder=3))
ax2.add_patch(Rectangle((R_ROOT - 1.0, z_lo), 1.0, z_hi - z_lo,
                        fc=C_SHAFT, ec="none", zorder=1, alpha=0.35))
# 轴线
ax2.plot([0, 0], [-1.4, TOTAL + 1.4], ls="-.", color="#888", lw=0.9, zorder=0)
ax2.plot([R_ROOT, R_ROOT + SHAFT_L + 1.0], [AXIS_Z, AXIS_Z], ls=":",
         color="#555", lw=0.8, zorder=4)

# 左侧: 分层厚度
dim_v(ax2, -8.6, 0, TOTAL, "总厚 4", color=TXT, side="left")
dim_v(ax2, -7.2, 0, GEAR_T, "齿轮层 2", color=TXT, side="left")
dim_v(ax2, -5.8, GEAR_T, TOTAL, "圆环层 2", color="#2f4a63", side="left")
# 上方: 两级直径
dim_h(ax2, 6.6, -R_TIP, R_TIP, "底层齿轮 Ø12")
dim_h(ax2, 5.1, -UPPER_OD / 2, UPPER_OD / 2, "上层圆环 Ø9", color="#2f4a63")
# 下方: 通孔 / 轴长
dim_h(ax2, -1.9, -BORE / 2, BORE / 2, f"Ø{BORE:g}", va="top", dy=0.25)
dim_h(ax2, -1.9, R_ROOT, R_ROOT + SHAFT_L, "轴长 11", color="#9a5a22", va="top", dy=0.25)
# 轴端: 轴径
dim_v(ax2, R_ROOT + SHAFT_L + 1.0, z_lo, z_hi,
      f"Ø{SHAFT_D:g}" + (" (切平)" if SHAFT_FLUSH else ""), color="#9a5a22")
# 轴心高度引线
ax2.annotate("轴心高度 2 (待确认)", xy=(R_ROOT + 8.0, AXIS_Z), xytext=(R_ROOT + 2.0, 8.4),
             fontsize=10.5, color="#8a4b1e",
             arrowprops=dict(arrowstyle="->", color="#8a4b1e", lw=1.0,
                             connectionstyle="arc3,rad=-0.2"))

ax2.set_title("剖面图 (Section, 过轴心)", fontsize=13, color=TXT)
ax2.set_xlim(-10.0, 19.5)
ax2.set_ylim(-3.6, 10.0)
ax2.set_aspect("equal")
ax2.axis("off")

fig.suptitle(f"白昼流星 翅膀-背包连接轴 {TAG} — 两层结构 (单位: mm)", fontsize=14.5, color=TXT)
path = os.path.join(OUT, f"{TAG}_schematic.png")
fig.savefig(path, dpi=160, bbox_inches="tight", facecolor="white")
print("SCHEMATIC:", path)
