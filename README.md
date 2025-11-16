# openldap-mailcow

This is a fork of [Programmierus/ldap-mailcow](https://github.com/Programmierus/ldap-mailcow) with modifications to support connections to OpenLDAP.

## New Features in This Fork

This fork extends the original `ldap-mailcow` with the following OpenLDAP-specific enhancements:

- **Configurable User Identifier Attribute** - Use `uid` or `mail` to identify users instead of the Active Directory-specific `userPrincipalName`
- **Configurable Email and Name Attributes** - Specify which LDAP attributes contain email addresses and display names
- **OpenLDAP-Compatible Authentication** - Removed dependency on Active Directory's `userAccountControl` attribute; accounts are considered active if they exist in the directory
- **Automatic DN Generation** - Auth bind DN is automatically constructed from your identifier attribute and base DN
- **Flexible LDAP Schema Support** - Works with `inetOrgPerson` and other standard OpenLDAP object classes

## Quick Start for OpenLDAP Users

**Required Environment Variable:**

- `OPENLDAP-MAILCOW_IDENTIFIER` - The LDAP attribute used to identify users for authentication (default: `uid`)
  - `uid` - Use the user ID attribute (recommended for most OpenLDAP setups)
  - `mail` - Use the email address attribute

**Optional Environment Variables:**

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

**Note:** For OpenLDAP, account activation status is determined by whether the account exists in the LDAP directory and matches the configured filter. If you need to disable accounts, remove them from the LDAP directory or exclude them using LDAP filters.

## Usage

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
            - LDAP-MAILCOW_LDAP_BASE_DN=OU=Mail Users,DC=example,DC=local
            - LDAP-MAILCOW_LDAP_BIND_DN=CN=Bind DN,CN=Users,DC=example,DC=local
            - LDAP-MAILCOW_LDAP_BIND_DN_PASSWORD=BindPassword
            - LDAP-MAILCOW_API_HOST=https://mailcow.example.local
            - LDAP-MAILCOW_API_KEY=XXXXXX-XXXXXX-XXXXXX-XXXXXX-XXXXXX
            - LDAP-MAILCOW_SYNC_INTERVAL=300
            - LDAP-MAILCOW_LDAP_FILTER=(&(objectClass=inetOrgPerson)(mail=*))
            - LDAP-MAILCOW_SOGO_LDAP_FILTER=objectClass='inetOrgPerson' AND mail=*
            - OPENLDAP-MAILCOW_IDENTIFIER=uid
    ```

3. Configure environmental variables:

    * `LDAP-MAILCOW_LDAP_URI` - LDAP (e.g., Active Directory) URI (must be reachable from within the container). The URIs are in syntax `protocol://host:port`. For example `ldap://localhost` or `ldaps://secure.domain.org`
    * `LDAP-MAILCOW_LDAP_BASE_DN` - base DN where user accounts can be found
    * `LDAP-MAILCOW_LDAP_BIND_DN` - bind DN of a special LDAP account that will be used to browse for users
    * `LDAP-MAILCOW_LDAP_BIND_DN_PASSWORD` - password for bind DN account
    * `LDAP-MAILCOW_API_HOST` - mailcow API url. Make sure it's enabled and accessible from within the container for both reads and writes
    * `LDAP-MAILCOW_API_KEY` - mailcow API key (read/write)
    * `LDAP-MAILCOW_SYNC_INTERVAL` - interval in seconds between LDAP synchronizations
    * **Optional** LDAP filters (see example above). SOGo uses special syntax, so you either have to **specify both or none**:
        * `LDAP-MAILCOW_LDAP_FILTER` - LDAP filter to apply, defaults to `(&(objectClass=user)(objectCategory=person))` for Active Directory. **For OpenLDAP, use `(&(objectClass=inetOrgPerson)(mail=*))`** to ensure only users with email addresses are synced.
        * `LDAP-MAILCOW_SOGO_LDAP_FILTER` - LDAP filter to apply for SOGo ([special syntax](https://sogo.nu/files/docs/SOGoInstallationGuide.html#_authentication_using_ldap)), defaults to `objectClass='user' AND objectCategory='person'` for Active Directory. **For OpenLDAP, use `objectClass='inetOrgPerson' AND mail=*`**
    * `OPENLDAP-MAILCOW_IDENTIFIER` - **(Optional)** The LDAP attribute used to identify and authenticate users (default: `uid`). Common values: `uid` or `mail`
    * `OPENLDAP-MAILCOW_EMAIL_ATTRIBUTE` - **(Optional)** The LDAP attribute containing the user's email address (default: `mail`). This is used by mailcow for account creation.
    * `OPENLDAP-MAILCOW_NAME_ATTRIBUTE` - **(Optional)** The LDAP attribute containing the user's display name (default: `cn`). This is shown as the user's name in mailcow.
    * `OPENLDAP-MAILCOW_AUTH_BIND_USERDN` - **(Advanced, optional)** Custom template for the DN used for LDAP user authentication binding (e.g., `uid=%n,ou=users,dc=example,dc=local`). **This is not usually required**—by default, this value is automatically generated from your `OPENLDAP-MAILCOW_IDENTIFIER` and `LDAP-MAILCOW_LDAP_BASE_DN`. Only set this if you need to override the default behavior for special LDAP directory structures.

4. Start additional container: `docker-compose up -d ldap-mailcow`
5. Check logs `docker-compose logs ldap-mailcow`
6. Restart dovecot and SOGo if necessary `docker-compose restart sogo-mailcow dovecot-mailcow`

### LDAP Fine-tuning

Container internally uses the following configuration templates:

* SOGo: `/templates/sogo/plist_ldap`
* dovecot: `/templates/dovecot/ldap/passdb.conf`

If necessary, you can edit and remount them through docker volumes. Some documentation on these files can be found here: [dovecot](https://doc.dovecot.org/configuration_manual/authentication/ldap/), [SOGo](https://sogo.nu/files/docs/SOGoInstallationGuide.html#_authentication_using_ldap)

## Limitations

### WebUI and EAS authentication

This tool enables authentication for Dovecot and SOGo, which means you will be able to log into POP3, SMTP, IMAP, and SOGo Web-Interface. **You will not be able to log into mailcow UI or EAS using your LDAP credentials by default.**

As a workaround, you can hook IMAP authentication directly to mailcow by adding the following code above [this line](https://github.com/mailcow/mailcow-dockerized/blob/48b74d77a0c39bcb3399ce6603e1ad424f01fc3e/data/web/inc/functions.inc.php#L608):

```php
    $mbox = imap_open ("{dovecot:993/imap/ssl/novalidate-cert}INBOX", $user, $pass);
    if ($mbox != false) {
        imap_close($mbox);
        return "user";
    }
```

As a side-effect, It will also allow logging into mailcow UI using mailcow app passwords (since they are valid for IMAP). **It is not a supported solution with mailcow and has to be done only at your own risk!**

### Two-way sync

Users from your LDAP directory will be added (and deactivated if disabled/not found) to your mailcow database. Not vice-versa, and this is by design.