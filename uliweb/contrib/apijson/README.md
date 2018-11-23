

# uliweb model configuration

## example

```
[APIJSON_MODEL_CONFIG]
user = {
    "user_id_field" : "id",
    "secret_fields" : ["password"]
}
```

## document

| Field         | Doc                                                          |
| ------------- | ------------------------------------------------------------ |
| public        | Default to be "False".<br />If not public, should be **login user** and only can see **user own data**. |
| user_id_field | Field name of user id, related to query user own data.       |
| secret_fields | Secret fields won't be exposed.                              |

