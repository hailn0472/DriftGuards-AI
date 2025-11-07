# Docker Commands - Pulumi EC2

## Build Image

```bash
docker build -t pulumi-ec2:latest .
```

## Run Commands

### Deploy EC2 (Create & SSH)

**Bash/Linux/macOS:**
```bash
docker run -it --rm \
  -e AWS_ACCESS_KEY_ID=AKIA57ZRLRMGYZOXCXHW \
  -e AWS_SECRET_ACCESS_KEY=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 \
  -e AWS_REGION=ap-southeast-1 \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest
```

**PowerShell (Windows):**
```powershell
docker run -it --rm `
  -e AWS_ACCESS_KEY_ID=AKIA57ZRLRMGYZOXCXHW `
  -e AWS_SECRET_ACCESS_KEY=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 `
  -e AWS_REGION=ap-southeast-1 `
  -v "${PWD}:/pulumi-project" `
  pulumi-ec2:latest
```

### Destroy Infrastructure

**Bash/Linux/macOS:**
```bash
docker run -it --rm \
  -e AWS_ACCESS_KEY_ID=AKIAQ3XLP23PPCOAVCWG \
  -e AWS_SECRET_ACCESS_KEY=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 \
  -e AWS_REGION=ap-southeast-1 \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  pulumi-ec2-down --yes
```

**PowerShell (Windows):**
```powershell
docker run -it --rm `
  -e AWS_ACCESS_KEY_ID=AKIAQ3XLP23PPCOAVCWG `
  -e AWS_SECRET_ACCESS_KEY=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 `
  -e AWS_REGION=ap-southeast-1 `
  -v "${PWD}:/pulumi-project" `
  pulumi-ec2:latest `
  pulumi-ec2-down --yes
```

### View Stack Output

**Bash/Linux/macOS:**
```bash
docker run -it --rm \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  bash -c "cd /pulumi-project && pulumi stack output"
```

**PowerShell (Windows):**
```powershell
docker run -it --rm `
  -v "${PWD}:/pulumi-project" `
  pulumi-ec2:latest `
  bash -c "cd /pulumi-project && pulumi stack output"
```

### List Stacks

**Bash/Linux/macOS:**
```bash
docker run -it --rm \
  -v $(pwd):/pulumi-project \
  pulumi-ec2:latest \
  bash -c "cd /pulumi-project && pulumi stack ls"
```

**PowerShell (Windows):**
```powershell
docker run -it --rm `
  -v "${PWD}:/pulumi-project" `
  pulumi-ec2:latest `
  bash -c "cd /pulumi-project && pulumi stack ls"
```
