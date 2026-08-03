# Unity 引擎模板

> 本文件从 game-code-forge SKILL.md 抽离,作为 Unity 引擎的完整模板(含工程配置)。生成 Unity 代码时按需读取。
> Unity 采用 C# 脚本(.cs)+ 工程配置(.csproj/.asmdef)+ Editor 构建脚本的组合。AI 直接生成 C# 源码与文本配置,.unity 场景文件由 Editor/SceneBuilder.cs 在 batchmode 中程序化构建,无需 Unity 编辑器交互。

## 七、Unity 引擎模板

Unity 采用 C# 脚本 + Editor 构建脚本的组合。AI 直接生成 `.cs` 源码与 `.csproj`/`.asmdef`/`manifest.json` 等文本配置,`.unity` 场景文件由 `Editor/SceneBuilder.cs` 在 batchmode 导入时程序化创建并保存,避免 AI 直接写 YAML 序列化的场景文件(易错且不可读)。

### 7.1 工程目录结构

```
{项目名}/
├── Assets/
│   ├── Scenes/                    # .unity 场景(由 SceneBuilder 生成)
│   │   ├── Main.unity
│   │   └── BootScene.unity
│   ├── Scripts/
│   │   ├── Runtime/               # 运行时脚本(MonoBehaviour)
│   │   │   ├── UnityMain.cs
│   │   │   ├── BootScene.cs
│   │   │   ├── CharacterController.cs
│   │   │   ├── GameManager.cs
│   │   │   └── {Module}.cs
│   │   └── {ProjectName}.asmdef   # 程序集定义
│   ├── Resources/                 # Resources.Load 加载的资源
│   │   └── (复用 game-asset-forge 产出的 assets/ 内容)
│   └── Settings/                  # ProjectSettings 引用
├── Packages/
│   └── manifest.json              # 包依赖
├── ProjectSettings/               # 工程设置
│   ├── ProjectSettings.asset
│   └── ProjectVersion.txt
├── {ProjectName}.sln              # 解决方案(可选)
├── {ProjectName}.csproj           # 工程文件
└── docs/                          # 已有文档
```

> **资源引用**:Unity 使用 `Resources.Load("role/hero/idle_000")`(无扩展名)或 `AssetReference`(Addressables)加载。将 `assets/` 目录复制或符号链接到 `Assets/Resources/`,保持子目录结构。

### 7.2 ProjectVersion.txt

```
m_EditorVersion: 2022.3 LTS
```

> **注意**:推荐 Unity 2022.3 LTS 或更新 LTS 版本。`ProjectVersion.txt` 是 Unity 识别工程版本的关键文件。

### 7.3 {ProjectName}.asmdef(程序集定义)

```json
{
    "name": "{ProjectName}",
    "rootNamespace": "{ProjectName}",
    "references": [],
    "includePlatforms": [],
    "excludePlatforms": [],
    "allowUnsafeCode": false,
    "overrideReferences": false,
    "precompiledReferences": [],
    "autoReferenced": true,
    "defineConstraints": [],
    "versionDefines": [],
    "noEngineReferences": false
}
```

> **关键**:`.asmdef` 把 `Assets/Scripts/Runtime/` 下所有 .cs 编译为一个程序集,避免与 Editor 脚本混编。Editor 脚本单独定义一个 `.asmdef` 并勾选 Editor 平台。

### 7.4 Packages/manifest.json(包依赖)

```json
{
    "dependencies": {
        "com.unity.2d.sprite": "1.0.0",
        "com.unity.2d.tilemap": "1.0.0",
        "com.unity.2d.animation": "9.0.0",
        "com.unity.inputsystem": "1.7.0",
        "com.unity.textmeshpro": "3.0.6",
        "com.unity.ugui": "2.0.0",
        "com.unity.modules.physics2d": "1.0.0"
    }
}
```

> 按项目实际裁剪:纯 3D 游戏移除 2d.* 包;无 TextMeshPro 需求移除 textmeshpro。inputsystem 为新版 Input System(推荐)。

### 7.5 UnityMain.cs(主入口)

