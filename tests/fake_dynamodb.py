"""An in-memory stand-in for a boto3 DynamoDB Table: just the calls records/state.py
makes, with the same conditional-write behaviour. No AWS calls in tests."""
import copy

from botocore.exceptions import ClientError


class FakeTable:
    def __init__(self):
        self.items: dict[str, dict] = {}
        self.puts = 0

    def get_item(self, Key, ConsistentRead=False):
        item = self.items.get(Key["pk"])
        return {"Item": copy.deepcopy(item)} if item else {}

    def put_item(self, Item, ConditionExpression=None, ExpressionAttributeValues=None):
        current = self.items.get(Item["pk"])
        if ConditionExpression == "attribute_not_exists(pk)":
            ok = current is None
        elif ConditionExpression == "version = :expected":
            ok = current is not None and current["version"] == ExpressionAttributeValues[":expected"]
        else:
            ok = ConditionExpression is None
        if not ok:
            raise ClientError({"Error": {"Code": "ConditionalCheckFailedException",
                                         "Message": "The conditional request failed"}}, "PutItem")
        self.items[Item["pk"]] = copy.deepcopy(Item)
        self.puts += 1
