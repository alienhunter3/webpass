# REST API reference

Route handlers are documented below. Each docstring leads with the HTTP method and path.

## Secrets (`/api/secret`)

::: pywebpass.api_secret
    options:
      members:
        - root_secrets
        - post_secret
        - secret_details
        - secret_update
        - secret_attachments
        - delete_secret_attachment
        - post_secret_attachment

## Groups (`/api/group`)

::: pywebpass.api_group
    options:
      members:
        - all_groups
        - group_details
        - group_secrets

## Database file (`/api/file`)

::: pywebpass.api_datafile
    options:
      members:
        - get_file
        - update_file
        - get_file_details
