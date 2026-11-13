# 技术方法来源

核验日期：2026-11-13。仅引用官方文档和原始论文。以下是概念来源，不表示本仓库导入了这些库、复现了论文系统，或取得论文中的结果。代码与合成样例由本项目独立编写，方法说明与实测结果分开。

| ID | 来源 | 本册使用范围 | 访问状态 |
| --- | --- | --- | --- |
| T01 | [scikit-learn：Common pitfalls](https://scikit-learn.org/stable/common_pitfalls.html) | 数据泄漏、分割后拟合预处理；本册未依赖 sklearn | 官方正文已读取 |
| T02 | [scikit-learn：Metrics and scoring](https://scikit-learn.org/stable/modules/model_evaluation.html) | precision、recall、F1、macro平均与指标选择 | 官方正文已读取 |
| T03 | [PyTorch：Reproducibility](https://docs.pytorch.org/docs/2.15/notes/randomness.html) | 跨环境重现的限制、随机性与环境记录；本册未运行PyTorch训练 | 官方正文已读取；stable入口指向此版本 |
| T04 | [Lewis et al., Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks](https://arxiv.org/abs/2005.11401) | 检索与生成的概念边界；本册离线样例无生成模型 | 原始论文摘要页已读取 |
| T05 | [Python：http.server](https://docs.python.org/3/library/http.server.html) | 本地HTTP演示的适用边界；标准库服务器不适合作为生产部署方案 | 官方正文已读取 |
| T06 | [GitHub：Custom workflows with GitHub Pages](https://docs.github.com/en/pages/getting-started-with-github-pages/using-custom-workflows-with-github-pages) | 配套静态站部署流程与权限；工作流已准备，未声称GitHub远端实际执行 | 官方正文已读取 |

Python 标准库接口以运行环境附带文档为准。示例项目只要求 Python 3.10+，所有外部模型适配仅在实际实现、运行与评测后才可声称验证。没有在线模型测评、GPU训练或真实用户业务指标。

第三方文档、商标、论文和招聘原文的权利归各权利人。链接与有限摘要不将第三方内容改授本项目许可证。
