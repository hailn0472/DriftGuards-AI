# Docker Commands - Pulumi EC2

## Build Image

```bash
docker build -t pulumi-ec2:latest .
```

## Run Commands

### Deploy EC2 (Create & SSH)

```bash
docker run -it --rm \
  -e AWS_ACCESS_KEY_ID=AKIAQ3XLP23PPCOAVCWG \
  -e AWS_SECRET_ACCESS_KEY=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 \
  -e AWS_REGION=ap-southeast-1 \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest
```

### Destroy Infrastructure

```bash
docker run -it --rm \
  -e AWS_ACCESS_KEY_ID=AKIAQ3XLP23PPCOAVCWG \
  -e AWS_SECRET_ACCESS_KEY=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 \
  -e AWS_REGION=ap-southeast-1 \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  pulumi-ec2-down --yes
```

### View Stack Output

```bash
docker run -it --rm \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  bash -c "cd /pulumi-project && pulumi stack output"
```

### List Stacks

```bash
docker run -it --rm \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  bash -c "cd /pulumi-project && pulumi stack ls"
```
