"""白昼流星 翅膀-背包连接轴 v4 (单位: mm)

用户确认的结构:
  - 圆环部分分两层 (总厚 4mm):
      底层: 齿轮盘, 厚 2mm; 大圆环外径 (含齿) Ø12
            环带 (Ø9 -> Ø12) = (12-9)/2 = 1.5mm = 光滑台肩 0.6 + 齿高 0.9 -> 齿根 Ø10.2
            **扇形齿: 仅 8 个齿**, 其余为光滑圆边(齿根圆), 不是整圈
            扇区中心与轴相反; 齿距按照片实测 20°/齿 (扇区 160°)
      上层: 内部圆环, 外径 Ø9, 高 2mm, 中心通孔 Ø5
  - 径向轴: Ø5 x 11, 从齿盘边缘伸出, 与中心孔垂直, 轴心在厚度中面

拟合实测结论 (2026-10, 实物打印验证):
  - Ø5 整圆轴 + Ø5 孔 = 可用 (本仓库 stl/ 就是这一版)
  - 轴上下切平 (SHAFT_FLUSH=1) 会松动, 不要用
  - 需要调松紧时只改 BORE_D / SHAFT_D, 保持轴为整圆

环境变量: OUT (输出目录) / TAG (文件名前缀) / STL_NAME / SPAN_DEG / BORE_D /
          SHAFT_D / SHAFT_FLUSH / FLUSH_CLEAR
"""
import bpy
import bmesh
import math
import os

OUT = os.environ.get("OUT", ".")   # 输出目录 (默认当前目录)
os.makedirs(OUT, exist_ok=True)

# ---------------- 参数 (mm) ----------------
TEETH_N = 8               # 扇形齿: 共 8 个齿
TEETH_SPAN_DEG = float(os.environ.get("SPAN_DEG", "160"))
TAG = os.environ.get("TAG", "model")          # 输出文件前缀
STL_NAME = os.environ.get("STL_NAME", "wing_backpack_shaft_1-12.stl")
TEETH_CENTER_DEG = 180.0  # 扇区中心方向 (+X 为轴方向, 180° = 与轴相反)
GEAR_TIP_OD = 12.0        # 底层大圆环外径 (含齿) = 齿顶圆
UPPER_OD = 9.0            # 上层小圆环外径
# 用户口径: 齿轮到小圆环的环带 = 大圆环 - 小圆环 = (12 - 9) / 2 = 1.5mm
RING_BAND = (GEAR_TIP_OD - UPPER_OD) / 2   # 1.5
FLANGE_BAND = 0.6                          # 环带里先留 0.6 光滑台肩
TOOTH_DEPTH = RING_BAND - FLANGE_BAND      # 0.9 -> 齿根圆 Ø10.2 (设为 0 则齿根=Ø9)
GEAR_T = 2.0              # 底层齿轮厚度
UPPER_T = 2.0             # 上层圆环高度 (总厚 4mm, 已确认)
UPPER_TAPER = 0.15        # 上层圆环侧面收分(上小下大)
BORE_D = float(os.environ.get("BORE_D", 5.0))
SHAFT_D = float(os.environ.get("SHAFT_D", 5.0))
SHAFT_L = 11.0            # 露出齿根圆外的长度
SHAFT_OVERLAP = 1.0
SHAFT_Z_MODE = 'MID'      # 'MID' = 整体厚度居中; 也可直接给数值(如 1.5)
BORE_CHAMFER = 0.4        # 前脸孔口小倒角
# 轴上下切平到与圆环齐平 (打印版用; 实物版保留整圆核对)
SHAFT_FLUSH = os.environ.get("SHAFT_FLUSH", "0") == "1"
FLUSH_CLEAR = float(os.environ.get("FLUSH_CLEAR", 0.1))   # 切平面再让出的间隙

# ---------------- 清空 ----------------
for o in list(bpy.data.objects):
    bpy.data.objects.remove(o, do_unlink=True)

sc = bpy.context.scene
sc.unit_settings.system = 'METRIC'
sc.unit_settings.scale_length = 0.001

TOTAL_T = GEAR_T + UPPER_T
SHAFT_Z = TOTAL_T / 2 if SHAFT_Z_MODE == 'MID' else float(SHAFT_Z_MODE)


def make_mat(name, rgba, metallic=0.0, rough=0.5):
    m = bpy.data.materials.new(name)
    nt = m.node_tree
    b = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
    if b:
        b.inputs['Base Color'].default_value = rgba
        b.inputs['Metallic'].default_value = metallic
        b.inputs['Roughness'].default_value = rough
    else:
        print("[warn] no Principled BSDF")
    return m


def select_only(o):
    bpy.ops.object.select_all(action='DESELECT')
    o.select_set(True)
    bpy.context.view_layer.objects.active = o


def bool_mod(target, tool, op):
    m = target.modifiers.new(op.lower(), 'BOOLEAN')
    m.operation = op
    m.object = tool
    m.solver = 'EXACT'
    select_only(target)
    bpy.ops.object.modifier_apply(modifier=m.name)
    bpy.data.objects.remove(tool, do_unlink=True)


