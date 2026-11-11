# 起步骨架（四件套 + 一条 UI 约定）

> 目的：让每次生成的工程**骨架一致**。现在每个项目都从零搭，同一件事每次写法不同，
> 于是同一个 bug 每次都要重新踩一遍。
> 用法：**复制 → 只改三处（事件名表 / 存档 schema / 皮肤常量）→ 不重写**。

---

## 0. 为什么是"模板文件"而不是"生成器脚本"

| 方案 | 问题 |
|---|---|
| 生成器脚本 | 要覆盖 Phaser / Pixi / Canvas / Godot / Unity 五套引擎，绑定爆炸，且脚本本身没有人 review |
| 模板文件（本文） | 只固化**引擎无关**的四件抽象；引擎适配交给各自的 `engine-*-template.md` |

判断标准：**这段代码里有没有出现引擎 API**。没有 → 进本文；有 → 进对应引擎模板。

---

## 1. `utils/event-bus.ts`

逻辑层与表现层的唯一耦合点。**只转发，不做判断。**

```ts
type Handler<T> = (payload: T) => void;

export class EventBus<E extends Record<string, unknown>> {
  private map = new Map<keyof E, Set<Handler<never>>>();

  on<K extends keyof E>(type: K, fn: Handler<E[K]>): () => void {
    let set = this.map.get(type);
    if (!set) { set = new Set(); this.map.set(type, set); }
    set.add(fn as Handler<never>);
    return () => this.off(type, fn);
  }

  once<K extends keyof E>(type: K, fn: Handler<E[K]>): void {
    const off = this.on(type, (p) => { off(); fn(p); });
  }

  off<K extends keyof E>(type: K, fn: Handler<E[K]>): void {
    this.map.get(type)?.delete(fn as Handler<never>);
  }

  emit<K extends keyof E>(type: K, payload: E[K]): void {
    // 复制一份再遍历：允许订阅方在回调里 off，不会漏发/重发
    const set = this.map.get(type);
    if (!set) return;
    for (const fn of [...set]) (fn as Handler<E[K]>)(payload);
  }

  clear(): void { this.map.clear(); }
}
```

**必须改**：事件名联合类型（`E`）。
**禁止**：在 `emit` 里做业务判断、在回调里改权威状态（改状态必须走事务，事件只是通知）、把 `emit` 写成 `async`（同步派发；需要异步由订阅方自己排队）。

---

## 2. `utils/save-store.ts`

**只做读写与迁移，不做业务校验。**

```ts
export interface StoragePort {
  get(key: string): string | null;
  set(key: string, value: string): void;
  remove(key: string): void;
}

export interface SaveData { version: number; [k: string]: unknown }

type Migration = (d: Record<string, unknown>) => Record<string, unknown>;

export class SaveStore {
  private timer: ReturnType<typeof setTimeout> | null = null;

  constructor(
    private port: StoragePort,
    private migrations: Record<number, Migration>, // 从 n 升到 n+1
    private current = 1,
    private key = 'save',
  ) {}

  load(): SaveData {
    const raw = this.port.get(this.key);
    if (!raw) return { version: this.current };
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(raw);
    } catch {
      console.warn('[save] 存档损坏，回退默认值');
      return { version: this.current };
    }
    let v = Number(data.version) || 1;
    while (v < this.current) {
      const m = this.migrations[v];
      if (!m) { console.warn(`[save] 缺 v${v}→v${v + 1} 迁移，回退默认值`); return { version: this.current }; }
      data = m(data);
      v += 1;
      data.version = v;
    }
    return data as SaveData;
  }

  /** 防抖写盘：一次操作里多次 save 只落一次 */
  save(data: SaveData): void {
    if (this.timer) clearTimeout(this.timer);
    this.timer = setTimeout(() => {
      this.timer = null;
      this.port.set(this.key, JSON.stringify(data));
    }, 120);
  }

  flush(data: SaveData): void {
    if (this.timer) { clearTimeout(this.timer); this.timer = null; }
    this.port.set(this.key, JSON.stringify(data));
  }

  reset(): void { this.port.remove(this.key); }
}
```

**必须改**：`SaveData` 字段、`migrations` 表。
**禁止**：在 `load` 里抛异常（回退默认值 + 打日志）；在存档里存"可重算的派生值"（等级、总分这类能算出来的不要存，存了就一定会不一致）。

---

## 3. `managers/audio-manager.ts`

参数表来自 `AUDIO_SPEC.md §2.6`，**逐行照抄，不重新设计音色**。

