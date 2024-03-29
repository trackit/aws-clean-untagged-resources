import boto3
import slack
import utils


class ECSService:
    def __init__(self, tag_key, tag_value, lifetime_tag_key, behavior, logger):
        self.slack_service: slack.Slack = slack.Slack.get_instance()
        self.tag_key = tag_key
        self.tag_value = tag_value
        self.lifetime_tag_key = lifetime_tag_key
        self.boto3_client = None
        self.untagged_resources = []
        self.lifetime_tagged_resources = []
        self.untagged_clusters = []
        self.lifetime_tagged_clusters = []
        self.behavior = behavior
        self.logger = logger

    def not_persistent_resources(self):
        if len(self.lifetime_tagged_resources) >= 1\
                or len(self.untagged_resources) >= 1\
                or len(self.untagged_clusters) >= 1:
            return True
        return False

    def change_region(self, region):
        self.untagged_resources = []
        self.untagged_clusters = []
        self.lifetime_tagged_resources = []
        self.boto3_client = boto3.client(service_name='ecs', region_name=region)

    def get_boto3_client(self):
        return self.boto3_client

    def generate_text_notify(self, task, task_name, region):
        result = ':pushpin: *Fargate Task:*\n'
        result += f'*{task["taskArn"]} ({task_name})*\n*Cluster Arn:* {task["clusterArn"]}\n'
        result += f':birthday: *Created at* {str(task["createdAt"])}\n'
        expired_str = ':warning: No Tag Provided, Expired Resource'
        if task["tags"]:
            for tag in task["tags"]:
                result += f':label: `{tag["key"]}` = `{tag["value"]}`\n'
                if tag["key"] == self.lifetime_tag_key:
                    expired_date = utils.get_expired_date(tag["value"], task["createdAt"])
                    if not expired_date:
                        expired_str = ':warning: Bad Tag value Provided'
                    elif utils.is_expired_date(expired_date):
                        expired_str = f'{str(expired_date)}\n:warning: Expired Resource'
                    else:
                        expired_str = str(expired_date)
        result += f':skull_and_crossbones: *Expiration date* {str(expired_str)}\n'
        cluster_name = 'Unknown'
        task_id = 'Unknown'
        try:
            split_arn = str(task["clusterArn"]).split('/')
            cluster_name = split_arn[len(split_arn) - 1]
            split_arn = str(task["taskArn"]).split('/')
            task_id = split_arn[len(split_arn) - 1]
        except Exception as e:
            self.logger.error('error while retrieving cluster name & task id: %s', e)
        url = f'https://{region}.console.aws.amazon.com/ecs/home?region={region}#/clusters/{cluster_name}/tasks/{task_id}'
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
                    'text': 'Manage it on ECS console',
                },
                'value': 'click_me_123',
                'url': url,
                'action_id': 'button-action'
            }
        }

    def generate_text_stop(self, task, task_name):
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':warning: *{str(task["taskArn"])} ({task_name})* has been stopped.'
            }
        }

    def generate_text_terminate(self, task, task_name):
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':rotating_light: Fargate task *{str(task["taskArn"])} ({task_name})* has been terminated.'
            }
        }

    def generate_text_element(self, task, task_name, region, notification_type):
        if notification_type == 'notify':
            return self.generate_text_notify(task, task_name, region)
        elif notification_type == 'stop':
            return self.generate_text_stop(task, task_name)
        elif notification_type == 'terminate':
            return self.generate_text_terminate(task, task_name)
        else:
            return

    def generate_cluster_text_notify(self, cluster, region):
        result = f':pushpin: *Cluster:*\n*{cluster["clusterArn"]} ({cluster["clusterName"]})*\n'
        expired_str = ':warning: No Tag Provided, Expired Resource'
        if cluster["tags"]:
            for tag in cluster["tags"]:
                result += f':label: `{tag["key"]}` = `{tag["value"]}`\n'
                if tag["key"] == self.lifetime_tag_key:
                    expired_date = utils.get_expired_date(tag["value"], None)
                    if not expired_date:
                        expired_str = ':warning: Bad Tag value Provided'
                    elif utils.is_expired_date(expired_date):
                        expired_str = f'{str(expired_date)}\n:warning: Expired Resource'
                    else:
                        expired_str = str(expired_date)
        result += f':skull_and_crossbones: *Expiration date* {str(expired_str)}\n'
        url = f'https://{region}.console.aws.amazon.com/ecs/home?region={region}#/clusters/{cluster["clusterName"]}'
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
                    'text': 'Manage it on ECS console',
                },
                'value': 'click_me_123',
                'url': url,
                'action_id': 'button-action'
            }
        }

    def generate_cluster_text_terminate(self, cluster):
        return {
            'type': 'section',
            'text': {
                'type': 'mrkdwn',
                'text': f':rotating_light: Cluster *{str(cluster["clusterArn"])} ({cluster["clusterName"]})* '
                        f'has been deleted.'
            }
        }

    def generate_cluster_text(self, cluster, region, notification_type):
        if notification_type == 'notify':
            return self.generate_cluster_text_notify(cluster, region)
        elif notification_type == 'terminate':
            return self.generate_cluster_text_terminate(cluster)
        else:
            return

    def tasks_loop(self, tasks, region):
        tasks_block = []

        for task in tasks["tasks"]:
            has_tag = False
            has_lifetime_tag = False
            task_name = 'Unknown'
            if task["tags"]:
                for tag in task["tags"]:
                    if tag["key"] == "Name":
                        task_name = tag["value"]
                    if tag["key"] == self.tag_key and tag["value"] == self.tag_value:
                        has_tag = True
                        break
                    if tag["key"] == self.lifetime_tag_key:
                        if not utils.check_tag_expired(tag["value"], task["createdAt"]):
                            has_lifetime_tag = True
                            break
                if not has_tag:
                    if has_lifetime_tag:
                        self.lifetime_tagged_resources.append(task)
                        tasks_block.append(self.generate_text_element(task, task_name, region, 'notify'))
                    else:
                        self.untagged_resources.append(task)
                        tasks_block.append(self.generate_text_element(task, task_name, region, self.behavior))
                    tasks_block.append({
                        'type': 'divider'
                    })

        return tasks_block

    def cluster_element(self, cluster, region):
        cluster_block = []

        has_tag = False
        has_lifetime_tag = False
        if cluster["tags"]:
            for tag in cluster["tags"]:
                if tag["key"] == self.tag_key and tag["value"] == self.tag_value:
                    has_tag = True
                    break
                if tag["key"] == self.lifetime_tag_key:
                    if not utils.check_tag_expired(tag["value"], None):
                        has_lifetime_tag = True
                        break
        if not has_tag:
            if has_lifetime_tag:
                self.lifetime_tagged_clusters.append(cluster)
                cluster_block.append(self.generate_cluster_text(cluster, region, 'notify'))
            else:
                self.untagged_clusters.append(cluster)
                cluster_block.append(self.generate_cluster_text(cluster, region, self.behavior))
            cluster_block.append({
                'type': 'divider'
            })
        return cluster_block

    def resources_loop(self, region):
        ecs_block = slack.section_header_text_fmt('ECS')

        clusters = self.boto3_client.list_clusters()
        clusters = self.boto3_client.describe_clusters(
            clusters=clusters["clusterArns"],
            include=["TAGS"]
        )
        for cluster in clusters["clusters"]:
            if self.behavior != 'stop':
                ecs_block.extend(self.cluster_element(cluster, region))
            if self.behavior != 'terminate':
                task_list = self.boto3_client.list_tasks(
                    cluster=cluster["clusterArn"],
                    launchType='FARGATE',
                    desiredStatus='RUNNING'
                )
                if task_list and len(task_list["taskArns"]) > 0:
                    tasks = self.boto3_client.describe_tasks(
                        cluster=cluster["clusterArn"],
                        tasks=task_list["taskArns"],
                        include=["TAGS"]
                    )
                    ecs_block.extend(self.tasks_loop(tasks, region))

        if len(self.untagged_resources) <= 0 and len(self.lifetime_tagged_resources) <= 0 \
                and len(self.untagged_clusters) <= 0:
            self.slack_service.no_resources_text()
        if len(self.untagged_resources) >= 0 or len(self.lifetime_tagged_resources) >= 0 \
                or len(self.untagged_clusters) >= 0:
            self.slack_service.extend_blocks(ecs_block)
        return self.untagged_resources

    def get_untagged_resources(self):
        return self.untagged_resources

    def get_lifetime_tagged_resources(self):
        return self.lifetime_tagged_resources

    def stop_untagged_resources(self):
        if len(self.untagged_resources) > 0:
            for task in self.untagged_resources:
                try:
                    self.boto3_client.stop_task(
                        cluster=task["clusterArn"],
                        task=task["taskArn"],
                        reason='Not persistent task'
                    )
                except Exception as e:
                    self.logger.error('error while stopping ecs instance: %s', e)
            self.logger.info('Fargate Stop Not Implemented')

    def terminate_untagged_resources(self):
        if len(self.untagged_clusters) > 0:
            for cluster in self.untagged_clusters:
                self.boto3_client.delete_cluster(
                    cluster=cluster["clusterArn"]
                )
            self.logger.info('Fargate Terminate Not Implemented')
