# Perjury App (modern native version)

This is a modernised version of the Perjury one-time image viewer:

- 4-digit PIN entry
- Per-IP permanent blocking after successful view
- Optional global temporary lockout (`LOCK_MODE` = `all_ip` or `single_ip`)
- Token-based one-time view links with TTL
- JSON flat-file storage
- Simple i18n using `i18n/en.json`
- Admin panel for settings, blocks, tokens and log

It can run:

- Standalone via `python -m perjury_app`
- Embedded as a native app inside AppHost via the `create_perjury_blueprint()` factory.