```ts
interface SfxParam { osc: OscillatorType; freq: number; attack: number; release: number; gain: number }

const SFX_TABLE: Record<string, SfxParam> = {
  'sfx-click': { osc: 'sine', freq: 880, attack: 0.012, release: 0.09, gain: 0.28 },
  // ... 与 AUDIO_SPEC §2.6 一一对应
};

export class AudioManager {
  private ctx: AudioContext | null = null;
  private master: GainNode | null = null;
  private enabled = true;
  private playing = new Map<string, number>();

  /** 首次用户手势时调用（移动端策略要求） */
  unlock(): void {
    if (this.ctx) return;
    try {
      this.ctx = new AudioContext();
      this.master = this.ctx.createGain();
      this.master.gain.value = 0.7;          // 总输出上限，见 §2.7
      this.master.connect(this.ctx.destination);
      if (this.ctx.state === 'suspended') void this.ctx.resume();
    } catch (e) {
      this.enabled = false;                   // 静默降级，不抛错
      console.warn('[audio] 初始化失败，已静音', e);
    }
  }

  play(id: string, pitchStep = 0): void {
    const p = SFX_TABLE[id];
    const ctx = this.ctx;
    if (!this.enabled || !ctx || !p || !this.master) return;
    const freq = p.freq * Math.pow(1.2, Math.min(pitchStep, 6));  // 连击变调
    const now = ctx.currentTime;
    const osc = ctx.createOscillator();
    const env = ctx.createGain();
    osc.type = p.osc;
    osc.frequency.value = freq;
    env.gain.setValueAtTime(0, now);
    env.gain.linearRampToValueAtTime(p.gain, now + p.attack);
    env.gain.exponentialRampToValueAtTime(0.001, now + p.attack + p.release);
    osc.connect(env).connect(this.master);
    osc.start(now);
    osc.stop(now + p.attack + p.release + 0.02);
  }

  setMuted(muted: boolean): void {
    if (this.master) this.master.gain.value = muted ? 0 : 0.7;   // 不销毁节点
  }

  suspend(): void { void this.ctx?.suspend(); }
  resume(): void { if (this.enabled) void this.ctx?.resume(); }
}
```

**必须改**：`SFX_TABLE`。
**禁止**：`new AudioContext()` 放在模块顶层（未手势时会被浏览器挂起且报警告）；用 `gain = 0` 之外的方式"静音"（销毁节点后恢复会有爆音）。

---

## 4. `managers/tutorial-director.ts`

引导是**状态机**，不是一段弹窗文案。

```ts
export interface TutorialStep {
  id: string;
  /** 进入条件：不满足就跳过这一步（而不是卡住） */
  canEnter(ctx: unknown): boolean;
  onEnter(ctx: unknown): void;
  /** 完成条件：由业务在合适时机置位 */
  doneWhen(ctx: unknown): boolean;
  skippable?: boolean;
}

export class TutorialDirector {
  private i = 0;
  private skipped = false;
  private gated = false;

  constructor(
    private steps: TutorialStep[],
    private ctx: () => unknown,
    private onDone?: () => void,
  ) {}

  /** 引导期间输入是否应被门控吞掉——这个结论必须能被外部查询（验证脚本要用） */
  isGating(): boolean { return this.gated && !this.skipped; }

  start(): void {
    this.gated = true;
    this.i = 0;
    this.advance();
  }

  advance(): void {
    while (this.i < this.steps.length && !this.steps[this.i].canEnter(this.ctx())) this.i += 1;
    if (this.i >= this.steps.length) return this.finish();
    this.steps[this.i].onEnter(this.ctx());
  }

  tick(): void {
    if (this.skipped || this.i >= this.steps.length) return;
    if (this.steps[this.i].doneWhen(this.ctx())) { this.i += 1; this.advance(); }
  }

  /** 测试旁路：没有它，引导关的自动化验证会静默假绿 */
  skipTutorial(): void { this.skipped = true; this.gated = false; this.onDone?.(); }

  /** 调试旁路：直接跳到某一步 */
  forceStep(id: string): void {
    const idx = this.steps.findIndex((s) => s.id === id);
    if (idx < 0) return;
    this.i = idx;
    this.advance();
  }

  private finish(): void { this.gated = false; this.onDone?.(); }
}
```

**必须改**：`steps` 表。
**禁止**：把 `skipTutorial` 写成"下次进入才生效"；在引导里直接改业务状态（引导只发指令，状态由业务自己改）。

---

## 5. UI 三件套：只给约定，不给代码

UI 与引擎强绑定（Phaser 容器 / Unity Canvas / Godot Control），**代码抄不动**。能固化的是结构：

| 件 | 职责 | 反模式 |
|---|---|---|
| `BasePopup` | 打开/关闭/遮罩/焦点/暂停底层输入 | 每个弹窗自己写遮罩 → 叠两层后点穿 |
| `HUD` | 订阅事件刷新数值，**不持有业务状态** | HUD 里存分数并回写 → 与逻辑层双写 |
| `Theme` | 颜色/字号/圆角/间距常量 | 每个文件里出现 `#ff0000` 字面量 |

`Theme` 是三者里最便宜的收益：**所有视觉常量集中一处**，换皮只改一个文件。

---

## 6. 移植规则（改什么 / 不许改什么）

| 文件 | 必须改 | 不许改 | 为什么 |
|---|---|---|---|
| `event-bus.ts` | 事件名联合类型 | 派发语义（同步、复制后遍历） | 改成异步或直接遍历会引入"回调里 off 导致漏发" |
| `save-store.ts` | `SaveData`、`migrations` | 损坏时回退默认值的行为 | 抛异常会让老存档用户直接进不去游戏 |
| `audio-manager.ts` | `SFX_TABLE` | `unlock()` 的时机与降级 | 未手势初始化会被浏览器挂起，降级失败要静音而不是崩 |
| `tutorial-director.ts` | `steps` | `skipTutorial` / `isGating` 的存在 | 没有它们，引导关的自动化验证全是假绿 |

---

## 7. 验收（5 条）

- [ ] `eventBus.emit` 时，某订阅方在回调里 `off` 自己，其余订阅方仍收到（复制后遍历）
- [ ] 用一个 v1 存档（缺新字段）启动，能正常进入且字段被迁移
- [ ] 把存档内容改成非法 JSON，启动不崩、回到默认值并打一条日志
- [ ] 未手势前不创建 `AudioContext`；手势后能出声；`setMuted(true)` 后无声且不报错
- [ ] 引导关的验证脚本里调用 `skipTutorial()` 后，点击能正常生效（`isGating() === false`）
