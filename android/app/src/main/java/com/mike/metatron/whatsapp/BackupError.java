package com.mike.metatron.whatsapp;

/**
 * Every way reading a WhatsApp backup can refuse, by the names in
 * archive/plans/whatsapp_backup_format_2026-10-26.md §§ 6–7.
 *
 * The user-facing text is code-written and carries no file content, key material or
 * account detail — it is safe to show and safe to log.
 */
public enum BackupError {
    KEY_FORMAT("key_format", "That isn't a 64-digit key — check it and enter it again."),
    WRONG_KEY("wrong_key", "The key doesn't match this backup."),
    INTEGRITY("integrity", "The backup file is damaged."),
    TRUNCATED("truncated", "The backup file is incomplete."),
    CRYPT14_END_TO_END_OFF("crypt14_end_to_end_off",
            "End-to-end backup is off — turn it on with the 64-digit key option."),
    UNKNOWN_FORMAT("unknown_format", "WhatsApp changed its backup format."),
    NOT_A_MESSAGE_DATABASE("not_a_message_database", "This backup is not a message database."),
    BEING_WRITTEN("being_written", "WhatsApp is still writing the backup — try again later."),
    INSUFFICIENT_SPACE("insufficient_space", "Not enough free space on the phone to read the backup."),
    SCHEMA_CHANGED("schema_changed", "WhatsApp changed how it stores messages."),
    // Not in the description's table, which assumes a file was found; needed so "nothing
    // there" is a named refusal rather than an empty result (§ 6.6).
    NO_BACKUP_FOUND("no_backup_found", "No WhatsApp backup was found on the phone."),
    BUSINESS_OUT_OF_SCOPE("whatsapp_business_out_of_scope", "WhatsApp Business backups aren't supported."),
    // Nightly increments — format description § 12.
    INCREMENT_FORMAT_UNKNOWN("increment_format_unknown", "WhatsApp changed its nightly backup format."),
    INCREMENT_MISSING_PART("increment_missing_part", "A nightly backup is missing a part the app needs."),
    INCREMENT_MALFORMED("increment_malformed", "A nightly backup is damaged."),
    INCREMENT_TOO_LARGE("increment_too_large", "A nightly backup is larger than expected."),
    INCREMENT_GAP("increment_gap", "A nightly backup is missing — the app catches up at the next full backup.");

    public final String code;
    public final String userText;

    BackupError(String code, String userText) {
        this.code = code;
        this.userText = userText;
    }
}