```csharp
using UnityEngine;
using UnityEngine.SceneManagement;

namespace {ProjectName}
{
    /// <summary>
    /// 主入口:挂载在 Main 场景的根 GameObject 上,负责初始化与首场景加载
    /// </summary>
    public class UnityMain : MonoBehaviour
    {
        [SerializeField] private string bootScene = "BootScene";

        private static UnityMain _instance;
        public static UnityMain Instance => _instance;

        private void Awake()
        {
            if (_instance != null && _instance != this)
            {
                Destroy(gameObject);
                return;
            }
            _instance = this;
            DontDestroyOnLoad(gameObject);
            Application.targetFrameRate = 60;
            QualitySettings.vSyncCount = 0;
        }

        private void Start()
        {
            SceneManager.LoadScene(bootScene);
        }
    }
}
```

### 7.6 BootScene.cs(启动/加载场景)

```csharp
using System.Collections;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace {ProjectName}
{
    /// <summary>
    /// 启动场景:资源预加载、初始化、跳转主游戏场景
    /// </summary>
    public class BootScene : MonoBehaviour
    {
        [SerializeField] private Slider progressBar;
        [SerializeField] private Text loadingLabel;
        [SerializeField] private string targetScene = "GameScene";

        private void Start()
        {
            StartCoroutine(LoadResources());
        }

        private IEnumerator LoadResources()
        {
            var op = SceneManager.LoadSceneAsync(targetScene);
            op.allowSceneActivation = false;
            while (op.progress < 0.9f)
            {
                if (progressBar != null) progressBar.value = op.progress;
                if (loadingLabel != null) loadingLabel.text = $"加载中... {(int)(op.progress * 100)}%";
                yield return null;
            }
            if (progressBar != null) progressBar.value = 1f;
            if (loadingLabel != null) loadingLabel.text = "加载完成";
            yield return new WaitForSeconds(0.3f);
            op.allowSceneActivation = true;
        }
    }
}
```

### 7.7 CharacterController.cs(2D 角色控制)

```csharp
using UnityEngine;

namespace {ProjectName}
{
    /// <summary>
    /// 2D 角色控制:移动、跳跃、动画状态机(基于 Rigidbody2D + SpriteRenderer)
    /// </summary>
    [RequireComponent(typeof(Rigidbody2D))]
    [RequireComponent(typeof(Animator))]
    public class CharacterController : MonoBehaviour
    {
        [SerializeField] private float moveSpeed = 5f;
        [SerializeField] private float jumpForce = 12f;
        [SerializeField] private LayerMask groundLayer;
        [SerializeField] private Transform groundCheck;
        [SerializeField] private float groundCheckRadius = 0.2f;

        private enum State { Idle, Run, Jump, Fall }

        private Rigidbody2D _rb;
        private Animator _animator;
        private SpriteRenderer _sprite;
        private State _currentState = State.Idle;
        private bool _isGrounded;

        private static readonly int AnimState = Animator.StringToHash("state");

        private void Awake()
        {
            _rb = GetComponent<Rigidbody2D>();
            _animator = GetComponent<Animator>();
            _sprite = GetComponent<SpriteRenderer>();
        }

        private void Update()
        {
            _isGrounded = Physics2D.OverlapCircle(groundCheck.position, groundCheckRadius, groundLayer);
            float inputX = Input.GetAxisRaw("Horizontal");
            _rb.velocity = new Vector2(inputX * moveSpeed, _rb.velocity.y);

            if (Input.GetButtonDown("Jump") && _isGrounded)
            {
                _rb.velocity = new Vector2(_rb.velocity.x, jumpForce);
            }

            UpdateState(inputX);
            UpdateAnimation(inputX);
        }

        private void UpdateState(float inputX)
        {
            if (!_isGrounded)
                _currentState = _rb.velocity.y > 0 ? State.Jump : State.Fall;
            else if (Mathf.Abs(inputX) > 0.1f)
                _currentState = State.Run;
            else
                _currentState = State.Idle;
        }

        private void UpdateAnimation(float inputX)
        {
            _animator.SetInteger(AnimState, (int)_currentState);
            if (inputX < 0) _sprite.flipX = true;
            else if (inputX > 0) _sprite.flipX = false;
        }

        private void OnDrawGizmosSelected()
        {
            if (groundCheck != null)
                Gizmos.DrawWireSphere(groundCheck.position, groundCheckRadius);
        }
    }
}
```

