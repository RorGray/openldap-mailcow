# openldap-mailcow

This is a fork of [Programmierus/ldap-mailcow](https://github.com/Programmierus/ldap-mailcow) with modifications to support connections to OpenLDAP.

## New Features in This Fork

This fork extends the original `ldap-mailcow` with the following OpenLDAP-specific enhancements:

- **Configurable User Identifier Attribute** - Use `mail` to identify users instead of the Active Directory-specific `userPrincipalName`
- **Configurable Email and Name Attributes** - Specify which LDAP attributes contain email addresses and display names
- **OpenLDAP-Compatible Authentication** - Removed dependency on Active Directory's `userAccountControl` attribute; accounts are considered active if they exist in the directory
- **Automatic DN Generation** - Auth bind DN is automatically constructed from your identifier attribute and base DN
- **Flexible LDAP Schema Support** - Works with `inetOrgPerson` and other standard OpenLDAP object classes
- **Domain Validation** - Automatically checks if mail domains exist in Mailcow before creating users, preventing sync crashes and providing helpful warnings
- **Enhanced Password Generation** - Generates secure 64-character passwords that meet all Mailcow password requirements, preventing user creation failures

## Quick Start for OpenLDAP Users

**Optional Environment Variables:**

> **Note:** For most OpenLDAP setups with standard `inetOrgPerson` schema, no environment variables are required. All values default to work with `mail` attribute for authentication.

- `OPENLDAP-MAILCOW_IDENTIFIER` - The LDAP attribute used to identify users for authentication (default: `mail`)
- `OPENLDAP-MAILCOW_AUTH_BIND_USERDN` - Custom authentication DN template (auto-generated if not specified)
- `OPENLDAP-MAILCOW_EMAIL_ATTRIBUTE` - LDAP attribute containing the email address (default: `mail`)
- `OPENLDAP-MAILCOW_NAME_ATTRIBUTE` - LDAP attribute containing the display name (default: `cn`)

---

# ldap-mailcow

Adds LDAP accounts to mailcow-dockerized and enables LDAP (e.g., Active Directory, OpenLDAP) authentication.

* [How does it work](#how-does-it-work)
* [Usage](#usage)
  * [LDAP Fine-tuning](#ldap-fine-tuning)
* [Limitations](#limitations)
  * [WebUI and EAS authentication](#webui-and-eas-authentication)
  * [Two-way sync](#two-way-sync)
* [Customizations and Integration support](#customizations-and-integration-support)

## How does it work

A python script periodically checks and creates new LDAP accounts and deactivates deleted ones with mailcow API. It also enables LDAP authentication in SOGo and dovecot.

**Important Notes:**
- For OpenLDAP, account activation status is determined by whether the account exists in the LDAP directory and matches the configured filter. If you need to disable accounts, remove them from the LDAP directory or exclude them using LDAP filters.
- **Mail domains must be created in Mailcow before users can be synced.** The script will automatically skip users whose domains don't exist and log a warning message.

## Usage

### Prerequisites

Before starting the LDAP sync:

1. **Add mail domains in Mailcow**: Log into your Mailcow admin panel and add all domains that your LDAP users belong to (e.g., `example.com`, `company.org`). The sync will skip users whose domains don't exist.

### Installation

1. Create a `data/ldap` directory. SQLite database for synchronization will be stored there.
2. Extend your `docker-compose.override.yml` with an additional container:

    ```yaml
    ldap-mailcow:
        image: rorgray/ldap-mailcow
        network_mode: host
        container_name: mailcowcustomized_ldap-mailcow
        depends_on:
            - nginx-mailcow
        volumes:
            - ./data/ldap:/db:rw
            - ./data/conf/dovecot:/conf/dovecot:rw
            - ./data/conf/sogo:/conf/sogo:rw
        environment:
            - LDAP-MAILCOW_LDAP_URI=ldap://openldap
            - LDAP-MAILCOW_LDAP_BASE_DN=ou=users,dc=example,dc=local
            - LDAP-MAILCOW_LDAP_BIND_DN=cn=admin,dc=example,dc=local
            - LDAP-MAILCOW_LDAP_BIND_DN_PASSWORD=BindPassword
            - LDAP-MAILCOW_API_HOST=https://mailcow.example.local
            - LDAP-MAILCOW_API_KEY=XXXXXX-XXXXXX-XXXXXX-XXXXXX-XXXXXX
            - LDAP-MAILCOW_SYNC_INTERVAL=300
            - LDAP-MAILCOW_LDAP_FILTER=(&(objectClass=inetOrgPerson)(mail=*))
            - LDAP-MAILCOW_SOGO_LDAP_FILTER=objectClass='inetOrgPerson' AND mail=*
    ```

3. Configure environment variables:

    * `LDAP-MAILCOW_LDAP_URI` - LDAP (e.g., Active Directory) URI (must be reachable from within the container). The URIs are in syntax `protocol://host:port`. For example `ldap://localhost` or `ldaps://secure.domain.org`
    * `LDAP-MAILCOW_LDAP_BASE_DN` - base DN where user accounts can be found
    * `LDAP-MAILCOW_LDAP_BIND_DN` - bind DN of a special LDAP account that will be used to browse for users
    * `LDAP-MAILCOW_LDAP_BIND_DN_PASSWORD` - password for bind DN account
    * `LDAP-MAILCOW_API_HOST` - mailcow API url. Make sure it's enabled and accessible from within the container for both reads and writes
    * `LDAP-MAILCOW_API_KEY` - mailcow API key (read/write)
    * `LDAP-MAILCOW_SYNC_INTERVAL` - interval in seconds between LDAP synchronizations
    * **Optional** LDAP filters (see example above). SOGo uses special syntax, so you either have to **specify both or none**:
        * `LDAP-MAILCOW_LDAP_FILTER` - LDAP filter to apply, defaults to `(&(objectClass=user)(objectCategory=person))` for Active Directory. 
        **For OpenLDAP, use `(&(objectClass=inetOrgPerson)(mail=*))`** to ensure only users with email addresses are synced.
        * `LDAP-MAILCOW_SOGO_LDAP_FILTER` - LDAP filter to apply for SOGo ([special syntax](https://sogo.nu/files/docs/SOGoInstallationGuide.html#_authentication_using_ldap)), defaults to `objectClass='user' AND objectCategory='person'` for Active Directory. **For OpenLDAP, use `objectClass='inetOrgPerson' AND mail=*`**
    * `OPENLDAP-MAILCOW_IDENTIFIER` - **(Optional)** The LDAP attribute used to identify and authenticate users (default: `mail`). Uses the full email address for authentication.
    * `OPENLDAP-MAILCOW_EMAIL_ATTRIBUTE` - **(Optional)** The LDAP attribute containing the user's email address (default: `mail`). This is used by mailcow for account creation.
    * `OPENLDAP-MAILCOW_NAME_ATTRIBUTE` - **(Optional)** The LDAP attribute containing the user's display name (default: `cn`). This is shown as the user's name in mailcow.
    * `OPENLDAP-MAILCOW_AUTH_BIND_USERDN` - **(Advanced, optional)** Custom template for the DN used for LDAP user authentication binding (e.g., `mail=%n,ou=users,dc=example,dc=local`). **This is not usually required**—by default, this value is automatically generated from your `OPENLDAP-MAILCOW_IDENTIFIER` and `LDAP-MAILCOW_LDAP_BASE_DN`. Only set this if you need to override the default behavior for special LDAP directory structures.

4. Start additional container: `docker-compose up -d ldap-mailcow`
5. Check logs `docker-compose logs ldap-mailcow`
6. Restart dovecot and SOGo if necessary `docker-compose restart sogo-mailcow dovecot-mailcow`

### LDAP Fine-tuning

Container internally uses the following configuration templates:

* SOGo: `/templates/sogo/plist_ldap`
* dovecot: `/templates/dovecot/ldap/passdb.conf`

If necessary, you can edit and remount them through docker volumes. Some documentation on these files can be found here: [dovecot](https://doc.dovecot.org/configuration_manual/authentication/ldap/), [SOGo](https://sogo.nu/files/docs/SOGoInstallationGuide.html#_authentication_using_ldap)

## Limitations

### WebUI and SOGo Authentication

This tool automatically configures LDAP authentication for **Dovecot** (IMAP/SMTP/POP3). However, to enable LDAP login for **Mailcow Web UI** and **SOGo webmail**, you need to configure the Identity Provider in Mailcow's admin interface.

#### Prerequisites

Ensure your LDAP server is accessible from the Mailcow Docker network.

#### Configuration Steps

1. Log into the **Mailcow Admin Interface**
2. Navigate to: **System → Configuration → Access → Identity Provider**
3. Configure the following LDAP settings:

| Field | Value |
|-------|-------|
| **Identity Provider** | LDAP |
| **Host** | `openldap` |
| **Port** | `389` |
| **Base DN** | `ou=users,dc=example,dc=local` |
| **Username Field** | `mail` |
| **Filter** | `(&(objectClass=inetOrgPerson)(mail=*))` |
| **Attribute Field** | `uid` |
| **Bind DN** | `cn=admin,dc=example,dc=local` |
| **Bind Password** | `[BindPassword]` |

4. Click **Save** and restart the affected services:
   ```bash
   docker-compose restart sogo-mailcow dovecot-mailcow
   ```

After this configuration, users can log into:
- ✅ **Mailcow Web UI** - using their email address and LDAP password
- ✅ **SOGo Webmail** - using their email address and LDAP password
- ✅ **Email clients** (IMAP/SMTP) - using their email address and LDAP password

### Two-way sync

Users from your LDAP directory will be added (and deactivated if disabled/not found) to your mailcow database. Not vice-versa, and this is by design.