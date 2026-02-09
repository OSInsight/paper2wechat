# WeChat Article Template

Use this template when writing from parsed JSON, especially if LLM API keys are unavailable.

```markdown
# [标题：给出结论导向的中文题目]

> 📋 **论文信息**
> - **标题**: [英文原题]
> - **作者**: [作者列表]
> - **论文链接**: [Arxiv URL]
> - **发布日期**: [YYYY-MM-DD 或年份]
> - **开源地址**: [GitHub / HuggingFace / Project URL；若无则写“未提供”]

## 导读

[2-3 句：说明这篇论文和读者有什么关系]

## 实用摘要

- **问题**: [论文要解决的核心问题]
- **创新**: [最关键的新方法或新机制]
- **结果**: [1-3 个关键指标，尽量保留数字]
- **可借鉴做法**: [工程或研究上可以直接复用的点]
- **边界与风险**: [适用条件、失败场景、成本]

## 方法拆解

[用通俗语言解释方法流程，避免堆术语]

![图1说明](../images/[paper_id]/[image_file_from_parsed_json_1])
_图1：说明图中结构/流程与正文结论的关系_

## 实验与结果

[强调对比对象、指标变化、收益和代价]

![图2说明](../images/[paper_id]/[image_file_from_parsed_json_2])
_图2：说明该结果对业务或工程决策的意义_

## 落地建议

- [建议 1]
- [建议 2]
- [建议 3]

## 结语

[1 段：总结价值、适用范围与下一步建议]

## 扩展阅读

### 相关研究

1. [论文/综述 1（含链接）]
2. [论文/综述 2（含链接）]
3. [可选：论文/综述 3（含链接）]

### 技术工具与资源

- [开源项目/代码仓库（含链接）]
- [数据集/评测集（含链接）]
- [可选：文档/教程/项目主页（含链接）]

**关键词**: #论文解读 #技术实践 #方法拆解 #实验结果 #业务落地
```

## Rules

- Keep claims consistent with source paper.
- Add image captions with context; do not drop raw figures without explanation.
- Keep practical summary concise and actionable.
- Prefer extracting open-source links and related resources from parsed JSON text.
- Build image links from `parsed/<paper_id>.json` -> `images[].url`; never guess filenames like `page_*.png`.
- Use image paths that remain valid from `.paper2wechat/outputs/<paper_id>.md`.
- Do not include tool-wrapper artifacts in final markdown: `</content>`, `<parameter name="filePath">...`, or local absolute paths like `/Users/...`.
- Do not append tool credits or auto-generation disclaimers.