def cyl(r, d, loc, name, rot=(0, 0, 0), verts=128):
    bpy.ops.mesh.primitive_cylinder_add(vertices=verts, radius=r, depth=d,
                                        location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return o


def box(sx, sy, sz, loc, name):
    bpy.ops.mesh.primitive_cube_add(size=1, location=loc)
    o = bpy.context.active_object
    o.name = name
    o.scale = (sx, sy, sz)
    bpy.ops.object.transform_apply(scale=True)
    return o


def cone(r1, r2, d, loc, name, rot=(0, 0, 0), verts=128):
    bpy.ops.mesh.primitive_cone_add(vertices=verts, radius1=r1, radius2=r2,
                                    depth=d, location=loc, rotation=rot)
    o = bpy.context.active_object
    o.name = name
    return o


# ---------------- 底层齿轮轮廓 (120° 扇形, 8 齿) ----------------
R_TIP = GEAR_TIP_OD / 2
R_ROOT = R_TIP - TOOTH_DEPTH
PITCH = math.radians(TEETH_SPAN_DEG) / TEETH_N   # 120° -> 15°/齿; 160° -> 20°/齿
HALF = PITCH / 2
W_TIP = 0.22 * HALF       # 齿顶平台半角 (小平台)
W_ROOT = 0.28 * HALF      # 齿根平台半角
SPAN = math.radians(TEETH_SPAN_DEG) / 2
NSEG = 1800               # 0.2° 采样

def gear_radius(th):
    """扇区外 = 齿根圆; 扇区内 = 圆角梯形齿 (小平台顶 + 余弦齿面)"""
    d = (th - math.radians(TEETH_CENTER_DEG) + math.pi) % (2 * math.pi) - math.pi
    if abs(d) > SPAN:
        return R_ROOT
    k = round(d / PITCH + (TEETH_N - 1) / 2)
    k = min(max(k, 0), TEETH_N - 1)
    u = abs(d - (k - (TEETH_N - 1) / 2) * PITCH)
    if u <= W_TIP:
        return R_TIP
    if u >= HALF - W_ROOT:
        return R_ROOT
    t = (u - W_TIP) / (HALF - W_ROOT - W_TIP)
    s = 0.5 * (1 - math.cos(math.pi * t))     # 两端圆滑, 中间接近直线
    return R_TIP + (R_ROOT - R_TIP) * s

pts = []
for i in range(NSEG):
    th = 2 * math.pi * i / NSEG
    r = gear_radius(th)
    pts.append((r * math.cos(th), r * math.sin(th)))

bm = bmesh.new()
bot = [bm.verts.new((x, y, 0.0)) for x, y in pts]
top = [bm.verts.new((x, y, GEAR_T)) for x, y in pts]
bm.faces.new(list(reversed(bot)))
bm.faces.new(top)
for i in range(NSEG):
    j = (i + 1) % NSEG
    bm.faces.new((bot[i], bot[j], top[j], top[i]))
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
me = bpy.data.meshes.new("GearLayer")
bm.to_mesh(me)
bm.free()
part = bpy.data.objects.new("GearLayer", me)
bpy.context.collection.objects.link(part)

# ---------------- 上层圆环 (略带上小下大) ----------------
upper = cone(UPPER_OD / 2, UPPER_OD / 2 - UPPER_TAPER, UPPER_T + 0.3,
             (0, 0, GEAR_T - 0.3 + (UPPER_T + 0.3) / 2), "UpperRing")
bool_mod(part, upper, 'UNION')

# ---------------- 径向轴 ----------------
shaft_x0 = R_ROOT - SHAFT_OVERLAP
shaft_x1 = R_ROOT + SHAFT_L
shaft = cyl(SHAFT_D / 2, shaft_x1 - shaft_x0,
            ((shaft_x0 + shaft_x1) / 2, 0, SHAFT_Z),
            "Shaft", rot=(0, math.pi / 2, 0))

# 根部不额外加过渡: 实测为均匀 Ø5 圆柱; 打印版再按需加补强圆角
# 轴上下切平到与圆环齐平: 先把轴自身切成扁圆, 再并进本体 (不切伤圆环)
if SHAFT_FLUSH:
    z_bot, z_top = FLUSH_CLEAR, TOTAL_T - FLUSH_CLEAR
    lim = box(2 * (SHAFT_L + 6), 2 * (SHAFT_D + 6), z_top - z_bot,
              ((shaft_x0 + shaft_x1) / 2, 0, (z_top + z_bot) / 2), "ShaftFlat")
    bool_mod(shaft, lim, 'INTERSECT')
    print(f"FLUSH: shaft trimmed to z {z_bot:.2f}..{z_top:.2f}")
bool_mod(part, shaft, 'UNION')

# ---------------- 中心通孔 ----------------
bore = cyl(BORE_D / 2, TOTAL_T + 2, (0, 0, TOTAL_T / 2), "Bore")
bool_mod(part, bore, 'DIFFERENCE')

if BORE_CHAMFER > 0:
    ch = cone(BORE_D / 2, BORE_D / 2 + 2 * BORE_CHAMFER, BORE_CHAMFER + 0.3,
              (0, 0, TOTAL_T - (BORE_CHAMFER + 0.3) / 2), "ChamferF")
    bool_mod(part, ch, 'DIFFERENCE')

# ---------------- 平滑 + 材质 ----------------
select_only(part)
try:
    bpy.ops.object.shade_smooth_by_angle(angle=math.radians(35))
except Exception as e:
    print("[warn] smooth:", e)

m = make_mat("Navy", (0.06, 0.075, 0.13, 1), 0.10, 0.55)
part.data.materials.clear()
part.data.materials.append(m)
for p in part.data.polygons:
    p.material_index = 0
print("MAT SLOTS:", [ms.material.name if ms.material else None for ms in part.material_slots])
print("ENGINE:", sc.render.engine)

# ---------------- 世界/灯光 ----------------
world = bpy.data.worlds.new("World")
sc.world = world
world.use_nodes = True
bg = next((n for n in world.node_tree.nodes if n.type == 'BACKGROUND'), None)
if bg:
    bg.inputs[0].default_value = (0.93, 0.93, 0.92, 1)
    bg.inputs[1].default_value = 0.55

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(52), 0, math.radians(40)))
key = bpy.context.active_object
key.data.energy = 2.2
key.data.angle = math.radians(12)

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(62), 0, math.radians(-150)))
fill = bpy.context.active_object
fill.data.energy = 0.8

