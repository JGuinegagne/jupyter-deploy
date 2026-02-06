View configured variables:
```bash
# List all the variable names that this template declares
jd show --variables --list --text

# Display the current value of a specific variable
jd show -v VARNAME --text

# Display the description of a variable
jd show -v VARNAME --description --text
```

**IMPORTANT:** The value of a variable returned by `jd show` is not applied to the resources
until the `jd up` command is run.
