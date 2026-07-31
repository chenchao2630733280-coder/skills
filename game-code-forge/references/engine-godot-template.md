# Godot 4 引擎模板

> 本文件从 game-code-forge SKILL.md 抽离,作为 Godot 4 引擎的完整模板(含工程配置)。生成 Godot 代码时按需读取。
> Godot 4 采用 .tscn 场景文件 + .gd 脚本的组合。AI 直接生成文本格式的 .tscn 和 .gd,无需 Godot 编辑器交互。

## 六、Godot 4 引擎模板

Godot 4 采用 .tscn 场景文件 + .gd 脚本的组合。AI 直接生成文本格式的 .tscn 和 .gd,无需 Godot 编辑器交互。

### 6.1 project.godot

```ini
config_version=5

[application]
config/name="{游戏名称}"
run/main_scene="res://scenes/Main.tscn"
config/features=PackedStringArray("4.3", "Forward Plus")

[display]
window/size/viewport_width=1280
window/size/viewport_height=720
window/stretch/mode="canvas_items"
window/stretch/aspect="keep"

[input]
move_left={"deadzone":0.5,"events":[Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":65,"key_label":0,"unicode":97,"location":0,"echo":false,"script":null)]}
move_right={"deadzone":0.5,"events":[Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":68,"key_label":0,"unicode":100,"location":0,"echo":false,"script":null)]}
move_up={"deadzone":0.5,"events":[Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":87,"key_label":0,"unicode":119,"location":0,"echo":false,"script":null)]}
move_down={"deadzone":0.5,"events":[Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":83,"key_label":0,"unicode":115,"location":0,"echo":false,"script":null)]}
jump={"deadzone":0.5,"events":[Object(InputEventKey,"resource_local_to_scene":false,"resource_name":"","device":-1,"window_id":0,"alt_pressed":false,"shift_pressed":false,"ctrl_pressed":false,"meta_pressed":false,"pressed":false,"keycode":0,"physical_keycode":32,"key_label":0,"unicode":32,"location":0,"echo":false,"script":null)]}
```

> **注意**:`config_version=5` 是 Godot 4.x 的格式。input 映射使用 `physical_keycode`(WASD + Space),按项目实际需求调整。

### 6.2 Main.tscn(主场景)

```ini
[gd_scene load_steps=2 format=3 uid="uid://main_scene"]

[ext_resource type="Script" path="res://scripts/main.gd" id="1_main"]

[node name="Main" type="Node2D"]
script = ExtResource("1_main")

[node name="Background" type="Sprite2D" parent="."]
centered = false

[node name="GameLayer" type="Node2D" parent="."]

[node name="UILayer" type="CanvasLayer" parent="."]
```

> **关键**:`format=3` 是 Godot 4 的 .tscn 格式。`uid` 可选但建议生成(AI 可用 `uid://` + 随机字符串)。节点树用缩进表示层级。

### 6.3 main.gd(主入口)

```gdscript
extends Node2D
class_name Main

## 主场景控制器:管理场景切换、全局状态、游戏流程

@onready var background: Sprite2D = $Background
@onready var game_layer: Node2D = $GameLayer
@onready var ui_layer: CanvasLayer = $UILayer

var current_scene: Node = null

func _ready() -> void:
    # 加载启动场景
    _change_scene("res://scenes/BootScene.tscn")

func _change_scene(scene_path: String) -> void:
    if current_scene != null:
        current_scene.queue_free()
    var scene_resource: PackedScene = load(scene_path)
    current_scene = scene_resource.instantiate()
    game_layer.add_child(current_scene)

func show_toast(msg: String, duration: float = 2.0) -> void:
    # 简易 Toast 实现
    var label: Label = Label.new()
    label.text = msg
    label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
    label.position = Vector2(get_viewport().get_visible_rect().size.x / 2 - 100, 20)
    ui_layer.add_child(label)
    await get_tree().create_timer(duration).timeout
    label.queue_free()
```

### 6.4 BootScene.gd(启动/加载场景)

```gdscript
extends Node2D
class_name BootScene

## 启动场景:资源预加载、初始化、跳转主游戏场景

@onready var progress_bar: ProgressBar = $UI/ProgressBar
@onready var label: Label = $UI/LoadingLabel

var target_scene: String = "res://scenes/GameScene.tscn"

func _ready() -> void:
    _load_resources()

func _load_resources() -> void:
    # 预加载关键资源
    var loader: ResourceLoader = ResourceLoader.load_threaded_get(target_scene)
    var status: int = ResourceLoader.load_threaded_get_status(target_scene)
    var progress: Array = []
    while status == ResourceLoader.THREAD_LOAD_IN_PROGRESS:
        status = ResourceLoader.load_threaded_get_status(target_scene, progress)
        progress_bar.value = progress[0] * 100.0
        label.text = "加载中... %d%%" % int(progress[0] * 100)
        await get_tree().process_frame
    if status == ResourceLoader.THREAD_LOAD_LOADED:
        get_tree().change_scene_to_file(target_scene)
    else:
        label.text = "加载失败,请重试"
```

