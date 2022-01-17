import boto3
import json
import logging
import os
import urllib.request

# ec2 = boto3.resource('ec2')
# rds = boto3.client('rds')
# ec2_client = boto3.client('ec2')
text = {"blocks": []}

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
TAG_KEY = os.environ['TAG_KEY']
TAG_VALUE = os.environ['TAG_VALUE']
BEHAVIOR = os.environ['BEHAVIOR']
MESSAGE = os.environ['MESSAGE']
REGION = os.environ['REGION']
REGIONS = os.environ['REGIONS']


def intro_text(region):
	text['blocks'].append({
		"type": "section",
		"text": {
			"type": "mrkdwn",
			"text": ":globe_with_meridians: *" + region + "*"
		}
	})
	text['blocks'].append({
		"type": "section",
		"text": {
			"type": "mrkdwn",
			"text": MESSAGE
		}
	})


def outro_text():
	text['blocks'].append({
		"text": {
			"text": ":robot_face: *Tag your resources with `" + TAG_KEY + "=" + TAG_VALUE + "` if you want them to live!*",
			"type": "mrkdwn"
		},
		"type": "section"
	})


def no_resources_text():
	text['blocks'].append({
		"text": {
			"text": ":robot_face: No untagged resource here, good job!",
			"type": "mrkdwn"
		},
		"type": "section"
	})


def section_header_text(name):
	text['blocks'].append({
		"type": "header",
		"text": {
			"type": "plain_text",
			"text": name
		}
	})
	text['blocks'].append({
		"type": "divider"
	})


def generate_text_element_ec2(instance, instance_name, region):
	result = "*" + str(instance.id) + " (" + instance_name + ")*\n"
	result += ":birthday: *Launch date* " + str(instance.launch_time) + "\n:key: *Keypair Name* " + instance.key_name + "\n"
	for tag in instance.tags:
		result += ":label: `" + tag['Key'] + "` = `" + tag['Value'] + "`\n"
	url = "https://" + region + ".console.aws.amazon.com/ec2/v2/home?region=" + region + "#InstanceDetails:instanceId=" + str(instance.id)
	text['blocks'].append({
			"type": "section",
			"text": {
				"type": "mrkdwn",
				"text": result
			},
			"accessory": {
				"type": "button",
				"text": {
					"type": "plain_text",
					"text": "Manage it on EC2 console",
				},
				"value": "click_me_123",
				"url": url,
				"action_id": "button-action"
			}
	})
	text['blocks'].append({
			"type": "divider"
	})


def generate_text_element_rds(instance, region):
	result = "*" + instance['DBInstanceIdentifier'] + " (" + instance['DbiResourceId'] + ")*\n"
	result += ":birthday: *Launch date* " + str(instance['InstanceCreateTime']) + "\n:wrench: *Engine* " + instance['Engine'] + "\n"
	for tag in instance['TagList']:
		result += ":label: `" + tag['Key'] + "` = `" + tag['Value'] + "`\n"
	url = "https://" + region + ".console.aws.amazon.com/rds/home?region=" + region + "#databases:"
	text['blocks'].append({
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
	text['blocks'].append({
			"type": "divider"
	})


def behavior(ec2_client, rds_client, untagged_ec2, untagged_rds):
	if BEHAVIOR == 'notify':
		req = urllib.request.Request(SLACK_WEBHOOK_URL, json.dumps(text).encode())
		urllib.request.urlopen(req)
	if BEHAVIOR == 'stop':
		ec2_client.stop_instances(InstanceIds=untagged_ec2)
		for instance in untagged_rds:
			rds_client.stop_db_instances(DBInstanceIdentifier=instance, DBSnapshotIdentifier=instance)
	if BEHAVIOR == 'terminate':
		print("nothing")


def ec2_instances_loop(ec2, region):
	untagged_ec2 = []
	n = 0

	section_header_text('EC2')

	for instance in ec2.instances.all():
		instance_name = ""
		has_tag = False
		for tag in instance.tags:
			if tag['Key'] == 'Name':
				instance_name = tag['Value']
			if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
				has_tag = True
				break
		if not has_tag:
			generate_text_element_ec2(instance, instance_name, region)
			untagged_ec2.append(instance.id)
			n += 1

	if n == 0:
		no_resources_text()
	return untagged_ec2


def rds_instances_loop(rds, region):
	untagged_rds = []
	n = 0

	section_header_text('RDS')

	instances = rds.describe_db_instances()
	for instance in instances['DBInstances']:
		has_tag = False
		for tag in instance['TagList']:
			if tag['Key'] == 'Name':
				instance_name = tag['Value']
			if tag['Key'] == TAG_KEY and tag['Value'] == TAG_VALUE:
				has_tag = True
				break

		if not has_tag:
			generate_text_element_rds(instance, region)
			untagged_rds.append(instance['DBInstanceIdentifier'])
			n += 1
	if n == 0:
		no_resources_text()
	return untagged_rds


def lambda_handler(event, context):
	regions = REGIONS.split(',')
	print(regions)
	for region in regions:
		text['blocks'] = []
		print(region)
		intro_text(region)
		ec2 = boto3.resource(service_name='ec2', region_name=region)
		ec2_client = boto3.client(service_name='ec2', region_name=region)
		rds_client = boto3.client(service_name='rds', region_name=region)
		untagged_ec2 = ec2_instances_loop(ec2, region)
		untagged_rds = rds_instances_loop(rds_client, region)
		outro_text()
		print(text)
		print(untagged_ec2)
		print(untagged_rds)
		behavior(ec2_client, rds_client, untagged_ec2, untagged_rds)
