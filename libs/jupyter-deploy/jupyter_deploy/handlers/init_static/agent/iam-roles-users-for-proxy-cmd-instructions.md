`jd users` maps to IAM **users**; `jd teams` maps to IAM **roles** (a shared role — e.g. an SSO
permission-set role — is the identity a team assumes, and is what `GetCallerIdentity` reports). IAM
**groups** do not map to `jd teams`: a group is only a policy container for users, is never a
principal, and never appears in the caller identity. Names match case-insensitively; pass bare names,
not ARNs.

```bash
# IAM users
jd users list
jd users add alice bob
jd users remove alice

# IAM roles
jd teams list
jd teams add DataScience MLTeam
jd teams remove MLTeam
```
