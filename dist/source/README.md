# 中国留学生 AI 岗位求职保姆级攻略

**岗位判断 → 技术能力差距 → 可验证项目 → 技术面试 → 定向申请与复盘。**

作者：**AI酋长Andy**。版本 **1.0.0**，资料核验日期 **2026-11-13**。

“AI 求职”在这里指申请 AI 相关技术岗位。本项目区分算法与机器学习、AI 工程、AI 应用工程；面向不同学历、专业和技术基础的中国留学生，覆盖北美、欧洲、亚洲、大洋洲的代表性地区，并包含回国求职。

> 免费正文、代码与模板完整开放。不需要加微信或购买服务。本版不使用未经核实与公开授权的客户学校、Offer、薪资或成功率。所有候选人情境和技术输入均明确标为教学模拟，不承诺录用。

## 直接开始

- [完整中文攻略](docs/00-start.md)
- [PDF 成品](pdf/chinese-international-student-ai-jobs-guide.pdf)
- [可运行技术项目](examples/README.md)
- [可编辑模板](templates/README.md)
- [岗位研究](research/employer-jds.md) · [地区规则](research/regional-rules.md)
- [验证记录](VALIDATION.md) · [覆盖缺口](research/coverage-gaps.md)

公开仓库：[AIPMAndy/chinese-international-student-ai-jobs](https://github.com/AIPMAndy/chinese-international-student-ai-jobs)。完整正文、可运行代码、PDF、14 套模板与网站已发布；GitHub Actions 远端技术验收、部署及实际 HTTP 下载检查均已成功。发布详情见 [PUBLISH.md](PUBLISH.md)。

网站离线包包含全部静态页面与 PDF、模板、源码下载。解压后可直接打开 `index.html`；完整本地验收建议在该目录运行 `python3 -m http.server 8080 --bind 127.0.0.1`，再打开 `http://127.0.0.1:8080/`。正式网站已部署到 [GitHub Pages](https://aipmandy.github.io/chinese-international-student-ai-jobs/)，并通过实际 HTTP 下载检查。

## 这版实际包含什么

| 交付 | 内容 |
| --- | --- |
| 中文攻略 | 10 个主章节、技术案例、地区与雇主研究、模板 |
| 岗位样本 | 18 条，覆盖 12 个国家或地区；16 条官方详情可读，2 条仅官方索引待复核 |
| 地区研究 | 19 个代表性地区，32 条官方来源记录；保留访问限制与冲突 |
| 技术项目 | 3 个标准库 Python 项目；完整输入、步骤、预期输出、验收与排错 |
| 可编辑模板 | 14 套 Markdown 模板，包括岗位、差距、评测、简历与面试 |
| 网站 | 手机阅读、章节搜索、JD 筛选、资格优先的岗位自查与实测结果 |
| PDF | 完整正文、目录、路线图、案例、操作截图、检查表、页码与来源 |

## 三条路线

| 路线 | 主要职责 | 重点证据 |
| --- | --- | --- |
| R1 算法与机器学习 | 研究、建模、实验与评测 | 数据分割、基线、消融、失败分析、研究贡献 |
| R2 AI 工程 | 模型训练/推理系统、服务、数据链路 | API 契约、可靠性、版本、性能条件和回退 |
| R3 AI 应用工程 | 检索、模型与工具集成、任务交付 | 任务评测、引用、拒答、权限和失败处理 |

AI 产品经理归产品专题。数据科学与解决方案等交叉岗位按主职责分流，详见[岗位路线](docs/01-role-map.md)。标题相同不等于要求相同。

## 一条命令跑完技术练习

下载本仓库源码并进入根目录，使用 Python 3.10+：

```bash
python3 examples/run_all.py
```

Windows 可把 `python3` 换成 `py -3`。无需付费 API、模型下载、账号或 GPU；运行期间会在本机回环地址启动临时 HTTP 服务进行测试，不向外部服务发送数据。

本版固定合成数据的实测结果：分类测试 10/12 正确，macro-F1 0.832011，保留 2 条失败；本地服务 14 项 HTTP 验收通过；检索应用任务正确 12/16，保留 4 条失败。18 项风险测试通过。详细定义与报告在 [examples](examples/README.md)。

这些结果用于教学验收，不能推断真实业务泛化、生产容量或就业结果。检索案例未调用 LLM：它展示的是 BM25、原文抽取与阈值拒答。

## 阅读目录

1. [先缩小目标](docs/00-start.md)
2. [按实际工作区分岗位](docs/01-role-map.md)
3. [判断能力差距与学习行动](docs/02-gap-and-learning.md)
4. [把研究、课程、实习、开源变成证据](docs/03-evidence.md)
5. [技术项目的完整流程](docs/04-project-workflow.md)
6. [GitHub、简历与项目讲解](docs/05-portfolio-and-resume.md)
7. [分岗位技术与行为面试](docs/06-technical-interviews.md)
8. [地区、毕业与雇主资格](docs/07-region-and-eligibility.md)
9. [有针对性的申请](docs/08-targeted-applications.md)
10. [投递与面试复盘](docs/09-review-and-next-steps.md)

附：[三个完整技术案例](docs/technical-case-studies.md)、[18 条 JD 核对卡](research/employer-jds.md)、[19 地区官方路径](research/regional-rules.md)、[技术方法来源](research/technical-sources.md)。

## 与既有项目的边界

本次先只读查看了 `how-to-get-offer`、`teach-rd-product-handbook`、`andy-product-skill` 和 `anthropic-claude-code-agent-handbook` 的目录及正文。本册新增的是岗位判断、技术差距、可验证代码和技术面试，不复制通用求职、产品训练或 Agent 使用手册充数。

审查范围和记录见[去重说明](research/repository-boundary.md)。本次没有修改个人主页、总导航、个人官网或另外三个留学生专题。

## 事实与更新

JD 是带日期的研究样本，不是实时招聘推荐。官方页面可读也不代表仍有名额。工作许可、毕业窗口与雇主支持分开核验；未说明、无法读取和原文冲突都保留原样。申请前重新打开官方原文。

本版尚未穷尽亚洲、欧洲和北美全部国家。非洲、南美洲按范围排除；其他待补地区和岗位见[缺口清单](research/coverage-gaps.md)。

## 常见问题

**教学分数是生产准确率吗？** 分类、服务和检索结果只用于教学验收。它们不能推断真实业务泛化、生产容量或录用结果。

**需要付费 API 吗？** 不需要。快速开始仍是 `python3 examples/run_all.py`，使用本机 Python 标准库，没有付费 API、模型下载、账号或 GPU。

**非洲和南美洲在范围内吗？** 不在。本版排除非洲、南美洲，覆盖北美、欧洲、亚洲、大洋洲和回国求职。

**AI 产品经理看哪一本？** AI 产品经理归产品专题。本册只处理算法、AI 工程与应用工程。

## 许可与贡献

代码采用 [MIT](LICENSE-CODE)，原创攻略/模板采用 [CC BY 4.0](LICENSE-CONTENT.md)，人工构造数据采用 [CC0](examples/DATA-LICENSE.md)。第三方 JD、文档、论文和商标仍归原权利人。请保留来源、许可和自己的贡献边界。

本版由 AI酋长Andy 发起，AI 辅助研究、编写和校验；不将辅助过程包装成未经证实的个人手写贡献。详细说明见 [AUTHORSHIP.md](AUTHORSHIP.md)。勘误与贡献规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

## 作者与可选咨询

**AI酋长Andy**，星觉科技，北京。流量 AI 联合创始人、星觉 AI 创始人。背景由作者提供。可选服务承接岗位判断、项目诊断、AI 转型与求职陪跑。

- 微信号：**AIPMAndy**（备注“留学生 AI 岗位”）

免费内容完整开放，具体服务与费用另行沟通，不承诺拿到 Offer。
