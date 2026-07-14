from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class DemoAgentResult:
    route_agent: str
    answer: str
    tool_name: str


PRODUCT_ANSWER = (
    "云服务器 ECS 的核心属性包括地域与可用区、实例规格、镜像、系统盘和数据盘、"
    "公网带宽、安全组、VPC/交换机以及计费方式。选型时先确认业务峰值 QPS、CPU/内存比例、"
    "磁盘 IO 和是否需要公网访问，再决定规格族和带宽。"
)

ORDER_ANSWER = (
    "已查询最近订单：近 30 天共有 3 笔订单，包含 ECS 包年包月续费、OSS 标准存储资源包、"
    "RDS MySQL 实例升级。当前没有待支付订单，最近一笔订单状态为已完成。"
)

BILLING_ANSWER = (
    "账单概览：本月累计消费约 1,286.40 元，其中 ECS 占 62%，RDS 占 21%，OSS 与公网流量占 17%。"
    "主要增长来自 ECS 按量实例运行时长增加，建议优先检查闲置实例和公网带宽峰值。"
)

PROMOTION_ANSWER = (
    "产品推荐：如果是 Java 接口服务 + MySQL，建议从 ECS 通用算力型 4C8G 或 8C16G 起步，"
    "搭配 RDS MySQL 高可用版和 OSS 存储静态资源。若访问量波动明显，可叠加弹性伸缩和按量实例。"
)

FINOPS_ANSWER = (
    "资源优化建议：发现近 7 天 CPU 峰值低于 10% 的实例可降配或停机；长期稳定运行资源建议转包年包月；"
    "公网带宽建议从固定带宽改为按使用流量计费，并为测试环境设置自动关停策略。"
)


def route_demo_agent(query: str) -> str:
    normalized = query.lower()
    if any(keyword in query for keyword in ("订单", "购买记录", "下单", "续费记录")):
        return "order_agent"
    if any(keyword in query for keyword in ("账单", "费用", "消费", "扣费", "成本")):
        return "billing_agent"
    if any(keyword in query for keyword in ("推荐", "选型", "买", "适合", "海报")):
        return "promotion_agent"
    if any(keyword in query for keyword in ("优化", "降本", "节省", "闲置", "cpu", "内存", "带宽")) or any(
        keyword in normalized for keyword in ("finops", "cost", "cpu")
    ):
        return "finops_agent"
    return "product_agent"


def build_demo_response(query: str) -> DemoAgentResult:
    route_agent = route_demo_agent(query)
    if route_agent == "order_agent":
        return DemoAgentResult(route_agent, ORDER_ANSWER, "mock_order_query")
    if route_agent == "billing_agent":
        return DemoAgentResult(route_agent, BILLING_ANSWER, "mock_billing_query")
    if route_agent == "promotion_agent":
        return DemoAgentResult(route_agent, PROMOTION_ANSWER, "mock_product_recommendation")
    if route_agent == "finops_agent":
        return DemoAgentResult(route_agent, FINOPS_ANSWER, "mock_resource_optimizer")
    return DemoAgentResult(route_agent, PRODUCT_ANSWER, "mock_product_knowledge_base")
