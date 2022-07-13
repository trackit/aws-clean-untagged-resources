import boto3
import slack
import utils


class RDSService:
    def __init__(self, tag_key, tag_value, lifetime_tag_key, behavior, logger):
        self.slack_service: slack.Slack = slack.Slack.get_instance()
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.boto3_client = None
        self.boto3_resource = None
        self.untagged_resources = []
        self.lifetime_tagged_resources = []
        self.behavior = behavior
        self.logger = logger

    def not_persistent_resources(self):
        if len(self.lifetime_tagged_resources) >= 1 or len(self.untagged_resources) >= 1:
            return True
        return False

    def change_region(self, region):
        self.untagged_resources = []
        self.lifetime_tagged_resources = []
        self.boto3_client = boto3.client(service_name='rds', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_notify(self, instance, region):
        result = f'*{instance["DBInstanceIdentifier"]} ({instance["DbiResourceId"]})*\n'
        result += f':birthday: *Launch date* {str(instance["InstanceCreateTime"])}\n' \
            f':wrench: *Engine* {instance["Engine"]}\n'
        expired_str = ':warning: No Tag Provided, Expired Resource'
        if instance["TagList"]:
            for tag in instance["TagList"]:
                result += f':label: `{tag["Key"]}` = `{tag["Value"]}`\n'
                if tag["Key"] == self.lifetime_tag_key:
                    expired_date = utils.get_expired_date(tag["Value"], instance["InstanceCreateTime"])
                    if not expired_date:
                        expired_str = ':warning: Bad Tag Value Provided'
                    elif utils.is_expired_date(expired_date):
                        expired_str = f'{str(expired_date)}\n:warning: Expired Resource'
                    else:
                        expired_str = str(expired_date)
        result += f':skull_and_crossbones: *Expiration date* {str(expired_str)}\n'
        url = f'https://{region}.console.aws.amazon.com/rds/home?region={region}#databases:'
        return {
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
        }

    def generate_text_stop(self, instance):
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'*{instance["DBInstanceIdentifier"]} ({instance["DbiResourceId"]})* has been stopped.'
            }
        }

    def generate_text_terminate(self, instance):
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f'*{instance["DBInstanceIdentifier"]} ({instance["DbiResourceId"]})*'
                        f'has been terminated as long as its cluster.'
            }
        }

    def generate_text_element_rds(self, instance, region, notification_type):
        if notification_type == 'notify':
            return self.generate_text_notify(instance, region)
        elif notification_type == 'stop':
            return self.generate_text_stop(instance)
        elif notification_type == 'terminate':
            return self.generate_text_terminate(instance)
        else:
            return

    def resources_loop(self, region):
        n = 0

        # self.slack_service.section_header_text('RDS')
        rds_block = slack.section_header_text_fmt('RDS')

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
                    if tag["Key"] == self.lifetime_tag_key:
                        if not utils.check_tag_expired(tag["Value"], instance["InstanceCreateTime"]):
                            has_lifetime_tag = True
                            break

            if not has_tag:
                if has_lifetime_tag:
                    self.lifetime_tagged_resources.append(instance)
                    rds_block.append(self.generate_text_element_rds(instance, region, "notify"))
                else:
                    self.untagged_resources.append(instance)
                    rds_block.append(self.generate_text_element_rds(instance, region, self.behavior))
                rds_block.append({
                    'type': 'divider'
                })
                n += 1

        # if n == 0:
        #     self.slack_service.no_resources_text()
        if n > 0:
            self.slack_service.extend_blocks(rds_block)
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
                self.logger.error('error while deleting db instance: %s', e)
        for instance in self.untagged_resources:
            try:
                self.boto3_client.delete_db_cluster(
                    DBClusterIdentifier=instance["DBClusterIdentifier"],
                    SkipFinalSnapshot=True
                )
            except Exception as e:
                self.logger.error('error while deleting db cluster: %s', e)
