# WeChat Article Template

Use this as a base scaffold when writing from parsed JSON.
This template is intentionally flexible: keep required blocks, then add/remove optional blocks by style and paper type.

```markdown
# [标题：给出结论导向的中文题目]

> 📋 **论文信息**
> - **标题**: [英文原题]
> - **作者**: [作者列表]
> - **机构/单位**: [作者所属团队/公司/高校/研究机构；若无法确定写“未明确注明”]
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

[可插入 1-2 张图（优先总览图、方法流程图）]
![图N说明](../images/[image_file_from_parsed_json_n])
_图N：说明图中结构/流程与正文结论的关系_

## 实验与结果

[强调对比对象、指标变化、收益和代价]

[可插入 1-3 张图（优先关键对比图、主结果图）]
![图N说明](../images/[image_file_from_parsed_json_n])
_图N：说明该结果对业务或工程决策的意义_

## 落地建议

- [建议 1]
- [建议 2]
- [建议 3]

## [可选] 工程实现与复现要点

[适合 academic-tech / academic-science：系统结构、算力成本、训练/推理配置、复现风险]

## [可选] 趋势判断与影响

[适合 academic-trend：技术演进、潜在影响、未来 1-3 年观察点]

## [可选] 应用场景与ROI

[适合 academic-applied：落地门槛、业务指标、收益与投入]

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

- Treat this as a scaffold, not a rigid format; section names/order can change by paper type.
- Required blocks: `论文信息` + `导读` + `实用摘要` + 主体分析 + `结语` + `扩展阅读`.
- Use 6-9 headings total; avoid long repetitive structure when paper is short.
- Keep claims consistent with source paper.
- Add image captions with context; do not drop raw figures without explanation.
- Keep practical summary concise and actionable.
- Prefer extracting open-source links and related resources from parsed JSON text.
- Prefer using parsed JSON `affiliations` for 机构/单位; if missing, write `未明确注明`.
- Build image links from `.paper2wechat/<paper_id>/parsed/<paper_id>.json` -> `images[].url`; never guess filenames like `page_*.png`.
- Use image paths that remain valid from `.paper2wechat/<paper_id>/outputs/<paper_id>.md`.
- Use dynamic image count (`2-6` usually) based on article structure and figure relevance; avoid mechanical fixed count.
- Do not include tool-wrapper artifacts in final markdown: `</content>`, `<parameter name="filePath">...`, or local absolute paths like `/Users/...`.
- Do not append tool credits or auto-generation disclaimers.