### 7.8 GameManager.cs(全局状态)

```csharp
using UnityEngine;

namespace {ProjectName}
{
    /// <summary>
    /// 全局游戏管理:状态机、分数、生命周期
    /// </summary>
    public class GameManager : MonoBehaviour
    {
        public enum GameState { Idle, Guide, Countdown, Play, Paused, GameOver }

        public GameState State { get; private set; } = GameState.Idle;
        public int Score { get; private set; }

        public static GameManager Instance { get; private set; }

        private void Awake()
        {
            if (Instance != null && Instance != this) { Destroy(gameObject); return; }
            Instance = this;
            DontDestroyOnLoad(gameObject);
        }

        public void StartGame()
        {
            Score = 0;
            State = GameState.Play;
        }

        public void AddScore(int delta)
        {
            if (State != GameState.Play) return;
            Score += delta;
        }

        public void GameOver()
        {
            State = GameState.GameOver;
        }
    }
}
```

### 7.9 Editor/SceneBuilder.cs(场景程序化构建)

> **关键**:Unity 的 `.unity` 文件是 YAML 序列化格式,AI 不直接写。改用 Editor 脚本在 batchmode 首次导入时构建场景并保存到 `Assets/Scenes/`。

```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;
using UnityEngine.UI;

namespace {ProjectName}.Editor
{
    /// <summary>
    /// 编辑器脚本:程序化构建 Main.unity 与 BootScene.unity 并保存。
    /// 在 batchmode 导入工程后由 BuildScript 调用一次,后续构建无需再次执行。
    /// </summary>
    public static class SceneBuilder
    {
        private const string MainScenePath = "Assets/Scenes/Main.unity";
        private const string BootScenePath = "Assets/Scenes/BootScene.unity";

        [MenuItem("Tools/Build Scenes")]
        public static void BuildAll()
        {
            EnsureFolder("Assets/Scenes");
            BuildMainScene();
            BuildBootScene();
            EditorSceneManager.SaveScene(EditorSceneManager.GetActiveScene());
            AssetDatabase.SaveAssets();
            Debug.Log("SceneBuilder: 场景构建完成");
        }

        private static void EnsureFolder(string path)
        {
            if (!AssetDatabase.IsValidFolder(path))
                AssetDatabase.CreateFolder("Assets", "Scenes");
        }

        private static void BuildMainScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Main");
            var main = root.AddComponent<{ProjectName}.UnityMain>();

            var bg = new GameObject("Background");
            var sr = bg.AddComponent<SpriteRenderer>();
            bg.transform.SetParent(root.transform);

            var gameLayer = new GameObject("GameLayer");
            gameLayer.transform.SetParent(root.transform);

            var uiLayer = new GameObject("UILayer");
            var canvas = uiLayer.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            uiLayer.AddComponent<CanvasScaler>();
            uiLayer.AddComponent<GraphicRaycaster>();
            uiLayer.transform.SetParent(root.transform);

            EditorSceneManager.SaveScene(scene, MainScenePath);
        }

        private static void BuildBootScene()
        {
            var scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
            var root = new GameObject("Boot");
            var boot = root.AddComponent<{ProjectName}.BootScene>();

            var ui = new GameObject("UI");
            var canvas = ui.AddComponent<Canvas>();
            canvas.renderMode = RenderMode.ScreenSpaceOverlay;
            ui.transform.SetParent(root.transform);

            var sliderObj = new GameObject("ProgressBar");
            var slider = sliderObj.AddComponent<Slider>();
            sliderObj.transform.SetParent(ui.transform);
            var labelObj = new GameObject("LoadingLabel");
            var label = labelObj.AddComponent<Text>();
            labelObj.transform.SetParent(ui.transform);

            var bootSer = new SerializedObject(boot);
            bootSer.FindProperty("progressBar").objectReferenceValue = slider;
            bootSer.FindProperty("loadingLabel").objectReferenceValue = label;
            bootSer.ApplyModifiedProperties();

            EditorSceneManager.SaveScene(scene, BootScenePath);
        }
    }
}
#endif
```

