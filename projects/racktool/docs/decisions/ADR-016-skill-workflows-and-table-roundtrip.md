# ADR-016: 对话执行、布局适配、绑定设备编辑和位置表回导

- Status: Accepted
- Date: 2026-10-15（北京时间）
- Extends: ADR-013 / ADR-014 / ADR-015

## Context

用户明确要求并行推进实际 Agent 对话闭环、陌生布局适配、已有设备高度调整、跨机房移动和
设备位置表回导。原入口需要自行查 ID，绑定写回不允许高度改变/跨 Sheet，导出的表不能回导。

## Decision

- Agent 负责自然语言理解，Core 接受严格 JSON 请求，不引入 LLM、自由提示词 Parser 或网络依赖。
  conversation query 提供机房/柜名/设备文字/U 定位、分页和空闲区间；有歧义则拒绝默认选择。
- preview 生成计划、摘要和 token，绑定规范请求、数据库字节修订与源 Hash；apply 必须显式
  --commit，验证计划完整性和当前状态后调用同一 Core 写入器。数据库旁的本地 HMAC 密钥、
  已消费标记和短期锁属于项目私有状态，更新技能时留存；它是误改保护，不隔离能读取本地密钥的人。
  working-copy/original-authorized 是调用者的授权声明，不能凭填字段创造覆盖原图的许可。
- 原 move 继续保留高度，新 sync edit 显式修改高度/文字/位置；允许跨机房 Sheet 移动并保留
  device_id，分别清理旧 Sheet 与写入目标 Sheet，按目标独立 U 轴映射。保留设备列数和 lane 偏移；
  目标过窄拒绝，不修改整柜行高列宽。不支持互相占用源区域的批量换位；整批冲突即拒绝。
- WritePlan 增加完整项目语义修订，提交再次检查源与项目，并重建预检；Excel 临时写入、样式/
  文字类型/合并/重扫身份核验、备份和 SQLite 失败回滚保持原链路。写入以原 OOXML 包为底，仅补丁计划 old/new 矩形中的单元格和合并范围，保留原 workbook.xml、
  未涉及的部件及 styles/workbook 扩展；样式前缀和索引核验后仅追加。命名样式基表原字节及计数保留，允许
  生成器省略其 apply 开关；cellXfs 的开关语义保护不放宽。合法无样式包补齐样式关系；
  Excel/WPS 空 fill 仅作等价 no-fill 的局部兼容修复，不重排索引。新编辑对不能保真的未知对象拒绝。
- layout inspect/propose/check 从只读快照输出逐 Sheet 候选、异常与纯布局 Profile；生成规则复用
  schema/YAML reload/match/apply dry-run，不复制 Parser、不 force 低置信结果。
  固定坐标描述每 Sheet 一个机柜，不同 Profile 的异构 Sheet 暂用独立 SQLite 项目。
  project import --expected-sha256 在快照及持久前后核对，避免检查后换源。
- 导出位置页以 scoped hidden definedNames 保存压缩/分块版本、项目修订和原行基线。
  保持 A:G 可见、H:I 隐藏 ID、A1 标题和单列 U 范围；不增加可见注释或业务 Sheet。
  原版面仅追加新位置页的局部名字，原 Sheet 部件和旧名字保留。
- 回导核对元数据与当前项目完整基线，允许改 B/C/D/E/F（设备、机柜、U 位、高度、机房），
  通过隐藏 device_id 保持身份，并以机房+柜名解析新目标。改高度时 E 列与范围须一致。
  公式、状态/隐藏 ID 变动、增删行、缺失/重复/未知 ID、歧义和过期导出拒绝。
  预览 token 绑定表文件 Hash/项目修订/全部变化；提交重新校验。绑定项目单次批量 Safe Sync；
  草稿一次校验最终状态并备份/原子发布，不逐行部分保存。元数据不是数字签名或鉴权机制。

## Validation / Limits

公开双机房反向 U 夹具、旧回归、真实私有副本、独立包 -S 与逐次 CLI 子进程分别验证。
新增未知布局的明确坐标、低置信停止、Hash 过期；跨房/改高的样式/合并/文本/身份/失败回滚；
位置表乱序、冲突/篡改/过期及原版面空 definedNames 节点均有回归。

尝试真实 Codex CLI 时，启动必须创建 /run/codex-environment/codex-home/installation_id，
受云端只读挂载阻塞（EROFS），尚未进入模型/技能加载。没有读取凭证或修改 HOME/CODEX_HOME。
脚本对话协议通过不计为实际 Agent 软件兼容通过；Mac Codex、WorkBuddy、TRAE 与 Excel/WPS
本机验收继续分别记录，不能由合成夹具或系统 CI 替代。
