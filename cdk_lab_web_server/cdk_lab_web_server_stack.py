import os.path

from aws_cdk.aws_s3_assets import Asset as S3asset
from aws_cdk.aws_elasticloadbalancingv2_targets import InstanceTarget

from aws_cdk import (
    # Duration,
    Stack,
    RemovalPolicy,
    CfnOutput,
    aws_ec2 as ec2,
    aws_iam as iam,
    aws_rds as rds,
    aws_elasticloadbalancingv2 as elbv2
    # aws_sqs as sqs,
)
from constructs import Construct

dirname = os.path.dirname(__file__)

class CdkLabWebServerStack(Stack):

    def __init__(self, scope: Construct, construct_id: str, cdk_lab_vpc:ec2.IVpc, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # The code that defines your stack goes here

        # Instance role and SSM Managed Policy
        InstanceRole = iam.Role(self, "InstanceSSM", assumed_by=iam.ServicePrincipal("ec2.amazonaws.com"))

        InstanceRole.add_managed_policy(iam.ManagedPolicy.from_aws_managed_policy_name("AmazonSSMManagedInstanceCore"))

        #shared security group for both web servers
        web_sg = ec2.SecurityGroup(
            self,
            "WebServerSecurityGroup",
            vpc=cdk_lab_vpc,
            description="Security Group fro EC2 web servers",
            allow_all_outbound=True
        )

        rds_sg = ec2.SecurityGroup(
            self,
            "RDSSecurityGroup",
            vpc=cdk_lab_vpc,
            description="Security Group for RDS MySQL",
            allow_all_outbound=True
        )

        # Subnet group containing both private subnets
        rds_subnet_group = rds.SubnetGroup(
            self,
            "RDSSubnetGroup",
            description="Private subnets for MySQL RDS",
            vpc=cdk_lab_vpc,
            vpc_subnets=ec2.SubnetSelection(subnet_type=ec2.SubnetType.PRIVATE_ISOLATED)
        )

        # Allow MySQL connections only from web servers
        rds_sg.add_ingress_rule(
            web_sg,
            ec2.Port.tcp(3306),
            "Allow MySQL from EC2 web servers"
        )

        # Allow HTTP traffic from anywhere
        web_sg.add_ingress_rule(
            ec2.Peer.any_ipv4(),
            ec2.Port.tcp(80),
            "Allow HTTP traffic"
        )

        # Create an RDS MySQL instance
        mysql_db = rds.DatabaseInstance(
            self,
            "MySQLDatabase",
            engine=rds.DatabaseInstanceEngine.mysql(
                version=rds.MysqlEngineVersion.of("8.4.11", "8.4")
            ),
            vpc=cdk_lab_vpc,
            subnet_group=rds_subnet_group,
            security_groups=[rds_sg],
            instance_type=ec2.InstanceType.of(
                ec2.InstanceClass.BURSTABLE3,
                ec2.InstanceSize.MICRO
            ),
            credentials=rds.Credentials.from_generated_secret(
                "admin"
            ),
            allocated_storage=20,
            multi_az=False,
            publicly_accessible=False,
            deletion_protection=False,
            removal_policy=RemovalPolicy.DESTROY
        )

        # Create one EC2 web server in each public subnet
        web_instances = []

        for i, subnet in enumerate(cdk_lab_vpc.public_subnets):
            instance = ec2.Instance(
                self,
                f"cdk_lab_web_instance_{i+1}",
                vpc=cdk_lab_vpc,
                vpc_subnets=ec2.SubnetSelection(subnets=[subnet]),
                instance_type=ec2.InstanceType("t2.micro"),
                machine_image=ec2.AmazonLinuxImage(generation=ec2.AmazonLinuxGeneration.AMAZON_LINUX_2),
                role=InstanceRole,
                security_group=web_sg
            )

            web_instances.append(instance)

        # Script in S3 as Asset
        webinitscriptasset = S3asset(
            self,
            "Asset",
            path=os.path.join(dirname, "configure.sh")
        )

        # Configure User Data for each web server
        for instance in web_instances:
            asset_path = instance.user_data.add_s3_download_command(
                bucket=webinitscriptasset.bucket,
                bucket_key=webinitscriptasset.s3_object_key
            )

            instance.user_data.add_execute_file_command(
                file_path=asset_path
            )

            # Grant access to download the script from S3
            webinitscriptasset.grant_read(instance.role)

        # Create an internet-facing Application Load Balancer
        alb = elbv2.ApplicationLoadBalancer(
            self,
            "WebApplicationLoadBalancer",
            vpc=cdk_lab_vpc,
            internet_facing=True,
            vpc_subnets=ec2.SubnetSelection(
                subnet_type=ec2.SubnetType.PUBLIC
            )
        )

        # Allow the ALB to send HTTP traffic to the web servers
        alb.connections.security_groups[0].add_egress_rule(
            web_sg,
            ec2.Port.tcp(80),
            "Allow HTTP traffic to web servers"
        )

        # Listen for incoming HTTP requests on port 80
        listener = alb.add_listener(
            "HTTPListener",
            port=80,
            open=True
        )

        # Register both EC2 web servers as targets
        target_group = listener.add_targets(
            "WebServerTargets",
            port=80,
            targets=[
                InstanceTarget(instance, port=80)
                for instance in web_instances
            ],
            health_check=elbv2.HealthCheck(
                path="/",
                port="80",
                healthy_http_codes="200"
            )
        )

        # Output the ALB URL after deployment
        CfnOutput(
            self,
            "LoadBalancerURL",
            value=f"http://{alb.load_balancer_dns_name}",
            description="URL for the CDK web application"
        )