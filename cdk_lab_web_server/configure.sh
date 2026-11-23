#!/bin/sh
set -e
# Use this to install software packages
# This script is for EC2 userdata. All commands are executed as administrators. 
yum update -y
amazon-linux-extras install -y mariadb10.5
amazon-linux-extras install -y php8.2
yum install -y httpd

# Create a test homepage
echo "<h1>CDK Web Server Running</h1>" > /var/www/html/index.html

systemctl start httpd
systemctl enable httpd