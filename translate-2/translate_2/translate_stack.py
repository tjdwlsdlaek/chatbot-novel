from aws_cdk import (
    Stack,
    aws_ec2 as ec2,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_dynamodb as dynamodb,
    aws_apigatewayv2 as apigatewayv2,
    aws_lambda as lambda_,
    aws_iam as iam,
    aws_elasticloadbalancingv2 as elbv2,
    CfnOutput,
    Duration
)
from constructs import Construct

class TranslateStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # Create VPC
        vpc = ec2.Vpc(self, "TranslateVpc", max_azs=2)

        # Create ECS Cluster
        cluster = ecs.Cluster(self, "TranslateCluster", vpc=vpc)

        # Create DynamoDB table
        chat_table = dynamodb.Table(
            self, "ChatMessages",
            partition_key=dynamodb.Attribute(name="id", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST
        )

        # Create Streamlit Docker image
        streamlit_image = ecr_assets.DockerImageAsset(self, "StreamlitImage",
            directory='app/streamlit'
        )

        # Streamlit ECS Task Definition
        streamlit_task_definition = ecs.FargateTaskDefinition(self, "StreamlitTaskDefinition",
            memory_limit_mib=512,
            cpu=256,
        )

        streamlit_container = streamlit_task_definition.add_container("StreamlitContainer",
            image=ecs.ContainerImage.from_docker_image_asset(streamlit_image),
            logging=ecs.LogDrivers.aws_logs(stream_prefix="Streamlit"),
            environment={
                'API_GATEWAY_URL': 'PLACEHOLDER_URL'  # We'll update this later
            }
        )

        streamlit_container.add_port_mappings(ecs.PortMapping(container_port=8501, host_port=8501))

        # Streamlit ECS Service
        streamlit_service = ecs.FargateService(self, "StreamlitService",
            cluster=cluster,
            task_definition=streamlit_task_definition,
            desired_count=1,
            assign_public_ip=True
        )

        # Lambda function for FastAPI
        fastapi_lambda = lambda_.Function(self, "FastAPILambda",
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler="main.handler",  # Ensure this is the correct handler path
            code=lambda_.Code.from_asset("app/fastapi"),
            environment={
                'DYNAMODB_TABLE_NAME': chat_table.table_name
            }
        )

        # Grant permissions to Lambda
        chat_table.grant_read_write_data(fastapi_lambda)
        fastapi_lambda.add_to_role_policy(iam.PolicyStatement(
            actions=["bedrock:InvokeModel"],
            resources=["*"]
        ))

        # WebSocket API
        websocket_api = apigatewayv2.CfnApi(self, "ChatWebSocketApi",
            name="ChatWebSocketApi",
            protocol_type="WEBSOCKET",
            route_selection_expression="$request.body.action"
        )

        # Integration for WebSocket API
        integration = apigatewayv2.CfnIntegration(self, "WebSocketIntegration",
            api_id=websocket_api.ref,
            integration_type="AWS_PROXY",
            integration_uri=fastapi_lambda.function_arn,
            integration_method="POST"
        )

        # Routes for WebSocket API
        apigatewayv2.CfnRoute(self, "ConnectRoute",
            api_id=websocket_api.ref,
            route_key="$connect",
            authorization_type="NONE",
            target="integrations/" + integration.ref
        )

        apigatewayv2.CfnRoute(self, "DisconnectRoute",
            api_id=websocket_api.ref,
            route_key="$disconnect",
            authorization_type="NONE",
            target="integrations/" + integration.ref
        )

        apigatewayv2.CfnRoute(self, "DefaultRoute",
            api_id=websocket_api.ref,
            route_key="$default",
            authorization_type="NONE",
            target="integrations/" + integration.ref
        )

        # Stage for WebSocket API
        websocket_stage = apigatewayv2.CfnStage(self, "ProdStage",
            api_id=websocket_api.ref,
            stage_name="prod",
            auto_deploy=True
        )

        # Grant Lambda permission to be invoked by API Gateway
        fastapi_lambda.add_permission("WebSocketPermission",
            principal=iam.ServicePrincipal("apigateway.amazonaws.com"),
            action="lambda:InvokeFunction",
            source_arn=f"arn:aws:execute-api:{self.region}:{self.account}:{websocket_api.ref}/*"
        )

        # Output the WebSocket URL
        websocket_url = f"wss://{websocket_api.ref}.execute-api.{self.region}.amazonaws.com/{websocket_stage.stage_name}"
        CfnOutput(self, "WebSocketURL",
            value=websocket_url,
            description="WebSocket URL"
        )

        # Application Load Balancer for Streamlit
        lb = elbv2.ApplicationLoadBalancer(self, "StreamlitLB",
            vpc=vpc,
            internet_facing=True
        )

        listener = lb.add_listener("StreamlitListener", port=80)
        
        target_group = listener.add_targets("StreamlitTarget",
            port=8501,
            targets=[streamlit_service.load_balancer_target(container_name="StreamlitContainer", container_port=8501)],
            protocol=elbv2.ApplicationProtocol.HTTP,
            health_check=elbv2.HealthCheck(
                path="/",
                healthy_http_codes="200",
                interval=Duration.seconds(30),
                timeout=Duration.seconds(5)
            )
        )

        CfnOutput(self, "StreamlitURL",
            value=f"http://{lb.load_balancer_dns_name}",
            description="URL for Streamlit application"
        )

        # Update Streamlit environment with WebSocket URL
        streamlit_container.add_environment("API_GATEWAY_URL", websocket_url)
