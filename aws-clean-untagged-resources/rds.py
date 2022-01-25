import datetime
import logging
import boto3
import slack
from datetime import timedelta, datetime
import pytz


class RDSService:
    def __init__(self, tag_key, tag_value, lifetime_tag_key):
        self.slack_service: slack.Slack = slack.Slack.get_instance()
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.boto3_client = None
        self.boto3_resource = None
        self.untagged_resources = []
        self.lifetime_tagged_resources = []

    def set_boto3(self, region):
        self.boto3_client = boto3.client(service_name='rds', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_element_rds(self, instance, region):
        result = f'*{instance["DBInstanceIdentifier"]} ({instance["DbiResourceId"]})*\n'
        result += f':birthday: *Launch date* {str(instance["InstanceCreateTime"])}\n' \
                  f':wrench: *Engine* {instance["Engine"]}\n'
        expired_date = 'No Tag Provided'
        if instance["TagList"]:
            for tag in instance["TagList"]:
                result += f':label: `{tag["Key"]}` = `{tag["Value"]}`\n'
                if tag["Key"] == self.lifetime_tag_key:
                    expired_date = instance["InstanceCreateTime"] + timedelta(int(tag["Value"]))
                    if (instance["InstanceCreateTime"] + timedelta(int(tag["Value"]))) > \
                            pytz.utc.localize(datetime.now()):
                        expired_date = f'{str(expired_date)}\n:warning: Expired Resource'
        result += f':skull_and_crossbones: *Expiration date* {str(expired_date)}\n'
        url = f'https://{region}.console.aws.amazon.com/rds/home?region={region}#databases:'
        self.slack_service.append_blocks({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': result
            },
            'accessory': {
                'type': 'button',
                'text': {
                    'type': 'plain_text',
                    'text': 'Manage it on RDS console',
                },
                'value': 'click_me_123',
                'url': url,
                'action_id': 'button-action'
            }
        })
        self.slack_service.append_blocks({
            'type': 'divider'
        })

    def resources_loop(self, region):
        n = 0

        self.slack_service.section_header_text('RDS')

        instances = self.boto3_client.describe_db_instances()
        for instance in instances["DBInstances"]:
            has_tag = False
            has_lifetime_tag = False
            if instance["TagList"]:
                for tag in instance["TagList"]:
                    # The following commented code isn't used for now
                    # if tag["Key"] == 'Name':
                    #     instance_name = tag["Value"]
                    if tag["Key"] == self.tag_key and tag["Value"] == self.tag_value:
                        has_tag = True
                        break
                    if tag["Key"] == self.lifetime_tag_key and \
                            (instance["InstanceCreateTime"] + timedelta(int(tag["Value"]))) > \
                            pytz.utc.localize(datetime.now()):
                        has_lifetime_tag = True
                        break

            if not has_tag:
                if has_lifetime_tag:
                    self.lifetime_tagged_resources.append(instance)
                else:
                    self.untagged_resources.append(instance)
                self.generate_text_element_rds(instance, region)
                n += 1

        if n == 0:
            self.slack_service.no_resources_text()
        return self.untagged_resources

    def get_untagged_resources(self):
        return self.untagged_resources

    def get_lifetime_tagged_resources(self):
        return self.lifetime_tagged_resources

    def stop_untagged_resources(self):
        for instance in self.untagged_resources:
            self.boto3_client.stop_db_instance(
                DBInstanceIdentifier=instance["DBInstanceIdentifier"],
                DBSnapshotIdentifier=instance["DBInstanceIdentifier"]
            )

    def terminate_untagged_resources(self):
        for instance in self.untagged_resources:
            try:
                self.boto3_client.delete_db_instance(
                    DBInstanceIdentifier=instance["DBInstanceIdentifier"],
                    SkipFinalSnapshot=True
                )
            except Exception as e:
                logging.error('error while deleting db instance: %s', e)
        for instance in self.untagged_resources:
            try:
                self.boto3_client.delete_db_cluster(
                    DBClusterIdentifier=instance["DBClusterIdentifier"],
                    SkipFinalSnapshot=True
                )
            except Exception as e:
                logging.error('error while deleting db cluster: %s', e)
