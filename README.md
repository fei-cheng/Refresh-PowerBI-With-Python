# Refresh-PowerBI-With-Python

The code provides 2 ways to refresh a PowerBI dataset programmatically:
- User account
- Service principal(Azure)

We would recommend the service principal solution because the password might be changed, and the user might leave the company in the future. We shouldn't bind the refresh code to a real user account.
