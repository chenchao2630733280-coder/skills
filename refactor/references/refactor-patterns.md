# 重构模式清单 (refactor-patterns)

本文件是 `refactor` skill 的模式参考。每种模式给出:**适用场景 / 操作步骤 / 示例 / 注意事项**。

约定:所有示例仅示意,语言无关(以类 C/JS 风格表达)。

---

## 1. 提取方法 (Extract Method)

**适用场景**
- 一个方法过长,内含多个意图不同的片段。
- 一段代码需要注释才能理解其意图。
- 同一段逻辑在多处重复出现。

**操作步骤**
1. 找出意图独立的代码片段。
2. 为片段起一个"做什么"的名字(动词短语)。
3. 创建新方法,把片段移入;注意其使用的局部变量,作为参数传入或作为返回值传出。
4. 原位置替换为新方法调用。
5. 跑测试;绿了再进下一处。

**示例**
```js
// 前
function printOwing(invoice) {
  let outstanding = 0;
  console.log("***********************");
  console.log("**** Customer Owes ****");
  console.log("***********************");
  for (const o of invoice.orders) outstanding += o.amount;
  console.log(`name: ${invoice.customer}`);
  console.log(`amount: ${outstanding}`);
}

// 后
function printOwing(invoice) {
  printBanner();
  const outstanding = calculateOutstanding(invoice);
  printDetails(invoice, outstanding);
}
```

**注意事项**
- 别过早提取:片段确有独立意图再拆。
- 变量流向复杂时,先以临时变量理清,再决定参数/返回。
- 提取后若方法名不能清晰表达意图,改名而非加注释。

---

## 2. 内联方法 (Inline Method)

**适用场景**
- 方法体与其名字同样清晰(甚至更清晰)。
- 方法只被调用一次,且无复用价值。
- 间接层已无收益,反而增加跳转。

**操作步骤**
1. 确认方法未被多态覆写/非接口实现。
2. 找到所有调用点。
3. 用方法体替换每个调用点。
4. 删除方法定义。
5. 跑测试。

**示例**
```js
// 前
function getRating(driver) {
  return moreThanFiveLateDeliveries(driver) ? 2 : 1;
}
function moreThanFiveLateDeliveries(driver) {
  return driver.numberOfLateDeliveries > 5;
}

// 后
function getRating(driver) {
  return driver.numberOfLateDeliveries > 5 ? 2 : 1;
}
```

**注意事项**
- 多态方法不可内联(会破坏分发)。
- 若方法被递归调用、或在测试中作为 stub,不可内联。
- 内联后若可读性下降,说明该方法是必要的,撤销。

---

## 3. 移动方法 (Move Method)

**适用场景**
- 一个方法更多使用另一个类的特性而非自身类的特性。
- 调用方总是先拿到目标类再调本方法(特征依恋)。
- 为降低跨类耦合、平衡类职责。

**操作步骤**
1. 在目标类新建同名方法,复制逻辑,调整字段访问(通过参数或源类引用)。
2. 让源方法成为委托(调用目标方法),先跑测试。
3. 逐个更新调用点指向目标方法。
4. 调用点全部迁移后,删除源方法(或保留委托供过渡)。
5. 跑测试。

**示例**
```js
// 前:AccountType 上的方法大量使用 Account
class AccountType {
  overdraftCharge(account) { /* 用 account.daysOverdrawn 等 */ }
}

// 后:移到 Account
class Account {
  overdraftCharge() { /* 用 this.daysOverdrawn 等 */ }
}
```

**注意事项**
- 移动后注意访问可见性(私有字段需暴露或改友元)。
- 若方法同时依赖两端,考虑"移动并保留委托"而非硬切。
- 一次只移一个方法,避免大规模耦合同时变化。

---

## 4. 重命名 (Rename)

**适用场景**
- 名字无法准确表达意图(如 `d`、`data2`、`proc`)。
- 名字与实际行为不符(改了实现没改名)。
- 命名风格不一致(同一概念多种叫法)。

**操作步骤**
1. 确定新名字(领域语言优先)。
2. 用 IDE 的重命名重构(整符号)替换所有引用。
3. 检查字符串/反射/动态调用等隐藏引用。
4. 跑测试。
5. 检查公开 API 是否受影响(若受影响,停止重构,转升级流程)。

**示例**
```js
// 前
let d; // elapsed time in days
let a = b * c;

// 后
let elapsedTimeInDays;
let area = width * height;
```

**注意事项**
- 公开 API 改名属于破坏性变更,不在本 skill 范围。
- 重命名后旧注释若仍指向旧名,一并更新。
- 不要顺手改无关名字,一次一个符号。

