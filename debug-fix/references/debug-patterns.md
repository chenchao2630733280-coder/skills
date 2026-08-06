# 常见 Bug 模式清单

调试时优先对照以下 8 类模式匹配根因。每类含:模式描述 / 典型表现 / 定位方法 / 修复策略 / 示例。

---

## 1. 空指针 / None 引用

**模式描述:** 解引用了 null / None / undefined 的对象或变量,导致运行时抛出异常。

**典型表现:**
- `NullPointerException`(Java)、`AttributeError: 'NoneType' object has no attribute ...`(Python)、`TypeError: Cannot read properties of null`(JS)
- 堆栈指向某一行取属性 / 调用方法的代码

**定位方法:**
- 从堆栈定位到具体行
- 反向追溯该变量来源:函数参数?API 返回?字典/列表取值?
- 重点检查:外部输入、API 响应、数据库查询结果、可选字段

**修复策略:**
- 上游加空值校验或默认值
- 下游加守卫语句(早返回 / 抛业务异常)
- 使用 Optional / 严格类型签名约束

**示例:**
```python
# Bug
def get_user_name(user):
    return user.name  # user 可能为 None

# Fix
def get_user_name(user):
    if user is None:
        return "anonymous"
    return user.name
```

---

## 2. 边界条件(off-by-one)

**模式描述:** 循环边界、切片、索引差一,导致漏处理首元素 / 越界访问 / 多处理一个元素。

**典型表现:**
- `IndexError: list index out of range`
- 数组越界、切片漏首尾、循环多/少执行一次
- 分页时第一页或最后一页数据异常

**定位方法:**
- 检查循环条件 `<` vs `<=`、`range` 起止
- 检查切片 `[a:b]` 是否覆盖预期范围
- 检查分页 `offset = (page-1)*size` 的 page 起点
- 边界用例:空集合、单元素、恰好满页

**修复策略:**
- 用语义明确的边界(左闭右开 / 半开区间)
- 加边界单测:空、1、N-1、N、N+1
- 优先用语言内置迭代器替代手写索引

**示例:**
```python
# Bug:漏掉最后一个元素
for i in range(0, len(arr) - 1):
    process(arr[i])

# Fix
for i in range(0, len(arr)):
    process(arr[i])
```

---

## 3. 并发竞争

**模式描述:** 多线程/协程/进程并发访问共享资源,因缺乏同步导致结果不确定或数据损坏。

**典型表现:**
- 复现概率低、结果时序相关
- 计数错乱、状态不一致、丢失更新
- 死锁、活锁

**定位方法:**
- 搜索共享可变状态:全局变量、静态字段、单例、共享缓存
- 检查临界区是否有锁 / 原子操作保护
- 检查锁的获取顺序是否一致(防死锁)
- 用 tool-monitor-ops 查 trace 看时序

**修复策略:**
- 加锁 / 互斥量 / 信号量保护临界区
- 用原子操作 / 无锁数据结构
- 缩小临界区、避免锁内 I/O
- 优先用不可变数据 / 消息传递替代共享状态

**示例:**
```python
# Bug:计数丢失更新
count = 0
def increment():
    global count
    count += 1  # 非原子

# Fix:加锁
import threading
lock = threading.Lock()
def increment():
    global count
    with lock:
        count += 1
```

---

## 4. 资源泄漏(未关闭)

**模式描述:** 文件、连接、锁、句柄等资源打开后未正确关闭,导致资源耗尽或锁未释放。

**典型表现:**
- "Too many open files"、连接池耗尽
- 内存缓慢增长(OOM)
- 锁一直被持有、后续请求阻塞

**定位方法:**
- 搜索 `open(`、`connect(`、`acquire(`、`lock(` 等资源获取点
- 检查是否在所有路径(含异常路径)都有对应 close / release
- 检查是否使用 `try/finally` 或上下文管理器
- 用 tool-monitor-ops 查资源指标趋势

**修复策略:**
- 使用 `with` 语句 / `try-with-resources` / `using` 等语言级资源管理
- 异常路径必须释放资源
- 对池化资源确认归还逻辑

**示例:**
```python
# Bug:异常时文件未关闭
f = open("data.txt")
data = f.read()  # 若抛异常,f 永不关闭
f.close()

# Fix:with 自动关闭
with open("data.txt") as f:
    data = f.read()
```

