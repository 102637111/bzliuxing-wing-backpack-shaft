"""实物照片 vs 模型顶视 同比例对照 (齿顶 Ø12 定标, 按轴方向转正)"""
import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

import os

OUT = os.environ.get("OUT", ".")
PHOTO = os.environ.get("PHOTO", "images/photo_front.jpg")
RENDER = os.environ.get("RENDER", f"{OUT}/model_top.png")
# 裁切框, 用相对比例 (y0:y1, x0:x1), 与照片分辨率无关
_c = [float(v) for v in os.environ.get("CROP", "0.3554:0.6176,0.1569:0.5948")
      .replace(",", ":").split(":")]

PXMM = 26.0
W, H = 760, 600

# ---------- 照片 ----------
im = cv2.imread(PHOTO)
PH, PW = im.shape[:2]
crop = im[int(_c[0] * PH):int(_c[1] * PH), int(_c[2] * PW):int(_c[3] * PW)]
g = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
_, th = cv2.threshold(g, 80, 255, cv2.THRESH_BINARY_INV)
th = cv2.morphologyEx(th, cv2.MORPH_CLOSE, np.ones((7, 7), np.uint8))
cnts, hier = cv2.findContours(th, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_SIMPLE)
outer = max(cnts, key=cv2.contourArea)
holes = [c for c, h in zip(cnts, hier[0]) if h[3] != -1]
hole = max(holes, key=cv2.contourArea)
(cx, cy), _ = cv2.minEnclosingCircle(hole)

pts = outer.reshape(-1, 2).astype(np.float64)
d = np.hypot(pts[:, 0] - cx, pts[:, 1] - cy)
pts_ang = np.degrees(np.arctan2(pts[:, 1] - cy, pts[:, 0] - cx))

# 轴的指向: 超出齿顶圆 1.5 倍的那些轮廓点的角度中位数 (比"最远点"稳)
shaft_pts_ang = np.radians(pts_ang[d > 1.5 * np.median(d)])
ang = np.degrees(np.arctan2(np.mean(np.sin(shaft_pts_ang)),
                            np.mean(np.cos(shaft_pts_ang))))

sel = np.abs(((pts_ang - ang + 180) % 360) - 180) > 50
(ex, ey), (MA, ma), eang = cv2.fitEllipse(pts[sel].astype(np.float32).reshape(-1, 1, 2))
scale_photo = max(MA, ma) / 12.0
rot_deg = ang - 180.0   # 把轴转到图像左侧 (180°)
print(f"shaft angle {ang:.1f} deg, ellipse {MA:.1f}x{ma:.1f}, "
      f"scale {scale_photo:.1f} px/mm, rot {rot_deg:.1f}")
M = cv2.getRotationMatrix2D((cx, cy), rot_deg, 1.0)
pad = int(max(crop.shape[:2]) * 1.6)
M[0, 2] += (pad - crop.shape[1]) / 2
M[1, 2] += (pad - crop.shape[0]) / 2
rot = cv2.warpAffine(crop, M, (pad, pad), flags=cv2.INTER_CUBIC,
                     borderValue=(255, 255, 255))
mask = np.zeros(crop.shape[:2], np.uint8)
cv2.rectangle(mask, (0, 0), (crop.shape[1] - 1, crop.shape[0] - 1), 255, -1)
mask = cv2.warpAffine(mask, M, (pad, pad), flags=cv2.INTER_NEAREST)
rot[mask == 0] = 255
cx2, cy2 = cx + (pad - crop.shape[1]) / 2, cy + (pad - crop.shape[0]) / 2
photo_img = Image.fromarray(cv2.cvtColor(rot, cv2.COLOR_BGR2RGB))
k = PXMM / scale_photo
photo_img = photo_img.resize((int(photo_img.width * k), int(photo_img.height * k)),
                             Image.LANCZOS)
cx2, cy2 = cx2 * k, cy2 * k


def window(img, cx, cy):
    out = Image.new("RGB", (W, H), "white")
    out.paste(img, (int(W / 2 - cx), int(H / 2 - cy)))
    return out


p_win = window(photo_img, cx2, cy2)


def render_window(path):
    img = Image.open(path).convert("RGB").transpose(Image.FLIP_LEFT_RIGHT)
    kr = PXMM / (900 / 26)
    img = img.resize((int(img.width * kr), int(img.height * kr)), Image.LANCZOS)
    # 相机看向 (4,0,0): 齿盘中心镜像后偏右 4mm
    return window(img, img.width / 2 + 4.0 * PXMM, img.height / 2)


panels = [
    (p_win, "实物照片 (转正, 齿顶Ø12定标)", "#1f2a36"),
    (render_window(RENDER), "模型 · 8齿 / 20°齿距 / 160°扇区", "#2f4a63"),
]

FONT_B = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FONT_R = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
f_title = ImageFont.truetype(FONT_B, 26)
f_note = ImageFont.truetype(FONT_R, 18)

GAP = 18
canvas = Image.new("RGB", (W * len(panels) + GAP * (len(panels) - 1) + 32, H + 150), "white")
for i, (im_, label, color) in enumerate(panels):
    x = 16 + i * (W + GAP)
    canvas.paste(im_, (x, 96))
    d = ImageDraw.Draw(canvas)
    d.text((x + W // 2, 26), label, font=f_title, fill=color, anchor="mt")
    if i:
        d.line([(x - GAP // 2, 80), (x - GAP // 2, H + 90)], fill="#ddd", width=2)

d = ImageDraw.Draw(canvas)
d.text((16 + W // 2, H + 112),
       "实拍有透视; 齿距 18.5–24° (均值 20.7°), 首末齿中心 ~145°",
       font=f_note, fill="#666", anchor="mt")
d.text((16 + W + GAP + W // 2, H + 112),
       "8 齿 · 20°/齿 · 首末齿中心 140° · 扇区外光滑圆边",
       font=f_note, fill="#666", anchor="mt")

path = os.environ.get("OUTP", f"{OUT}/photo_vs_model.png")
canvas.save(path, quality=95)
print("COMPARE:", path, canvas.size)