### 6.5 Character.gd(角色控制 2D)

```gdscript
extends CharacterBody2D
class_name Character

## 2D 角色控制:移动、跳跃、动画状态机

@export var move_speed: float = 200.0
@export var jump_force: float = 400.0
@export var gravity: float = 980.0

@onready var sprite: AnimatedSprite2D = $AnimatedSprite2D

var states: Dictionary = {
    "idle": "idle",
    "run": "run",
    "jump": "jump",
    "fall": "fall"
}
var current_state: String = "idle"

func _physics_process(delta: float) -> void:
    # 重力
    if not is_on_floor():
        velocity.y += gravity * delta
    
    # 水平移动
    var input_x: float = Input.get_axis("move_left", "move_right")
    velocity.x = input_x * move_speed
    
    # 跳跃
    if Input.is_action_just_pressed("jump") and is_on_floor():
        velocity.y = -jump_force
    
    move_and_slide()
    _update_state(input_x)
    _update_animation()

func _update_state(input_x: float) -> void:
    if not is_on_floor():
        current_state = "jump" if velocity.y < 0 else "fall"
    elif abs(input_x) > 0.1:
        current_state = "run"
    else:
        current_state = "idle"

func _update_animation() -> void:
    if sprite.animation != states[current_state]:
        sprite.play(states[current_state])
    # 朝向翻转
    if velocity.x < 0:
        sprite.flip_h = true
    elif velocity.x > 0:
        sprite.flip_h = false
```

### 6.6 export_presets.cfg(导出预设)

```ini
[preset.0]
name="Windows Desktop"
platform="Windows Desktop"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="export/Game.exe"
script_encryption_key=""
encrypt_pck=false
encrypt_directory=false

[preset.0.options]
custom_template/debug=""
custom_template/release=""
debug/export_console_wrapper=1
binary_format/embed_pck=false
texture_format/s3tc=true
texture_format/etc=false
texture_format/etc2=false

[preset.1]
name="HTML5"
platform="Web"
runnable=true
dedicated_server=false
custom_features=""
export_filter="all_resources"
include_filter=""
exclude_filter=""
export_path="export/Web/index.html"
script_encryption_key=""
encrypt_pck=false
encrypt_directory=false

[preset.1.options]
custom_template/debug=""
custom_template/release=""
variant/extensions_support=false
html/export_icon=true
html/custom_html_shell=""
html/head_include=""
```

### 6.7 Godot 4 与 Web 引擎的关键差异

| 维度 | Web 引擎(Phaser/Pixi/Canvas) | Godot 4 |
|------|------------------------------|---------|
| 入口 | `index.html` + `src/main.ts` | `project.godot` + `scenes/Main.tscn` |
| 脚本语言 | TypeScript/JavaScript | GDScript 4.x(类 Python,静态类型) |
| 场景定义 | 代码动态创建 | `.tscn` 文本文件声明式定义 |
| 资源加载 | `load.atlas()` / `Assets.load()` | `load()` / `preload()` |
| 物理引擎 | Matter.js(Phaser) / 自实现 | 内置(2D: PhysicsServer2D;3D: PhysicsServer3D) |
| 导出 | `vite build` → `dist/` | `godot --headless --export-release` → `export/` |
| 类型检查 | `tsc --noEmit` | `godot --check-only --script` |
| 3D 支持 | 不支持 | 原生支持(3D 物理/光照/骨骼) |

---

## Godot 4 工程配置(Godot 引擎时生成)

Godot 工程不需要 package.json/tsconfig/vite,改为生成以下文件:
- `project.godot`:工程配置(引擎版本、窗口尺寸、input 映射、autoload)
- `export_presets.cfg`:导出预设(Windows/HTML5/Linux/macOS)
- `scenes/*.tscn`:场景文件(用文本格式生成,不依赖编辑器)
- `scripts/*.gd`:GDScript 4.x 脚本(静态类型,带 @export/@onready 注解)

**资源引用**:Godot 使用 `res://` 协议引用资源,将 `assets/` 目录复制或符号链接到 Godot 工程根目录,用 `load("res://assets/role/hero/idle_000.png")` 加载。