bpy.ops.object.light_add(type='SUN', rotation=(math.radians(8), 0, math.radians(90)))
rim = bpy.context.active_object
rim.data.energy = 0.5


# ---------------- 相机/渲染 ----------------
def add_cam(name, loc, target, ortho=None, lens=60):
    bpy.ops.object.camera_add(location=loc)
    cam = bpy.context.active_object
    cam.name = name
    e = bpy.data.objects.new("T_" + name, None)
    bpy.context.collection.objects.link(e)
    e.location = target
    c = cam.constraints.new('TRACK_TO')
    c.target = e
    c.track_axis = 'TRACK_NEGATIVE_Z'
    c.up_axis = 'UP_Y'
    if ortho:
        cam.data.type = 'ORTHO'
        cam.data.ortho_scale = ortho
    else:
        cam.data.lens = lens
    return cam


def render(cam, path, rx=1000, ry=800):
    sc.camera = cam
    sc.render.resolution_x = rx
    sc.render.resolution_y = ry
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'PNG'
    sc.render.filepath = path
    bpy.ops.render.render(write_still=True)
    print("RENDER:", path)


# 3/4 视角: 轴一侧 (光滑圆边)
cam34 = add_cam("Cam34", (36, -56, 40), (5, 0, 2), lens=58)
render(cam34, f"{OUT}/{TAG}_threequarter.png", 1000, 800)

# 3/4 视角: 扇形齿一侧
cam34b = add_cam("Cam34b", (-34, -54, 40), (-2, 0, 2), lens=58)
render(cam34b, f"{OUT}/{TAG}_threequarter_teeth.png", 1000, 800)

cam_top = add_cam("CamTop", (4, 0, 70), (4, 0, 0), ortho=26)
render(cam_top, f"{OUT}/{TAG}_top.png", 900, 700)

cam_side = add_cam("CamSide", (5, -80, 2), (5, 0, 2), ortho=34)
render(cam_side, f"{OUT}/{TAG}_side.png", 1100, 600)

# ---------------- 检查 + 导出 ----------------
select_only(part)
bm2 = bmesh.new()
bm2.from_mesh(part.data)
nonman = sum(1 for e in bm2.edges if not e.is_manifold)
print("NON-MANIFOLD EDGES:", nonman)
bm2.free()

print("DIM:", tuple(round(v, 3) for v in part.dimensions), "mm")
print("VERTS:", len(part.data.vertices), "FACES:", len(part.data.polygons))
print(f"PARAMS: teeth={TEETH_N} gear_t={GEAR_T} upper_od={UPPER_OD} upper_t={UPPER_T} "
      f"total_t={TOTAL_T} shaft_z={SHAFT_Z} span={TEETH_SPAN_DEG} "
      f"pitch={math.degrees(PITCH):.1f}")
print(f"BAND: ring={RING_BAND:.2f} flange={FLANGE_BAND:.2f} "
      f"tooth={TOOTH_DEPTH:.2f} root_od={2 * R_ROOT:.2f}")
print(f"FIT: bore={BORE_D:.2f} shaft={SHAFT_D:.2f} flush={SHAFT_FLUSH} "
      f"clear={FLUSH_CLEAR:.2f}")

stl = f"{OUT}/{STL_NAME}"
try:
    bpy.ops.wm.stl_export(filepath=stl, export_selected_objects=True)
    print("STL:", stl)
except Exception as e:
    print("[warn] stl export:", e)

blend = f"{OUT}/{TAG}_connector.blend"
bpy.ops.wm.save_as_mainfile(filepath=blend)
print("BLEND:", blend)
print("DONE")