### 7.10 Editor/BuildScript.cs(构建入口)

```csharp
#if UNITY_EDITOR
using UnityEditor;
using UnityEngine;

namespace {ProjectName}.Editor
{
    /// <summary>
    /// 构建入口:供 unity -batchmode -executeMethod 调用
    /// </summary>
    public static class BuildScript
    {
        public static void BuildWindows()
        {
            BuildPlayer(BuildTarget.StandaloneWindows64, "Build/Game.exe");
        }

        public static void BuildWebGL()
        {
            BuildPlayer(BuildTarget.WebGL, "Build/Web/index.html");
        }

        private static void BuildPlayer(BuildTarget target, string outputPath)
        {
            // 首次构建前确保场景已生成
            if (!System.IO.File.Exists("Assets/Scenes/Main.unity"))
            {
                SceneBuilder.BuildAll();
            }

            var scenes = new[]
            {
                new EditorBuildSettingsScene("Assets/Scenes/Main.unity", true),
                new EditorBuildSettingsScene("Assets/Scenes/BootScene.unity", true),
            };
            EditorBuildSettings.scenes = scenes;

            var options = new BuildPlayerOptions
            {
                scenes = new[]
                {
                    "Assets/Scenes/Main.unity",
                    "Assets/Scenes/BootScene.unity"
                },
                locationPathName = outputPath,
                target = target,
                options = BuildOptions.None
            };

            var report = BuildPipeline.BuildPlayer(options);
            var summary = report.summary;
            if (summary.result == UnityEditor.Build.Reporting.BuildResult.Succeeded)
                Debug.Log($"Build 成功: {outputPath}");
            else
                Debug.LogError($"Build 失败: result={summary.result}");
        }
    }
}
#endif
```

### 7.11 {ProjectName}.csproj(工程文件)

> Unity 通常在打开工程时自动生成 .csproj/.sln。AI 可生成一个最小占位 .csproj,或在 batchmode 首次运行时由 Unity 重新生成。下面是最小占位:

```xml
<?xml version="1.0" encoding="utf-8"?>
<Project ToolsVersion="4.0" DefaultTargets="Build" xmlns="http://schemas.microsoft.com/developer/msbuild/2003">
  <PropertyGroup>
    <Configuration Condition=" '$(Configuration)' == '' ">Debug</Configuration>
    <Platform Condition=" '$(Platform)' == '' ">AnyCPU</Platform>
    <ProductVersion>10.0.20506</ProductVersion>
    <SchemaVersion>2.0</SchemaVersion>
    <RootNamespace>{ProjectName}</RootNamespace>
    <ProjectGuid>{NEW-GUID-HERE}</ProjectGuid>
    <OutputType>Library</OutputType>
    <AppDesignerFolder>Properties</AppDesignerFolder>
    <AssemblyName>{ProjectName}</AssemblyName>
    <TargetFrameworkVersion>v4.7.1</TargetFrameworkVersion>
    <FileAlignment>512</FileAlignment>
  </PropertyGroup>
  <ItemGroup>
    <Compile Include="Assets/Scripts/Runtime/**/*.cs" />
    <Compile Include="Assets/Scripts/Editor/**/*.cs" />
  </ItemGroup>
  <Import Project="$(MSBuildToolsPath)\Microsoft.CSharp.targets" />
</Project>
```

> **注意**:`TargetFrameworkVersion` 按 Unity 版本调整(2022.3 LTS 默认 v4.7.1)。`ProjectGuid` 用任意有效 GUID。Unity 重新生成时会覆盖此文件。

### 7.12 Unity 与 Godot 4 / Web 引擎的关键差异

