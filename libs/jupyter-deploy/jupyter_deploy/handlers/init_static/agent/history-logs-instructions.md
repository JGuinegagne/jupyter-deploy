```bash
# View the latest config command output
jd history show config

# View the second-to-latest up command output
jd history show up -n 1

# View specific lines from the output (e.g., lines 100-200 of the latest up run)
jd history show up -l 100 -s 100

### View available config command outputs
jd history list config
```
