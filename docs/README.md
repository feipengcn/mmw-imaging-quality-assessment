# Documentation Map

这个目录用于放“会持续被人查看和维护”的项目文档，不放一次性的临时记录。

## 建议分层

- `README.md`
  仓库入口文档。说明项目是什么、怎么启动、怎么验证、当前提供什么能力。

- `AGENT.md`
  面向接手开发的人或代码代理。说明当前工程结构、运行方式、已知约束、最近落地状态。

- `DESIGN.md`
  视觉和交互基线。描述页面结构、设计原则、组件语义和当前已落地的 UI 方向。

- `docs/HANDOFF.md`
  交接文档。记录阶段性结论、未完成事项、风险和后续建议。

- `docs/superpowers/specs/`
  需求和设计规格文档。按日期和主题存档，适合保留“为什么要这么做”。

- `docs/superpowers/plans/`
  实施计划文档。描述开发步骤和批次安排，适合保留“准备怎么做”。

## 业内常见做法

比较常见的做法不是把所有内容都塞进一个大 `README`，而是按用途分层：

- 入口层：`README.md`
- 运行层：开发/部署/运维文档
- 设计层：设计说明、架构说明、API 约定
- 过程层：spec、plan、handoff、ADR

如果项目继续变大，通常还会再补两类文档：

- `docs/adr/`
  Architecture Decision Record。记录关键技术决策，比如为什么选 FastAPI、为什么采用流式导入进度。

- `docs/runbooks/`
  运行手册。记录服务启动、数据恢复、常见故障排查。

## 对这个仓库的建议

当前最小可维护体系建议保持为：

- `README.md`：用户入口
- `AGENT.md`：工程现状
- `DESIGN.md`：UI 基线
- `docs/HANDOFF.md`：阶段交接
- `docs/superpowers/specs/`：需求/设计方案
- `docs/superpowers/plans/`：执行计划

这样已经够用，而且边界清楚，不容易文档互相覆盖。