---

## 5. 类型不匹配

**模式描述:** 传入了与函数/方法签名不符的类型,或隐式类型转换产生非预期结果。

**典型表现:**
- `TypeError`、`ClassCastException`、`AttributeError`
- 字符串当数字用、None 当对象用
- 隐式转换:`"1" + 1`、`0 == ""`、浮点比较失真

**定位方法:**
- 从错误信息看期望类型 vs 实际类型
- 检查数据来源:JSON 反序列化、表单输入、DB 字段
- 检查动态类型语言中变量在分支后类型是否一致
- 加类型注解 + 静态检查(mypy / ts / pyright)

**修复策略:**
- 在边界做显式类型转换 + 校验
- 加类型注解并启用静态检查
- 拒绝隐式转换,用严格相等 `===`

**示例:**
```python
# Bug:JSON 返回的数字是字符串
def total(prices):
    return sum(prices)  # ["10","20"] → TypeError 或字符串拼接

# Fix
def total(prices):
    return sum(float(p) for p in prices)
```

---

## 6. 异步时序

**模式描述:** 异步/延迟操作未按预期顺序执行,导致用了尚未就绪的数据或状态。

**典型表现:**
- "数据还没到就用了"
- Promise/Future 未 await、回调顺序错乱
- 状态机在异步回调中读取已被改写的状态

**定位方法:**
- 搜索 `async`、`await`、`then`、`setTimeout`、`Promise`
- 检查是否有未 await 的异步调用(fire-and-forget)
- 检查回调是否依赖尚未完成的上一步
- 用 tool-monitor-ops 查异步 trace 时序

**修复策略:**
- 显式 await / 串行化依赖链
- 用 async/await 替代嵌套回调
- 对依赖状态加就绪检查 / 完成事件
- 避免在异步回调中读取可变共享状态

**示例:**
```javascript
// Bug:未 await,用了未就绪的 result
async function load() {
    fetchData();           // 未 await
    console.log(result);   // result 还没赋值
}

// Fix
async function load() {
    await fetchData();
    console.log(result);
}
```

---

## 7. 配置缺失

**模式描述:** 依赖的环境变量、配置项、密钥、特性开关缺失或值非法,导致启动失败或行为异常。

**典型表现:**
- `KeyError`、`EnvironmentError`、`ConfigError`
- 启动时报缺配置、运行时某功能失效
- 本地正常、部署后异常(环境差异)

**定位方法:**
- 搜索配置读取点:`os.getenv`、`config.get`、`process.env`
- 对照配置清单确认必填项是否齐全
- 检查默认值 / 校验逻辑是否存在
- 对比本地与目标环境的配置差异

**修复策略:**
- 启动时校验所有必填配置,缺失时快速失败并给出明确提示
- 为可选配置提供合理默认值
- 用 .env.example / config schema 文档化所需配置

**示例:**
```python
# Bug:缺配置时静默使用 None 导致后续崩溃
db_host = os.getenv("DB_HOST")
conn = connect(db_host)  # None → 连接失败

# Fix:启动时校验
db_host = os.getenv("DB_HOST")
if not db_host:
    raise RuntimeError("缺少必填配置 DB_HOST")
conn = connect(db_host)
```

---

## 8. 依赖版本冲突

**模式描述:** 引入的依赖版本与已有依赖或运行环境不兼容,导致方法缺失、行为变化或加载失败。

**典型表现:**
- `ImportError`、`MethodNotFoundError`、`ClassNotFoundException`
- 升级依赖后功能异常、API 签名变化
- 多个传递依赖要求同一库的不同大版本

**定位方法:**
- 检查 lock 文件(package-lock.json / poetry.lock / requirements.txt)
- 对比变更前后依赖版本
- 查依赖 changelog / breaking changes
- 用 `pip show` / `npm ls` 看实际解析版本

**修复策略:**
- 锁定兼容版本范围(semver)
- 升级后跑全量回归测试
- 传递冲突用版本对齐或依赖隔离(虚拟环境 / overrides)
- 必要时回退到上一个已知可用版本

**示例:**
```python
# Bug:lib v2 移除了 v1 的方法
from lib import old_method  # ImportError

# Fix:适配 v2 API 或锁版本
# requirements.txt: lib>=1.0,<2.0
from lib import new_method
```
