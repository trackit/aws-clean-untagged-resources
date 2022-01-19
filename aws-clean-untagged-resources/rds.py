import boto3
import slack
from datetime import timedelta


class RDSService:
    def __init__(self, tag_key, tag_value, lifetime_tag_key):
        self.slack_service: slack.Slack = slack.Slack.get_instance()
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.boto3_client = None
        self.boto3_resource = None

    def set_boto3(self, region):
        self.boto3_client = boto3.client(service_name='rds', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_element_rds(self, instance, region):
        result = "*" + instance['DBInstanceIdentifier'] + " (" + instance['DbiResourceId'] + ")*\n"
        result += ":birthday: *Launch date* " + str(instance['InstanceCreateTime']) + "\n:wrench: *Engine* " + instance[
            'Engine'] + "\n"
        expired_date = "No Tag Provided"
        for tag in instance['TagList']:
            result += ":label: `" + tag['Key'] + "` = `" + tag['Value'] + "`\n"
            if tag['Key'] == self.lifetime_tag_key:
                expired_date = instance['InstanceCreateTime'] + timedelta(int(tag['Value']))
        result += ":skull_and_crossbones: *Expiration date* " + str(expired_date) + "\n"
        url = "https://" + region + ".console.aws.amazon.com/rds/home?region=" + region + "#databases:"
        self.slack_service.append_blocks({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": result
            },
            "accessory": {
                "type": "button",
                "text": {
                    "type": "plain_text",
                    "text": "Manage it on RDS console",
                },
                "value": "click_me_123",
                "url": url,
                "action_id": "button-action"
            }
        })
        self.slack_service.append_blocks({
            "type": "divider"
        })

    def rds_instances_loop(self, region):
        untagged_rds = []
        n = 0

        self.slack_service.section_header_text('RDS')

        instances = self.boto3_client.describe_db_instances()
        for instance in instances['DBInstances']:
            has_tag = False
            for tag in instance['TagList']:
                if tag['Key'] == 'Name':
                    instance_name = tag['Value']
                if tag['Key'] == self.tag_key and tag['Value'] == self.tag_value:
                    has_tag = True
                    break

            if not has_tag:
                self.generate_text_element_rds(instance, region)
                untagged_rds.append(instance['DBInstanceIdentifier'])
                n += 1
        if n == 0:
            self.slack_service.no_resources_text()
        return untagged_rds

    def stop_instances(self, instances):
        for instance in instances:
            self.boto3_client.strop_db_instances(DBInstanceIdentifier=instance, DBSnapshotIdentifier=instance)
