# 跨前后端业务事实层

本目录是 Careerpass 的跨前后端业务事实层，回答“产品在业务上是什么、用户可以做什么、系统必须遵守什么业务规则”。

入口文档：

- [`business-baseline.md`](business-baseline.md)：当前已确认的业务事实及事实编号；
- [`business-fact-extraction.md`](business-fact-extraction.md)：从前端文档提取、审核、更新和供 Slice 使用业务事实的机制。

前端文档是业务事实的主要候选来源，后端文档是实现和技术事实来源。本目录发布后，前后端 Slice 不再分别从大量前端文档中重新猜测已经确认的业务语义。
