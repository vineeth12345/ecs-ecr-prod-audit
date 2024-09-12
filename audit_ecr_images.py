import boto3
import datetime


def get_ecs_services(cluster_name, region):
    ecs_client = boto3.client('ecs', region_name=region)
    services = ecs_client.list_services(cluster=cluster_name)['serviceArns']
    return services


def get_task_definition(service_arn, region):
    ecs_client = boto3.client('ecs', region_name=region)
    task_definition_arn = ecs_client.describe_services(services=[service_arn])[
        'services'][0]['taskDefinition']
    task_definition = ecs_client.describe_task_definition(
        taskDefinition=task_definition_arn)['taskDefinition']
    return task_definition


def get_image_details(task_definition):
    container_definitions = task_definition['containerDefinitions']
    images = []
    for container in container_definitions:
        image = container['image']
        images.append(image)
    return images


def get_image_creation_date(image, region):
    ecr_client = boto3.client('ecr', region_name=region)
    repository_name, image_tag = image.split(':')
    image_details = ecr_client.describe_images(repositoryName=repository_name, imageIds=[
                                               {'imageTag': image_tag}])['imageDetails'][0]
    creation_date = image_details['imagePushedAt']
    return creation_date


def get_owning_team(service_arn, region):
    ecs_client = boto3.client('ecs', region_name=region)
    tags = ecs_client.list_tags_for_resource(resourceArn=service_arn)['tags']
    for tag in tags:
        if tag['key'] == 'Team':
            return tag['value']
    return 'Unknown'


def get_image_status(image, cluster_name, region):
    if 'linux' in cluster_name.lower():
        inspector_client = boto3.client('inspector', region_name=region)
        findings = inspector_client.list_findings()['findings']
        for finding in findings:
            if finding['severity'] in ['HIGH', 'CRITICAL']:
                return '❌'
        return '✅'
    else:
        creation_date = get_image_creation_date(image, region)
        if (datetime.datetime.now() - creation_date).days > 90:
            return '❌'
        return '✅'


def generate_markdown_table(cluster_name, services, region):
    table = f"### {cluster_name} Images\n\n"
    table += "| Image Name | Image Creation Date | ECS Service | Owning Team | Status |\n"
    table += "|------------|---------------------|-------------|-------------|--------|\n"
    for service in services:
        task_definition = get_task_definition(service, region)
        images = get_image_details(task_definition)
        for image in images:
            creation_date = get_image_creation_date(image, region)
            owning_team = get_owning_team(service, region)
            status = get_image_status(image, cluster_name, region)
            table += f"| {image} | {creation_date} | {service} | {owning_team} | {status} |\n"
    return table


def main():
    clusters = ['Test-Cluster']
    region = 'us-east-1'  # Specify your AWS region here
    summary = "# ECR Image Audit Report\n\n"
    for cluster in clusters:
        services = get_ecs_services(cluster, region)
        summary += generate_markdown_table(cluster, services, region)
    print(summary)


if __name__ == "__main__":
    main()