---

## 5. 提取类 (Extract Class)

**适用场景**
- 一个类承担多个职责(God Class)。
- 类的字段可明显分成两组,各组独立变化。
- 子集化一个类总是一起使用。

**操作步骤**
1. 识别职责边界(哪些字段/方法属于新职责)。
2. 新建类,把相关字段与方法移入。
3. 原类持有新类实例(组合)。
4. 委托:原类需要的方法转发到新类。
5. 逐字段/方法迁移,每移一项跑一次测试。
6. 更新调用方(若需要直接用新类)。

**示例**
```js
// 前:Person 同时管姓名与电话号码格式
class Person {
  get officeAreaCode() { return this._officeAreaCode; }
  get officeNumber() { return this._officeNumber; }
  get telephoneNumber() { return `(${this._officeAreaCode}) ${this._officeNumber}`; }
}

// 后:提取 TelephoneNumber
class Person {
  constructor() { this._telephoneNumber = new TelephoneNumber(); }
  get telephoneNumber() { return this._telephoneNumber.telephoneNumber; }
}
class TelephoneNumber {
  get telephoneNumber() { return `(${this.areaCode}) ${this.number}`; }
}
```

**注意事项**
- 暴露内部类可能破坏封装,优先委托而非直接暴露。
- 迁移顺序:先字段后方法,保持每步可编译可测。
- 不要在提取类的同时改业务规则。

---

## 6. 内联类 (Inline Class)

**适用场景**
- 一个类经过多次重构后已无独立职责。
- 两个类职责高度重叠,合并更清晰。
- 临时提取的类已不再需要。

**操作步骤**
1. 在目标类(被合并入的类)中创建源类的字段与方法。
2. 把源类的引用替换为目标类直接调用。
3. 逐个迁移方法,每步跑测试。
4. 全部迁移后删除源类。

**示例**
```js
// 前
class Person { constructor() { this._telephoneNumber = new TelephoneNumber(); } get telephoneNumber() { return this._telephoneNumber.telephoneNumber; } }
class TelephoneNumber { get telephoneNumber() { return `(${this.areaCode}) ${this.number}`; } }

// 后:合并回 Person
class Person {
  get telephoneNumber() { return `(${this._areaCode}) ${this._number}`; }
}
```

**注意事项**
- 若源类被外部直接依赖,合并属破坏性变更,需走升级流程。
- 合并前确认没有其他类依赖其多态性。

---

## 7. 提取接口 (Extract Interface)

**适用场景**
- 多个类共享同一组方法,但无共同抽象。
- 调用方只依赖某子集行为,希望解耦具体类。
- 为测试引入 mock 替代点。

**操作步骤**
1. 识别调用方真正依赖的方法子集。
2. 定义接口,包含这些方法签名。
3. 让相关类实现该接口。
4. 调用方/参数类型改为接口类型。
5. 跑测试。

**示例**
```ts
// 前
class FileLogger { write(msg: string) { /*...*/ } flush() { /*...*/} }
class ConsoleLogger { write(msg: string) { /*...*/ } flush() { /*...*/} }
function persist(logger: FileLogger) { logger.write("done"); }

// 后
interface Logger { write(msg: string): void; }
function persist(logger: Logger) { logger.write("done"); }
```

**注意事项**
- 只提取真正被使用的方法,避免膨胀接口(接口隔离)。
- 不要为提取而提取:仅一个实现且无测试需求时,过早抽象反而增加成本。
- 接口命名应表达行为角色(如 `Logger`、`Readable`),而非实现。

---

## 8. 合并相似代码 (Consolidate Duplicate)

**适用场景**
- 多个方法/分支结构高度相似,仅个别参数不同。
- 复制粘贴产生的重复代码。
- 同一逻辑用多种写法实现。

**操作步骤**
1. 识别重复片段,列出差异点。
2. 把差异参数化为参数/配置/策略。
3. 提取统一实现(方法/基类/工具函数)。
4. 逐个替换原重复调用为统一实现。
5. 跑测试(用原有各分支用例覆盖)。

**示例**
```js
// 前
function tenPercentDiscount(price) { return price * 0.9; }
function twentyPercentDiscount(price) { return price * 0.8; }

// 后
function discount(price, rate) { return price * rate; }
// 调用:discount(price, 0.9) / discount(price, 0.8)
```

**注意事项**
- 强行合并差异过大的代码会催生分支地狱;差异 > 相似时不要合并。
- 合并后务必保留各原分支的测试用例,防止语义偏移。
- 注意副作用顺序:原代码各自可能有隐式依赖,合并时勿改变执行顺序。
