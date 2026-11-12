"""Everything the app needs on AWS, as code. For now: the state table."""
from aws_cdk import CfnOutput, RemovalPolicy, Stack
from aws_cdk import aws_dynamodb as dynamodb
from constructs import Construct

TABLE_NAME = "dispute-agent-state"


class DisputeAgentStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # One item, pk="state", holds the whole app state plus a version number.
        # records/state.py writes it with a conditional write (optimistic locking).
        self.table = dynamodb.Table(
            self, "StateTable",
            table_name=TABLE_NAME,
            partition_key=dynamodb.Attribute(name="pk", type=dynamodb.AttributeType.STRING),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,   # on-demand: pay per request
            removal_policy=RemovalPolicy.DESTROY,                # hackathon: cdk destroy leaves nothing
        )

        CfnOutput(self, "StateTableName", value=self.table.table_name)
