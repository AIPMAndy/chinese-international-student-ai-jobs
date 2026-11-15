# 07｜中文与英文简历：三条路线的教学样例

版本：2026-11-13。用途：把证据转成准确的申请描述，而不是把教程包装成企业经历。

## 填写说明

下方全部是教学模拟，不对应任何学生、学校、客户或Offer。示范假设读者已亲自复现、理解并能解释相应实验；没有完成就不能使用。数字来自本仓库固定合成输入，只说明这次实验，不代表真实用户或商业效果。

每条项目描述按“本人做了什么→针对什么问题→怎样比较或验收→结果与边界”组织。只有运行上游代码时写“复现”；自己新增的部分必须有diff、实验记录或其他证据。求职简历不必塞满所有限制，但不能删掉“教学、合成数据、局部测量”这些改变结论含义的条件。

## 空白可复制结构

### 中文简历骨架

姓名：【真实姓名】｜所在地：【城市】｜联系方式：【自己的信息】  
GitHub：【个人链接】｜目标岗位：【具体路线与级别】

**教育背景**：【真实学校、学位、专业、起止时间、预计/实际毕业月】。相关课程：【只列能回答的问题】。

**技术能力**：【技能】——【能用它完成的任务/证据】，不把“听过”写为“精通”。

**项目：**【名称】｜【教学/开源复现/个人改进/获授权的真实项目】｜【日期】  
- 【本人动作】＋【方法与比较】＋【有分母/范围的结果】。  
- 【本人新增贡献】＋【验收方式】＋【当前限制】。  
证据：【README、提交、报告】。上游与AI辅助：【简短注明，详细声明链接】。

**经历：**【仅填真实且可核验的实习/工作；没有就省略】。

### English structure

**Name:** [Your actual name] | **Location:** [City] | **GitHub:** [URL]

**Education:** [Actual institution, degree, subject, expected/completed graduation month and year]

**Project:** [Title] | [Teaching replication / personal extension / authorized real project] | [Dates]

- [Your action] to address [specific problem], using [method/baseline]; measured [metric with denominator and scope].
- Added [your verified contribution], checked with [test/evidence], with [material limitation].

**Evidence:** [Repository / commit / report]. **Attribution:** [Upstream work and AI assistance, with disclosure link].

## R1：算法与机器学习示范

**中文，教学模拟：**

- 复现并审查合成工单分类基线，在51条输入上保持30/9/12的训练、开发、测试划分；仅用开发集选参，固定12条测试中10条正确，macro-F1为0.832，记录2个边界错误。
- 本人新增：【具体实验或代码改动】；使用【独立评测或复现检查】验收。该练习未验证真实业务数据上的泛化能力。

**English, teaching example:**

- Reproduced and reviewed a text-classification baseline on 51 synthetic tickets, using fixed 30/9/12 train/development/test splits and development-only selection; recorded 10 correct predictions out of 12 test cases and a macro-F1 of 0.832.
- Added [your actual experiment or code change] and verified it with [evidence]. These results apply only to the bundled synthetic test set.

来源：[分类README](../examples/01_ml_experiment/README.md)、[实际评测报告](../examples/01_ml_experiment/reports/evaluation.json)。这不构成研究创新或论文成果。

## R2：AI工程示范

**中文，教学模拟：**

- 复现本地模型HTTP服务并复跑14项接口验收，检查输入校验、错误状态、批次顺序与并发请求响应；保存模型标识和可重放请求记录。
- 本人新增：【实际接口/测试/错误处理改动】。测量限定本机回环网络；没有据此声称生产容量、云部署或线上可用率。

**English, teaching example:**

- Reproduced a local model HTTP service and reran 14 acceptance checks covering input validation, error responses, batch ordering, and concurrent requests; retained versioned model and request evidence.
- Added [your actual contribution]. Measurements cover a local loopback setup and do not establish production capacity or availability.

来源：[服务验收报告](../examples/02_model_service/reports/verification.json)。不要把40次本地串行延迟测量写成大规模压测。

## R3：AI应用工程示范

**中文，教学模拟：**

- 复现BM25检索与引用/拒答基线，在8篇虚构文档和固定16题测试上取得12题符合任务预期；保留4条失败，区分检索缺失、错误拒答和不可回答问题误作答。
- 本人新增：【实际评测/接口/错误分析改动】。该基线不调用LLM，未验证生成式RAG或真实提示注入防护。

**English, teaching example:**

- Reproduced a BM25 retrieval baseline with extractive citations and refusal rules, recording 12 successful outcomes across 16 fixed test questions over eight fictional documents; retained four failures for analysis.
- Added [your actual contribution]. The baseline does not call an LLM and does not establish production RAG quality or prompt-injection resistance.

来源：[检索评测报告](../examples/03_grounded_retrieval/reports/evaluation.json)、[固定验收口径](../examples/expected_metrics.json)。

## 不能直接替换的说法

| 有证据的表达 | 没有证据时不能写 |
| --- | --- |
| 复现教学基线 | 从零独立研发商用系统 |
| 固定合成测试10/12正确 | 线上客户准确率83% |
| 本机14项HTTP验收通过 | 支撑百万用户高并发 |
| 引用与拒答实验 | 已解决大模型幻觉或提示注入 |
| 本人新增一个测试并定位错误 | 主导整个团队研发 |

## 验收标准

- 所有学校、日期、经历和贡献都真实；没有填充虚构身份。
- 每个数字有来源、分母和实验边界，结果与当前代码一致。
- “本人新增”不能空着；没有新增就明确只是复现练习。
- 能在面试中解释一个失败、一个取舍、一个不是自己完成的部分。

作者：AI酋长Andy｜星觉科技 · 北京 · 微信号：AIPMAndy  
