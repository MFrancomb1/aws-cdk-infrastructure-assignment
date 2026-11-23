# AWS CDK Infrastructure Homework

This project uses the AWS Cloud Development Kit (CDK) with Python to deploy a web application infrastructure on AWS.

The infrastructure is organized into two CloudFormation stacks:

**1. CdkLabNetworkStack**
- Creates a VPC with a `10.0.0.0/16` CIDR.
- Creates two public subnets and two private isolated subnets across two Availability Zones.
- Configures an Internet Gateway and routing for the public subnets.

**2. CdkLabWebServerStack**
- Deploys two EC2 web servers, one in each public subnet.
- Installs and configures Apache HTTP Server through an EC2 User Data script.
- Creates an RDS MySQL database using both private subnets in its DB subnet group.
- Configures security groups to permit HTTP traffic on port 80 and restrict MySQL port 3306 to the web servers.
- Creates an internet-facing Application Load Balancer (ALB) with both EC2 instances registered as targets.

## Deployment

The infrastructure was deployed in AWS region `us-east-1` using:

```bash
cdk deploy --all
```

## Implementation Verification

The implementation was verified using the AWS CLI and HTTP requests.

### 1. Website and Load Balancer

The deployed website was accessed through the Application Load Balancer using `curl -i`.

**Output:**

```text
HTTP/1.1 200 OK
Server: Apache/2.4.71 ()

<h1>CDK Web Server Running</h1>
```

The successful HTTP 200 response confirmed that the ALB forwarded requests to a functioning Apache web server.

The ALB target group was also verified using:

```bash
aws elbv2 describe-target-health --target-group-arn <target-group-arn>
```

**Result:** Both EC2 instances were registered as targets and reported `healthy`.

### 2. EC2 Instances and Subnets

The EC2 instances were verified using the AWS CLI.

| Instance ID | Availability Zone | Subnet | State |
|---|---|---|---|
| `i-07434990a79e9b51a` | us-east-1a | subnet-02981e78025d7a1b8 | running |
| `i-0f4d3bb932c8c62d8` | us-east-1b | subnet-0d0c1f1e1014103f6 | running |

**Result:** Two EC2 web servers were running in separate public subnets across two Availability Zones.

### 3. RDS MySQL Database

The database was verified using:

```bash
aws rds describe-db-instances
```

**Results:**

| Property | Value |
|---|---|
| Engine | MySQL |
| Version | 8.4.11 |
| Status | available |
| Publicly Accessible | False |

The DB subnet group was verified to contain both private subnets:

| Private Subnet | Availability Zone | Status |
|---|---|---|
| subnet-07d64667f35e30442 | us-east-1a | Active |
| subnet-0f91e19dd1230ccd4 | us-east-1b | Active |

**Result:** The RDS database was successfully deployed with a subnet group containing both private subnets.

### 4. Security Groups

Security group inbound rules were verified using `aws ec2 describe-security-groups`.

| Security Group | Inbound Rule | Source |
|---|---|---|
| Application Load Balancer | TCP 80 | 0.0.0.0/0 |
| EC2 Web Servers | TCP 80 | 0.0.0.0/0 |
| RDS MySQL | TCP 3306 | Web Server Security Group |

**Result:** HTTP traffic was permitted as required, while database access was restricted to the web server security group.

## Resource Cleanup

After completing verification, both stacks were destroyed using:

```bash
cdk destroy --all
```

**Output:**

```text
✅ CdkLabWebServerStack: destroyed
✅ CdkLabNetworkStack: destroyed
```

Checks in the AWS management console confirmed that no resources remained in the assignment VPC.
