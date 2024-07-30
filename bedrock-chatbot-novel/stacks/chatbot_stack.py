from aws_cdk import (
    Stack,
    aws_ecs as ecs,
    aws_ecr_assets as ecr_assets,
    aws_ecs_patterns as ecs_patterns,
    aws_iam as iam,
    aws_lambda as lambda_,
    custom_resources as cr,
    CfnOutput,
    Fn
)
from constructs import Construct

class ChatbotStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, knowledge_base_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        knowledge_base_id = Fn.import_value('KnowledgeBaseId')

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
        # Lambda 함수 생성
        start_ingestion_job_lambda = lambda_.Function(
            self, 'StartIngestionJobLambda',
            runtime=lambda_.Runtime.PYTHON_3_9,
            handler='index.handler',
            code=lambda_.Code.from_asset('./lambda/'),
            environment={
                'KNOWLEDGE_BASE_ID': knowledge_base_id
            }
        )

        # Lambda에 필요한 권한 부여
        start_ingestion_job_lambda.add_to_role_policy(
            iam.PolicyStatement(
                actions=['bedrock:StartIngestionJob'],
                resources=['*']
            )
        )

        # Custom Resource를 위한 IAM 역할 생성
        custom_resource_role = iam.Role(
            self, 'CustomResourceRole',
            assumed_by=iam.ServicePrincipal('lambda.amazonaws.com')
        )

        # Custom Resource 역할에 Lambda 호출 권한 추가
        custom_resource_role.add_to_policy(
            iam.PolicyStatement(
                actions=['lambda:InvokeFunction'],
                resources=[start_ingestion_job_lambda.function_arn]
            )
        )

        # Custom Resource 생성
        cr.AwsCustomResource(
            self, 'TriggerStartIngestionJobLambda',
            on_create=cr.AwsSdkCall(
                service='Lambda',
                action='invoke',
                parameters={
                    'FunctionName': start_ingestion_job_lambda.function_name,
                    'InvocationType': 'Event'
                },
                physical_resource_id=cr.PhysicalResourceId.of('TriggerStartIngestionJobLambda')
            ),
            policy=cr.AwsCustomResourcePolicy.from_statements([
                iam.PolicyStatement(
                    actions=['lambda:InvokeFunction'],
                    resources=[start_ingestion_job_lambda.function_arn]
                )
            ]),
            role=custom_resource_role
        )

        # Lambda 함수 URL 생성 (테스트 목적)
        lambda_url = start_ingestion_job_lambda.add_function_url(
            auth_type=lambda_.FunctionUrlAuthType.NONE
        )

        # Lambda 함수 URL 출력
        CfnOutput(self, 'StartIngestionJobLambdaUrl',
            value=lambda_url.url,
            description='URL for the Start Ingestion Job Lambda function'
        )

        # 출력
        CfnOutput(self, 'ServiceURL',
            value=f"http://{fargate_service.load_balancer.load_balancer_dns_name}",
            description='Chatbot Service URL'
        )