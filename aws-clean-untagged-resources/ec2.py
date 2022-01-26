import boto3
import slack
from datetime import timedelta, datetime
import pytz


class EC2Service:
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

    def set_boto3(self, region):
        self.boto3_client = boto3.client(service_name='ec2', region_name=region)
        self.boto3_resource = boto3.resource(service_name='ec2', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_notify(self, instance, instance_name, region):
        result = f'*{str(instance.id)} ({instance_name})*\n'
        result += f':birthday: *Launch date* {str(instance.launch_time)}\n:key: *Keypair Name* {instance.key_name}\n'
        expired_date = 'No Tag Provided'
        if instance.tags:
            for tag in instance.tags:
                result += f':label: `{tag["Key"]}` = `{tag["Value"]}`\n'
                if tag["Key"] == self.lifetime_tag_key:
                    expired_date = instance.launch_time + timedelta(int(tag["Value"]))
                    if (instance.launch_time + timedelta(int(tag["Value"]))) < pytz.utc.localize(datetime.now()):
                        expired_date = f'{str(expired_date)}\n:warning: Expired Resource'
        result += f':skull_and_crossbones: *Expiration date* {str(expired_date)}\n'
        url = f'https://{region}.console.aws.amazon.com/ec2/v2/home?region={region}#InstanceDetails:instanceId=' \
              f'{str(instance.id)}'
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
                    'text': 'Manage it on EC2 console',
                },
                'value': 'click_me_123',
                'url': url,
                'action_id': 'button-action'
            }
        })

    def generate_text_stop(self, instance, instance_name):
        self.slack_service.append_blocks({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':warning: *{str(instance.id)} ({instance_name})* has been stopped.'
            }
        })

    def generate_text_terminate(self, instance, instance_name):
        self.slack_service.append_blocks({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':rotating_light: *{str(instance.id)} ({instance_name})* has been terminated.'
            }
        })

    def generate_text_element_ec2(self, instance, instance_name, region):
        if self.behavior == 'notify':
            self.generate_text_notify(instance, instance_name, region)
        elif self.behavior == 'stop':
            self.generate_text_stop(instance, instance_name)
        elif self.behavior == 'terminate':
            self.generate_text_terminate(instance, instance_name)
        else:
            return
        self.slack_service.append_blocks({
            'type': 'divider'
        })

    def resources_loop(self, region):
        n = 0

        self.slack_service.section_header_text('EC2')

        for instance in self.boto3_resource.instances.all():
            instance_name = 'Unknown'
            has_tag = False
            has_lifetime_tag = False
            if instance.tags:
                for tag in instance.tags:
                    if tag["Key"] == 'Name':
                        instance_name = tag["Value"]
                    if tag["Key"] == self.tag_key and tag["Value"] == self.tag_value:
                        has_tag = True
                        break
                    if tag["Key"] == self.lifetime_tag_key and \
                            (instance.launch_time + timedelta(int(tag["Value"]))) > pytz.utc.localize(datetime.now()):
                        has_lifetime_tag = True
                        break
            if not has_tag:
                if has_lifetime_tag:
                    self.lifetime_tagged_resources.append(instance.id)
                else:
                    self.untagged_resources.append(instance.id)
                self.generate_text_element_ec2(instance, instance_name, region)
                n += 1

        if n == 0:
            self.slack_service.no_resources_text()
        return self.untagged_resources

    def get_untagged_resources(self):
        return self.untagged_resources

    def get_lifetime_tagged_resources(self):
        return self.lifetime_tagged_resources

    def stop_untagged_resources(self):
        if len(self.untagged_resources) > 0:
            self.boto3_client.stop_instances(InstanceIds=self.untagged_resources)

    def terminate_untagged_resources(self):
        if len(self.untagged_resources) > 0:
            try:
                self.boto3_client.terminate_instances(InstanceIds=self.untagged_resources)
            except Exception as e:
                self.logger.error('error while terminating EC2 instances: %s', e)
