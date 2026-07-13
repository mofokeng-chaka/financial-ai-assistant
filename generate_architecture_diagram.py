"""Generate architecture diagram for the Financial Services AI Assistant."""

from diagrams import Diagram, Cluster, Edge
from diagrams.aws.ml import Bedrock
from diagrams.aws.compute import Lambda
from diagrams.aws.network import APIGateway, Route53
from diagrams.aws.integration import StepFunctions
from diagrams.aws.management import SystemsManagerParameterStore as AppConfig
from diagrams.aws.management import Cloudwatch
from diagrams.aws.general import User

graph_attr = {
    "fontsize": "14",
    "bgcolor": "white",
    "pad": "0.5",
    "nodesep": "0.7",
    "ranksep": "1.0",
}

with Diagram(
    "Financial AI Assistant - Circuit Breaker Architecture",
    filename="architecture",
    show=False,
    direction="TB",
    graph_attr=graph_attr,
    outformat="png",
):
    user = User("Client\nApplication")
    dns = Route53("Route53\nFailover DNS")

    with Cluster("Primary Region (us-east-1)"):
        apigw1 = APIGateway("API Gateway\nPOST /generate\nGET /health")

        with Cluster("Step Functions - Circuit Breaker"):
            sfn = StepFunctions("Express\nState Machine")

            with Cluster("Stage 1: Primary"):
                primary = Lambda("Model Abstraction\n(Claude Sonnet 4.5)")

            with Cluster("Stage 2: Fallback"):
                fallback = Lambda("Fallback Model\n(Nova Lite)")

            with Cluster("Stage 3: Degradation"):
                degraded = Lambda("Graceful\nDegradation")

        appconfig = AppConfig("AWS AppConfig\nModel Selection\nStrategy")
        cw1 = Cloudwatch("CloudWatch\nAlarms & Logs")

        with Cluster("Amazon Bedrock Models"):
            bedrock_primary = Bedrock("Claude Sonnet 4.5\n(Primary)")
            bedrock_fallback = Bedrock("Nova Lite\n(Fallback)")

    with Cluster("Secondary Region (us-west-2)", graph_attr={"style": "dashed"}):
        apigw2 = APIGateway("API Gateway\n(Standby)")
        sfn2 = StepFunctions("Circuit Breaker\n(Standby)")

    # Client flow
    user >> dns
    dns >> Edge(label="Active") >> apigw1
    dns >> Edge(label="Failover", style="dashed") >> apigw2

    # Primary region flow
    apigw1 >> sfn
    sfn >> Edge(label="Try 1\n(retry 2x)") >> primary
    primary >> Edge(label="fail", style="dashed", color="red") >> fallback
    fallback >> Edge(label="fail", style="dashed", color="red") >> degraded

    # Model invocations
    primary >> bedrock_primary
    fallback >> bedrock_fallback
    primary >> Edge(label="Config", style="dotted") >> appconfig

    # Monitoring
    primary >> Edge(style="dotted") >> cw1
    fallback >> Edge(style="dotted") >> cw1

    # Secondary region
    apigw2 >> sfn2
