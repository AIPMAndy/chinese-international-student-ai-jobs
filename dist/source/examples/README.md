# 三个能运行、能解释、能查错的技术样例

作者：AI 酋长 Andy · 微信：AIPMAndy · 公众号：AI酋长Andy  
个人官网：https://metaver.vip/ · 公司官网：https://www.a6no1.cn/  
版本：2026-11-13。全部为教学模拟，不代表客户案例、商业部署或求职成绩。

## 先跑起来

要求：Python 3.10 或以上。本次实际验收环境为 Python 3.12.14 / Linux。只用标准库，不需要安装依赖、下载模型、GPU、账号或 API Key。进入仓库根目录后运行：

```bash
python3 --version
python3 examples/run_all.py
```

Windows 可把 `python3` 替换为 `py -3`。最终出现 `ALL_EXAMPLES_ACCEPTED` 即通过。运行约数秒；服务测试使用本机随机端口，完成后自动关闭。隔离环境如果禁用回环网络，第二个案例会失败，不能把这一项写成已验收。

| 路线 | 样例 | 核心输入 | 要证明的能力 | 不能证明什么 |
|---|---|---|---|---|
| 算法 / ML | [01 文本分类实验](01_ml_experiment/README.md) | 51 条合成工单，固定 train/dev/test | 数据划分、基线、参数选择、评测、失败归因 | 研究创新、大模型训练、真实业务效果 |
| AI 工程 | [02 模型 HTTP 服务](02_model_service/README.md) | 01 的模型文件、JSON 请求 | 模型产物、接口契约、错误处理、实际 HTTP 测试、延迟测量 | 生产可用性、高并发容量、云部署安全 |
| AI 应用工程 | [03 有引用与拒答的检索应用](03_grounded_retrieval/README.md) | 8 篇虚构实验室文档、24 道问题 | 检索、证据、拒答、评测集、故障定位 | LLM 生成质量、真实 RAG 效果、提示注入防护能力 |

这三项是练习起点。算法研究岗位通常还需要与 JD 对应的研究经历、论文或更深入的实验；工程岗位需要进一步展示代码质量、系统设计与真实规模下的取舍。不要只改项目名就放进简历。

## 结果在哪里

| 文件 | 用途 |
|---|---|
| `01_ml_experiment/reports/evaluation.json` | 数据哈希、dev 选择过程、test 指标、混淆矩阵、每题结果 |
| `01_ml_experiment/reports/model.json` | 可读 JSON 模型产物 |
| `02_model_service/reports/verification.json` | 14 项 HTTP 验收、真实响应、40 次本地延迟样本 |
| `03_grounded_retrieval/reports/evaluation.json` | 阈值选择、检索与拒答指标、逐题证据 |
| 两个 `failures.json` | 必须解释的失败样本 |
| `verification-summary.json` | 全量验收摘要 |
| `expected_metrics.json` | 固定输入的验收值；不固定机器相关延迟 |

不要修改 `expected_metrics.json` 来让失败变成通过。确实修改了数据或方法时，保留旧结果，记录新实验 ID、修改理由和 test 是否已被查看；建立新的独立测试集再评价泛化能力。

## 怎么形成自己的证据

1. 原样复现一次，记录机器环境、提交号、运行命令和结果。
2. 选一个具体失败，先提出原因，再只改一个因素。
3. 保留 baseline，用 dev 做选择。已经反复查看的 test 只能作为回归集；新结论需要新测试数据。
4. 给出自己新增的代码 diff、数据来源、评测结果和没有解决的问题。
5. 用 3 分钟讲清“问题、方法、比较、失败、限制、个人贡献”。

## 归属与许可

代码为本项目新写的 MIT 教学实现，制作过程中使用 AI 辅助；未复制第三方实现。合成输入见 [数据许可](DATA-LICENSE.md)。读者需要在 `CONTRIBUTIONS.md` 区分上游基线、个人修改、AI 辅助和人工验收。不能把本仓库已有代码说成自己从零独立实现，不能把模拟项目写成真实公司业务。

资料免费完整开放。需要外部反馈时，咨询可聚焦“选哪条路线、项目缺哪类证据、面试解释哪里不清楚”；不承诺拿到 Offer。
