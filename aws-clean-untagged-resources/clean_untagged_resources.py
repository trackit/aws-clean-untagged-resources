import logging
import os
import slack
from ec2 import EC2Service
from rds import RDSService

SLACK_WEBHOOK_URL = os.environ["SLACK_WEBHOOK_URL"]
TAG_KEY = os.environ["TAG_KEY"]
TAG_VALUE = os.environ["TAG_VALUE"]
BEHAVIOR = os.environ["BEHAVIOR"]
MESSAGE = os.environ["MESSAGE"]
REGION = os.environ["REGION"]
REGIONS = os.environ["REGIONS"]
LIFETIME_TAG_KEY = os.environ["LIFETIME_TAG_KEY"]


class AWSTerminator:
    def __init__(self, webhook_url, regions, message, tag_key, tag_value, lifetime_tag_key, behavior_type):
        self.regions = regions
        self.behavior_type = behavior_type
        self.slack_service = slack.Slack.get_instance(webhook_url, message, tag_key, tag_value, lifetime_tag_key)
        self.ec2_service = EC2Service(tag_key, tag_value, lifetime_tag_key)
        self.rds_service = RDSService(tag_key, tag_value, lifetime_tag_key)

    def process(self):
        logging.info('Processing AWSTerminator...')
        for region in self.regions:
            logging.info('Processing AWSTerminator for %s...', region)
            self.slack_service.intro_text(region)

            self.ec2_service.set_boto3(region)
            self.rds_service.set_boto3(region)

            self.ec2_service.resources_loop(region)
            self.rds_service.resources_loop(region)

            self.slack_service.outro_text()
            self.behavior()
            self.slack_service.clean_blocks()
            logging.info('Process Done for %s.\n', region)

    def behavior(self):
        logging.info('Processing behavior %s...', self.behavior_type)
        if self.behavior_type == 'notify':
            self.slack_service.request()
        elif self.behavior_type == 'stop':
            self.ec2_service.stop_untagged_resources()
            self.rds_service.stop_untagged_resources()
        elif self.behavior_type == 'terminate':
            logging.info('%s behavior not implemented.', self.behavior_type)
        else:
            logging.info('%s behavior does not exist.', self.behavior_type)


def lambda_handler(event, context):
    regions = REGIONS.split(',')
    logging.basicConfig(format='%(asctime)s %(message)s', datefmt='[%I:%M:%S %p]', level=logging.INFO)

    terminator = AWSTerminator(SLACK_WEBHOOK_URL, regions, MESSAGE, TAG_KEY, TAG_VALUE, LIFETIME_TAG_KEY, BEHAVIOR)
    terminator.process()
