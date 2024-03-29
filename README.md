wazo-export-import is a collection of tools to allow an administrator to generate a dump file
that can be used to populate a Wazo tenant.

# Installation

```shell
apt install python3-pip
pip3 install -r requirements.txt
python3 setup.py install
```

On Wazo Platform <= 23.05 (Debian 10 Buster):

```shell
apt install python3-pip
pip3 install -r <(sed s/master/wazo-23.05/ requirements.txt)
python3 setup.py install
```

# Process

The first step is to generate an import file using an existing configuration or generating an empty dump file and filling it manually.

The dump file can the be edited using a spread sheet application. The email field should be filled on users.

A new tenant needs to be created before the import. The 3 common contexts, internal, from-extern and to-extern should be created with the appropriate number ranges.

You can then install the phone provisioning plugins that are going to be used.

Once the import has been completed phones will still have there old configuration files but Wazo will need to set the relation between lines and devices. This should be done using the provisioning code on the phones.


# The Dump File

The dump file is a .ods file that can be read by `wazo-import-dump` to create multiple resources.

The dump file contains many tabs for each resources.

# Tools

## wazo-generate-dump

This tool is used to build the dump file, it can add data to an exising file or generate a new file.

### Generating an empty dump file

To generate a new empty file that can be used to fill the blanks to build a complete configuration
can be done with the `new` command

```sh
wazo-generate-dump new <filename.ods>
```

This will generate a valid ods file that can be imported in a spreadsheet program and modified to
your needs. It can also be used to add data using other commands.

### Listing resources

The dump file is made of many resources. Each resource is a separate tab in the ods file. To view a
list of supported resources use the following command

```sh
wazo-generate-dump list resources
```

### Listing fields

Each resources support a number of fields. To view which fields are available to a given resource use
the following command.

```sh
wazo-generate-dump list fields --<resource>
```

Given the resource `users` you will get a list of all fields that can be specified on a user.

### Exporting resources

Exporting resources is the main job of `wazo-generate-dump`. It can add resources that are piped in
to a dump file.

```sh
wazo-generate-dump add --users <filename.odf> < cat user.csv
```

This will do many things. First if the .ods file does not exist it will get created. Then the
users in the user.csv files will be added to the "users" tab of the .ods file matching the headers
in the first row of the CSV file.

If a resource being imported already exists in the file it will be replaced by the new one.

Unknown columns in the CSV file will stop the import with an error message


## wazo-import-dump

Once you have a complete dump file you can import it into a stack using `wazo-import-dump`

```sh
wazo-import-dump import --username <username> --password <password> --tenant <tenant-uuid> dump_file.ods
```
