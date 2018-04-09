Tools for exporting wazo configuration and reimporting in another wazo

# Usage

## Exporting

On the original Wazo, create a web-service user with the following credentials:

username: export
password: export123
acl: confd.#

Export all objects:

```sh
./export.py > wazo.data
```

## Importing

On the new Wazo, create a web-service user with the following credentials:

username: import
password: import123
acl: confd.#

Create the required voicemail timezone in voicemail general.

Install all used provisioning plugins

```sh
cat wazo.data | jq '.devices.items[] | .plugin' | sort -u
```

Take a snapshot before importing

Import all data.

```sh
./import.py wazo.data
```

Import other custom sql scripts

```sh
sudo -u postgres psql asterisk < <script_name.sql>
```

Restart all Wazo services

```sh
wazo-service restart all
```
