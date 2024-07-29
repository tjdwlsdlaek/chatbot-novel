from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    CfnOutput
)
from constructs import Construct

class ChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, knowledge_base_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # knowledge_base_id를 파라미터로 받아옵니다.
        if not knowledge_base_id:
            raise ValueError("KNOWLEDGE_BASE_ID is not provided")

        # ECR 이미지 생성
        image = ecr_assets.DockerImageAsset(self, "ChatbotImage",
            directory="./app",
            platform=ecr_assets.Platform.LINUX_AMD64
        )

        # ECS 클러스터 생성
        cluster = ecs.Cluster(self, "ChatbotCluster")

        # Fargate 서비스 생성
        fargate_service = ecs_patterns.ApplicationLoadBalancedFargateService(
            self, "ChatbotService",
            cluster=cluster,
            cpu=256,
            memory_limit_mib=512,
            desired_count=1,
            task_image_options=ecs_patterns.ApplicationLoadBalancedTaskImageOptions(
                image=ecs.ContainerImage.from_docker_image_asset(image),
                container_port=8501,  # Streamlit의 기본 포트
                environment={
                    "KNOWLEDGE_BASE_ID": knowledge_base_id
                }
            ),
            assign_public_ip=True
        )

        # IAM 정책 추가 (Amazon Bedrock 접근 권한)
        fargate_service.task_definition.add_to_task_role_policy(
            iam.PolicyStatement(
                actions=[
                    "bedrock:InvokeModel",
                    "bedrock:RetrieveAndGenerate",
                    "bedrock:Retrieve"
                ],
                resources=["*"]
            )
        )

        # 출력
        CfnOutput(self, 'ServiceURL',
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description='Chatbot Service URL'
        )