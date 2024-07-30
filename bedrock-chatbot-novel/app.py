#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.chatbot_stack import ChatbotStack

app = cdk.App()

# KnowledgeBaseStack을 먼저 생성
kb_stack = KnowledgeBaseStack(app, "KnowledgeBaseStack")

# ChatbotStack 생성 시 KnowledgeBaseStack에 대한 의존성 추가
chatbot_stack = ChatbotStack(app, "ChatbotStack", knowledge_base_id=kb_stack.knowledge_base_id)
chatbot_stack.add_dependency(kb_stack)

app.synth()