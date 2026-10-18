# PR #16 拆分与贡献者署名方案

> 维护目标：吸收 Sanity-Cloud / @insane66613 的工作，**以对方 commit / PR 合作为主**，
> 不做「整包自改 + 一句感谢」。

## 原则

1. **拆小 PR**：一次一个主题，可审、可测、可回滚。
2. **保留 Author**：用 `cherry-pick` 保留原作者（`Math Shamenson` / `insane66613`），禁止把对方 diff 重写成维护者独作 commit。
3. **用 GitHub Merge**：每个小 PR 走 Merge 按钮，留下 Merged 记录与贡献统计。
4. **维护者只跟安全/冲突修复**：跟进 commit 写清 `fix after contrib:`，必要时加 `Co-authored-by`。
5. **邀请 Collaborator**：Settings → Collaborators → 邀请 `@insane66613`（仓库设置，需 owner 操作）。

## 拆分顺序（与原 #17–#22 对齐）

| 序号 | 分支 | 主题 | 原 PR | 风险 |
|-----:|------|------|-------|------|
| 01 | `contrib/pr16-01-maintenance` | migration 性能 + 小清理 | #17 | 低 |
| 02 | `contrib/pr16-02-stream-hardening` | stream safe parser | #18 | 中（影响 thinking） |
| 03 | `contrib/pr16-03-model-registry` | 模型表增量 | #19 | 中（与 main 冲突） |
| 04 | `contrib/pr16-04-attachments-core` | 附件核心包（**收紧默认**） | #20 | 高（安全） |
| 05 | `contrib/pr16-05-chat-history-ro` | 历史只读/sync | #21 子集 | 高 |
| 06 | `contrib/pr16-06-chat-history-write` | 删除/cleanup 等破坏性 API | #21 剩余 | 很高（强制 API_KEY） |
| 07 | `contrib/pr16-07-frontend-history` | 前端历史 UI | #22 | 中 |
| 08 | 可选 | MCP | 伞形内 | 高（最后） |

**不做**：直接 merge #16 伞形 PR；把对方代码整段粘贴成维护者 commit。

## 每个小 PR 的标题模板

```text
[contrib #16/@insane66613] <主题>

Landed from Sanity-Cloud split (originally PR #N).
Author commits preserved via cherry-pick.
```

## #16 本体

关闭或保留为目录 issue，评论指向本拆分表与后续小 PR 链接。
