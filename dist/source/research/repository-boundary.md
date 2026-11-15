# 新旧仓库内容边界与只读审查

检查日期：2026-11-13。新仓库候选：`AIPMAndy/chinese-international-student-ai-jobs`。已通过 GitHub 连接确认登录账户为 AIPMAndy；候选仓库 API 返回 404。此结果表示本连接未发现可访问的同名仓库，不将其写成绝对不存在的证明。

## 实际读取范围

| 既有仓库 | 已读目录/正文 | 已有重点 | 新项目怎样去重 |
| --- | --- | --- | --- |
| [how-to-get-offer](https://github.com/AIPMAndy/how-to-get-offer) | README、目录、guides/12-role-playbooks.md、examples/ops-to-ai.md | 通用定位、简历、渠道、面试、Offer与AI辅助求职 | 通用流程只作简短入口；新增跨地区技术JD、运行实验和技术追问 |
| [teach-rd-product-handbook](https://github.com/AIPMAndy/teach-rd-product-handbook) | README、docs/curriculum.md、目录 | 研发的用户价值、需求、产品决策与90天训练 | 不重写产品意识课程；聚焦技术岗位可核验证据 |
| [andy-product-skill](https://github.com/AIPMAndy/andy-product-skill) | 远端根目录、README.md、SKILL.md | 产品方法框架与决策路由 | AI产品经理转产品专题，本册不搬入产品框架 |
| [anthropic-claude-code-agent-handbook](https://github.com/AIPMAndy/anthropic-claude-code-agent-handbook) | README、目录、docs/02-agent-patterns.md、docs/05-evals-and-safety.md | Agent架构、工具操作、使用方法与评估原则 | 不重新做Agent工具教程；用独立输入、独立代码、可验收技术项目服务申请 |

本地读取的求职指南、研发产品训练和 Claude Code Agent 手册，具体文件摘要以 `repository-audit.json` 的 SHA-256 和本地 checkout commit 为准；Andy Product Skill 通过远端读取。只读本地快照不保证与未来远端最新版本永远相同。本记录没有宣称审查了每个仓库的所有文件。

## 四册边界

全局专题负责跨地区求职路径、时间、材料与资格；本册负责 AI 技术岗位、能力差距、技术项目和面试；产品专题负责产品岗位与作品集；商科专题按实际业务职能分流。其他三个候选仓库均不由本次任务创建、编辑或发布。

本次没有对个人主页、总导航、个人官网或任何旧项目执行写入。新项目样例是独立编写的教学代码，不复制旧广告分析练习，不把“用AI写简历”改名当作AI岗位教程。

## 新成果验收点

- 每条岗位有原始来源、核验日期、职责分类理由和资格未知项。
- 学历、专业、编码、数学和研究基础对应可观察的能力验证。
- 三个技术样例都有数据、方法、评测、失败、运行步骤与机器验收。
- 项目结果可转换为真实的简历、GitHub展示和面试追问。
- 政策与雇主要求分开，不套用单一国家的经验。

作者：AI酋长Andy｜星觉科技 · 北京 · 微信号：AIPMAndy。
