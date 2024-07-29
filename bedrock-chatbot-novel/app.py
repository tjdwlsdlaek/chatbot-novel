#!/usr/bin/env python3
import aws_cdk as cdk
from stacks.knowledge_base_stack import KnowledgeBaseStack
from stacks.chatbot_stack import ChatbotStack

app = cdk.App()

kb_stack = KnowledgeBaseStack(app, "KnowledgeBaseStack")
ChatbotStack(app, "ChatbotStack", knowledge_base_id=kb_stack.knowledge_base_id)

app.synth()