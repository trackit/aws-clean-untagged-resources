import boto3
import slack
from datetime import timedelta, datetime
import pytz


class ECSService:
    def __init__(self, tag_key, tag_value, lifetime_tag_key, behavior, logger):
        self.slack_service: slack.Slack = slack.Slack.get_instance()
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.boto3_client = None
        self.untagged_resources = []
        self.lifetime_tagged_resources = []
        self.behavior = behavior
        self.logger = logger

    def set_boto3(self, region):
        self.boto3_client = boto3.client(service_name='ecs', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_notify(self, task, task_name, region):
        result = f'*{task["taskArn"]} ({task_name})*\n*Cluster Arn:* {task["clusterArn"]}\n'
        result += f':birthday: *Created at* {str(task["createdAt"])}\n'
        expired_date = 'No Tag Provided'
        if task["tags"]:
            for tag in task["tags"]:
                result += f':label: `{tag["key"]}` = `{tag["value"]}`\n'
                if tag["key"] == self.lifetime_tag_key:
                    expired_date = task["createdAt"] + timedelta(int(tag["value"]))
                    if (task["createdAt"] + timedelta(int(tag["value"]))) < pytz.utc.localize(datetime.now()):
                        expired_date = f'{str(expired_date)}\n:warning: Expired Resource'
        result += f':skull_and_crossbones: *Expiration date* {str(expired_date)}\n'
        cluster_name = 'Unknown'
        task_id = 'Unknown'
        try:
            split_arn = str(task["clusterArn"]).split('/')
            cluster_name = split_arn[len(split_arn) - 1]
            split_arn = str(task["taskArn"]).split('/')
            task_id = split_arn[len(split_arn) - 1]
        except Exception as e:
            self.logger.error('error while retrieving cluster name & task id: %s', e)
        url = f'https://{region}.console.aws.amazon.com/home?region={region}#/clusters/{cluster_name}/tasks/{task_id}'
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
                    'text': 'Manage it on ECS console',
                },
                'value': 'click_me_123',
                'url': url,
                'action_id': 'button-action'
            }
        })

    def generate_text_stop(self, task, task_name):
        self.slack_service.append_blocks({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':warning: *{str(task["taskArn"])} ({task_name})* has been stopped.'
            }
        })

    def generate_text_terminate(self, task, task_name):
        self.slack_service.append_blocks({
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':rotating_light: *{str(task["taskArn"])} ({task_name})* has been terminated.'
            }
        })

    def generate_text_element(self, task, task_name, region):
        if self.behavior == 'notify':
            self.generate_text_notify(task, task_name, region)
        elif self.behavior == 'stop':
            self.generate_text_stop(task, task_name)
        elif self.behavior == 'terminate':
            self.generate_text_terminate(task, task_name)
        else:
            return
        self.slack_service.append_blocks({
            'type': 'divider'
        })

    def tasks_loop(self, tasks, region):
        for task in tasks["tasks"]:
            has_tag = False
            has_lifetime_tag = False
            task_name = 'Unknown'
            if task["tags"]:
                for tag in task["tags"]:
                    print(tag)
                    if tag["key"] == "Name":
                        task_name = tag["value"]
                    if tag["key"] == self.tag_key and tag["value"] == self.tag_value:
                        has_tag = True
                    if tag["key"] == self.lifetime_tag_key and \
                            (task["createdAt"] + timedelta(int(tag["value"])) > pytz.utc.localize(datetime.now())):
                        has_lifetime_tag = True
                if not has_tag:
                    if has_lifetime_tag:
                        self.lifetime_tagged_resources.append(task)
                        if self.behavior == 'notify':
                            self.generate_text_element(task, task_name, region)
                    else:
                        self.untagged_resources.append(task)
                        self.generate_text_element(task, task_name, region)
            print(task)

    def resources_loop(self, region):
        self.slack_service.section_header_text('ECS')

        clusters = self.boto3_client.list_clusters()
        for cluster in clusters["clusterArns"]:
            task_list = self.boto3_client.list_tasks(
                cluster=cluster,
                launchType='FARGATE',
                # desiredStatus='RUNNING'
            )
            self.logger.info('tasks = %s', task_list)
            if task_list and len(task_list["taskArns"]) > 0:
                tasks = self.boto3_client.describe_tasks(
                    cluster=cluster,
                    tasks=task_list["taskArns"],
                    include=["TAGS"]
                )
                self.tasks_loop(tasks, region)

        if len(self.untagged_resources) <= 0 and len(self.lifetime_tagged_resources) <= 0:
            self.slack_service.no_resources_text()
        return self.untagged_resources

    def get_untagged_resources(self):
        return self.untagged_resources

    def get_lifetime_tagged_resources(self):
        return self.lifetime_tagged_resources

    def stop_untagged_resources(self):
        if len(self.untagged_resources) > 0:
            self.logger('Fargate Stop Not Implemented')

    def terminate_untagged_resources(self):
        if len(self.untagged_resources) > 0:
            self.logger('Fargate Terminate Not Implemented')
