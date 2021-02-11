import boto3
import json
import logging
import os
from urllib2 import Request, urlopen, URLError, HTTPError

ec2 = boto3.resource('ec2')
rds = boto3.client('rds')
ec2_client = boto3.client('ec2')
text = {"blocks" : [] }

SLACK_WEBHOOK_URL = os.environ['SLACK_WEBHOOK_URL']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
TAG_KEY = os.environ['TAG_KEY']
TAG_VALUE = os.environ['TAG_VALUE']
BEHAVIOR = os.environ['BEHAVIOR']
MESSAGE = os.environ['MESSAGE']
REGION = os.environ['REGION']

def intro_text():
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

def generate_text_element_ec2(instance, instance_name):
    result = "*" + str(instance.id) + " (" + instance_name + ")*\n"
    result += ":birthday: *Launch date* " + str(instance.launch_time) + "\n:key: *Keypair Name* " + instance.key_name + "\n"
    for tag in instance.tags:
        result += ":label: `" + tag['Key'] + "` = `" + tag['Value'] + "`\n"
    url = "https://" + REGION + ".console.aws.amazon.com/ec2/v2/home?region=us-west-2#InstanceDetails:instanceId=" + str(instance.id)
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
	
def generate_text_element_rds(instance):
    result = "*" + instance['DBInstanceIdentifier'] + " (" + instance['DbiResourceId'] + ")*\n"
    result += ":birthday: *Launch date* " + str(instance['InstanceCreateTime']) + "\n:wrench: *Engine* " + instance['Engine'] + "\n"
    for tag in instance['TagList']:
        result += ":label: `" + tag['Key'] + "` = `" + tag['Value'] + "`\n"
    url = "https://" + REGION + ".console.aws.amazon.com/rds/home?region=us-west-2#databases:"
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


def behavior(untagged_ec2, untagged_rds):
	if BEHAVIOR == 'notify':
	    req = Request(SLACK_WEBHOOK_URL, json.dumps(text))
    	urlopen(req)
	if BEHAVIOR == 'stop':
		ec2_client.stop_instances(InstanceIds=untagged_ec2)
		for instance in untagged_rds:
			rds.stop_db_instances(DBInstanceIdentifier=instance,DBSnapshotIdentifier=instance)
	if BEHAVIOR == 'terminate':
		print("nothing")

def lambda_handler(event, context):
	intro_text()
	untagged_ec2 = []
	untagged_rds = []
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
			generate_text_element_ec2(instance, instance_name)
			untagged_ec2.append(instance.id)
			n += 1

	if n == 0:
		no_resources_text()

	section_header_text('RDS')

	n = 0
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
			generate_text_element_rds(instance)
			untagged_rds.append(instance['DBInstanceIdentifier'])
			n += 1    
	if n == 0:
		no_resources_text()
	outro_text()
	print(text)
	print(untagged_ec2)
	print(untagged_rds)
	behavior(untagged_ec2, untagged_rds)