import aws_cdk as core
import aws_cdk.assertions as assertions

from persona_chatbot_usermade.persona_chatbot_usermade_stack import PersonaChatbotUsermadeStack

# example tests. To run these tests, uncomment this file along with the example
# resource in persona_chatbot_usermade/persona_chatbot_usermade_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = PersonaChatbotUsermadeStack(app, "persona-chatbot-usermade")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