| 维度 | Web 引擎(Phaser/Pixi/Canvas) | Godot 4 | Unity |
|------|------------------------------|---------|-------|
| 入口 | `index.html` + `src/main.ts` | `project.godot` + `scenes/Main.tscn` | `Assets/Scenes/Main.unity` + `UnityMain.cs` |
| 脚本语言 | TypeScript/JavaScript | GDScript 4.x | C#(.cs) |
| 场景定义 | 代码动态创建 | `.tscn` 文本文件 | `.unity` YAML(由 Editor 脚本程序化生成,AI 不直接写) |
| 资源加载 | `load.atlas()` / `Assets.load()` | `load()` / `preload()` | `Resources.Load()` / Addressables |
| 物理引擎 | Matter.js(Phaser) / 自实现 | 内置(PhysicsServer2D/3D) | PhysX(3D) + Box2D(2D),内置 |
| 导出 | `vite build` → `dist/` | `godot --headless --export-release` → `export/` | `unity -batchmode -quit -executeMethod` → `Build/` |
| 类型检查 | `tsc --noEmit` | `godot --check-only --script` | `unity -batchmode -quit -executeMethod` 编译隐式检查(无独立 typecheck) |
| 工程识别 | `package.json` | `project.godot` | `ProjectSettings/ProjectVersion.txt` + `Assets/` 目录 |
| 3D 支持 | 不支持 | 原生支持 | 原生支持(PhysX + 光照 + 骨骼) |
| 生态成熟度 | Web 游戏 | 开源,2D/3D 均衡 | 工业级,3D/跨平台发布最强 |

### 7.13 Unity 生成注意事项

1. **不直接写 .unity 场景文件**:YAML 序列化格式复杂且 Unity 版本敏感,改用 `Editor/SceneBuilder.cs` 在 batchmode 首次导入时程序化构建并保存场景。
2. **程序集分离**:`Runtime/` 与 `Editor/` 各自定义 `.asmdef`,Editor 程序集勾选 Editor 平台,避免 Editor API 误入运行时构建。
3. **资源路径**:`Resources.Load("role/hero/idle_000")` 不带扩展名,且资源必须在 `Assets/Resources/` 下。Sprite 图集用 `SpriteAtlas`(在 Editor 脚本中创建)。
4. **Input System**:推荐新版 Input System 包(`com.unity.inputsystem`),代码用 `Input.GetAxisRaw`/`Input.GetButtonDown`(旧 Input Manager 兼容模式)或 `InputAction`。
5. **数值平衡**:与 Phaser/Godot 一致,`GameConfig` 类用 `const`/`static readonly` 集中管理,顶部带推导注释(见 `references/pitfall-balance-validation.md`)。
6. **构建依赖**:Unity 工程必须先在装有 Unity Editor 的机器上用 `unity -batchmode -quit -projectPath . -executeMethod {ProjectName}.Editor.BuildScript.BuildWindows` 构建,AI 不在沙箱内运行 Unity,构建由 game-integrate 调用宿主 Unity CLI。

---

## Unity 工程配置(Unity 引擎时生成)

Unity 工程不需要 package.json/tsconfig/vite,改为生成以下文件:
- `ProjectSettings/ProjectVersion.txt`:Unity 版本标识(2022.3 LTS)
- `Assets/Scripts/Runtime/{ProjectName}.asmdef`:运行时程序集定义
- `Assets/Scripts/Editor/{ProjectName}.Editor.asmdef`:Editor 程序集定义(Editor 平台)
- `Packages/manifest.json`:包依赖(2D/3D 按需裁剪)
- `Assets/Scripts/Runtime/*.cs`:运行时脚本(MonoBehaviour)
- `Assets/Scripts/Editor/SceneBuilder.cs`:场景程序化构建
- `Assets/Scripts/Editor/BuildScript.cs`:构建入口(供 -executeMethod 调用)
- `{ProjectName}.csproj`:最小占位(Unity 重新生成会覆盖)

**资源引用**:Unity 使用 `Resources.Load()` 加载,将 `assets/` 目录复制或符号链接到 `Assets/Resources/`,保持子目录结构,调用 `Resources.Load<Sprite>("role/hero/idle_000")`(无扩展名)。
