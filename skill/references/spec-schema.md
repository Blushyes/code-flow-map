# FLOW_DATA spec 结构

`build_flow.py` 吃的 JSON。一份完整可改的实例见同目录 `example.json`。

## 目录
- [顶层](#顶层)
- [cluster](#cluster)
- [node](#node)
- [io item（输入/输出项）](#io-item输入输出项)
- [edge](#edge)
- [校验规则](#校验规则)

## 顶层
```jsonc
{
  "title": "下单流程",                // 必填，图标题 / 文件标题
  "summary": "一句话概述",            // 可选，显示在标题下
  "rankdir": "LR",                    // 可选，LR(左右,默认更像泳道) | TB(上下)
  "clusters": [ ...cluster ],         // 可选，逻辑分组（大框）
  "nodes":    [ ...node ],            // 必填
  "edges":    [ ...edge ]             // 必填，流程主干连线
}
```

## cluster
图里的大框（如「接入校验」）。节点通过 `node.cluster` 归属。
```jsonc
{ "id": "intake", "label": "接入 / 校验" }
```

## node
```jsonc
{
  "id": "order",                   // 必填，全局唯一
  "label": "订单记录",             // 必填，框内文字；\n 可换行
  "kind": "data",                  // 可选: start|end|process|decision|data|io
  "cluster": "fulfill",            // 可选，所属 cluster.id
  "note": "唯一事实源",            // 可选，框上方红色小标注
  "summary": "一句话说这步干嘛",   // 可选，面板顶部摘要
  "source": "src/domain/order.ts:45",  // 可选但强烈建议，file:line 溯源
  "inputs":  [ ...io item ],       // 可选
  "outputs": [ ...io item ]        // 可选
}
```

## io item（输入/输出项）
描述一个输入或输出。`from`/`to` 是数据流向的来源/去向节点 id（面板里可点跳转、
选中节点时对应的边会高亮）——这是本工具的灵魂，**尽量都填**。
```jsonc
{
  "name": "order",                 // 必填，I/O 名
  "type": "object",                // 可选，类型注记（string / object / file[] / 自定义都行）
  "format": "json",                // 可选: json(默认) | table | code | text | file
  "desc": "下游落库/通知全靠它",    // 可选，一句话
  "from": "card_pay",              // input 用：上游来源节点 id（可为数组）
  "to": "persist",                 // output 用：下游去向节点 id（可为数组）

  // —— 按 format 配下面之一 ——
  // format=json:
  "schema":  { "id": "str", "status": "str", "amount_cents": "int" },  // 字段→类型，渲染成结构树
  "example": { "id": "ord_8f3", "status": "paid", "amount_cents": 3998 }, // 真实示例值，渲染成结构树
  // format=table:
  "columns": [ { "name": "id", "type": "varchar(32)", "desc": "主键" } ], // 渲染成表格
  // format=code / text:
  "example": "interface Notification { to: string; channel: 'email' | 'sms' }", // 等宽展示（text 同字段）
  // format=file:
  "path": "var/receipts/ord_8f3.pdf"                              // 文件路径
}
```
`schema` 和 `example` 都填时面板会先显「结构」再显「示例」。`schema` 支持任意嵌套
（对象套对象、数组用 `["int"]` 或 `[{...}]` 表示元素结构）。

## edge
流程主干连线。节点间的控制/数据流。
```jsonc
{ "from": "order", "to": "persist", "label": "order", "kind": "main" }
```
`label` 标注边上流动的数据，选填但建议填——让数据脉络在图上直接可读。
`kind`（可选）：`main`（默认，主数据流，实线）| `error`（异常/错误/回退/降级路径，红色虚线）|
`secondary`（辅助/复用/日志等次要边，灰色虚线）。**异常和次要边查看器默认隐藏**（一个开关
随时调出），这样主流程是干净骨架，不被一堆跨级的错误边糊成一团——长管线尤其明显。
所以：**只把真正的主数据流留作默认实线，错误/回退/降级边标 `error`，辅助/复用边标 `secondary`**。
（即使没标 `kind`，label 里含 error/异常/fallback/降级/retry 的边也会被自动当异常边处理。）
`edges` 和 io 的 `from/to` 各管一摊：`edges` 画线，io 的 `from/to` 管面板导航与高亮。

## 校验规则
`build_flow.py` 会拒绝并报错：
- 重复的 node id
- `node.cluster` 指向不存在的 cluster
- io 的 `from`/`to` 指向不存在的 node
- `edge` 的 `from`/`to` 指向不存在的 node

## 重构对比（refactor compare）

旧↔新双图对比模式。两份 **物理隔离** 的 spec：`X.old.json`（原封不动的现状流程，就是上面
描述的普通 spec）和 `X.new.json`（新架构）。旧文件永不引用新，对应关系只挂在新节点上。

构建：
```bash
python3 scripts/build_flow.py --old X.old.json --new X.new.json X-compare.html
```

`X.new.json` 在普通 spec 基础上扩展：

```jsonc
{
  "title": "...", "rankdir": "LR",
  "clusters": [...], "edges": [...],
  "nodes": [{
    "id": "pay_gateway", "label": "支付网关", "kind": "process", "cluster": "intake",
    "summary": "...", "source": "...", "inputs": [...], "outputs": [...],
    // —— 对应关系（挂在新节点上，单向引用旧节点 id）——
    "maps_from": ["card_pay", "wallet_pay"],  // 这个新节点由哪些旧节点演变而来
    "change": "merged",        // kept|renamed|merged|split|new|moved
    "rationale": "为什么这么改"
    // 拆分: 多个新节点 maps_from 同一个旧 id; 合并: 一个新节点 maps_from 多个旧 id;
    // new: maps_from 省略/空，表示从零新增
  }],
  // —— 被删除的旧节点（可选）——
  "removed": [{ "old_id": "dispatch", "rationale": "分发判定被统一网关取代" }],
  // —— 迁移计划（可选，"认真设计"就在这）——
  "migration": {
    "strategy": "in-place",     // rewrite(从零重写) | in-place(原地改造)
    "summary": "整体迁移思路",
    "steps": ["第1步…", "第2步…"],
    "risks": ["风险点…"]
  }
}
```

额外校验：`maps_from` 里每个 id、`removed[].old_id` 都必须是 `X.old.json` 里真实存在的节点。

查看效果：选中任一侧节点 → 另一侧对应节点绿边高亮；右侧面板显示变更类型徽章 + 源自/去向
跨图跳转链接 + 重构理由；右上角「迁移计划」看策略/步骤/风险。
