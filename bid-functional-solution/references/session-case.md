# Session Case: 12320预约挂号系统

## User Goal

Create a new Word document for a bid document's 功能建设方案 module based on `12320公众号需规.docx`, organized by:

1. 图片
2. 功能说明
3. 功能描述

## Source Characteristics

- Source document: 12320公众号需求规格说明书
- Major scopes: 客户端功能性需求说明 and 管理后台功能性需求说明
- Source contained custom heading styles, use-case tables, flowcharts, prototype screenshots, and rule descriptions
- Relevant extracted structure: about 39 function sections after scope cleanup
- Images were reused as function visual evidence

## Key Iterations

1. Initial document copied source sections too closely.
2. User clarified that `功能说明` should be a bid-ready capability sentence, while `功能描述` should be functional bullets.
3. The document was regenerated with rewritten capability prose.
4. User requested removal of 候补功能 and 排队叫号功能.
5. The final document removed those functions from headings, overview, prose, captions, and screenshots.
6. User provided a mixed flowchart image and requested a new version without `候补记录`; the image was deterministically edited so Chinese text stayed exact.

## Final Document Behavior

The final Word document:

- Uses professional bid language instead of use-case table labels
- Keeps `图片 / 功能说明 / 功能描述` order
- Removes `候补` and `排队叫号` residues
- Keeps remaining functions such as 首页、我的、常用联系人、预约挂号、搜索、检验检查、预防接种、体检预约、常见问题、健康百科、新闻资讯、问卷调查、登录、管理后台登录、查询统计、业务运维、信息发布、集群管理
- Passes DOCX structural checks and image relationship checks

## Important Lesson

For bid documents, never treat a requirement use-case table as the final prose. Use the table as source material, then rewrite into construction-scope capabilities.
