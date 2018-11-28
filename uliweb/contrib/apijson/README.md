

# Introduction

uliweb.contrib.apijson is a subset and slightly different variation of [apijson](https://github.com/TommyLemon/APIJSON/blob/master/Document.md)

# uliweb model configuration

## example

```
[APIJSON_MODEL_CONFIG]
user = {
    "public" : False,
    "user_id_field" : "id",
    "secret_fields" : ["password"],
    "default_filter_by_self" : True
}
```

## document

settings.APIJSON_MODEL_CONFIG.[MODEL_NAME]

| Field                  | Doc                                                          |
| ---------------------- | ------------------------------------------------------------ |
| public                 | Default to be "False".<br />If not public, should be **login user** and only can see **user own data**. |
| user_id_field          | Field name of user id, related to query user own data.       |
| secret_fields          | Secret fields won't be exposed.                              |
| default_filter_by_self | If True, when no filter parameter, will filter by self user id |

# Supported API Examples

### Single record query: with id as parameter

Request:

```
{
   "user":{
     "id":1
   }
}
```

Response

```
{
    "code": 200,
    "msg": "success",
    "user": {
        "username": "zhangcl",
        "nickname": "Chunlin Zhang",
        "email": "zhangcl@localhost",
        "is_superuser": true,
        "last_login": "2018-11-12 17:35:23",
        "date_join": "2018-08-23 14:48:54",
        "image": "portraits/1.tmp.jpg",
        "active": false,
        "locked": false,
        "deleted": false,
        "auth_type": "default",
        "id": 1
    }
}
```

### Single record query: no parameter

Request:

```
{
   "user":{
   }
}
```

Response

```
{
    "code": 200,
    "msg": "success",
    "user": {
        "username": "zhangcl",
        "nickname": "Chunlin Zhang",
        "email": "zhangcl@localhost",
        "is_superuser": true,
        "last_login": "2018-11-12 17:35:23",
        "date_join": "2018-08-23 14:48:54",
        "image": "portraits/1.tmp.jpg",
        "active": false,
        "locked": false,
        "deleted": false,
        "auth_type": "default",
        "id": 1
    }
}
```

### Single record query: @column

Request:

```
{
   "user":{
     "@column": "id,username,email"
   }
}
```

Response

```
{
    "code": 200,
    "msg": "success",
    "user": {
        "username": "zhangcl",
        "email": "zhangcl@localhost",
        "id": 1
    }
}
```
