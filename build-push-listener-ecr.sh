#!/usr/bin/env bash

# Change to your local profile
AWS_PROFILE="goodit"

echo "=== Building Patron docker image"
docker build -t patron-arby .

echo "=== Tagging docker image with AWS ECR tag"
docker tag patron-arby:latest 446899667593.dkr.ecr.us-east-1.amazonaws.com/patron-arby:latest

echo "=== Getting aws temporary login token"
aws --profile ${AWS_PROFILE} ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin 446899667593.dkr.ecr.us-east-1.amazonaws.com

echo "=== Pushing docker image to ECR"
docker push 446899667593.dkr.ecr.us-east-1.amazonaws.com/patron-arby:latest

echo "=== Done"
