"""CDK entry point: `cdk deploy` (run from infra/) builds everything in stack.py.

Account and region come from your AWS CLI profile (aws configure), so no account
id is written into the repo. CDK sets CDK_DEFAULT_ACCOUNT / CDK_DEFAULT_REGION.
"""
import os

import aws_cdk as cdk

from stack import DisputeAgentStack

app = cdk.App()
DisputeAgentStack(
    app, "DisputeAgentStack",
    env=cdk.Environment(account=os.getenv("CDK_DEFAULT_ACCOUNT"),
                        region=os.getenv("CDK_DEFAULT_REGION")),
    description="Dispute Response Agent: state table (more resources added in Part C)",
)
cdk.Tags.of(app).add("project", "dispute-agent")   # every resource gets this tag (cost tracking)
app.synth()
