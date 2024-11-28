import aws_cdk as core
import aws_cdk.assertions as assertions

from translate_2.translate_2_stack import Translate2Stack

# example tests. To run these tests, uncomment this file along with the example
# resource in translate_2/translate_2_stack.py
def test_sqs_queue_created():
    app = core.App()
    stack = Translate2Stack(app, "translate-2")
    template = assertions.Template.from_stack(stack)

#     template.has_resource_properties("AWS::SQS::Queue", {
#         "VisibilityTimeout": 300
#     })
