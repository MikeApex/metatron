package com.mike.metatron.whatsapp;

/**
 * A named refusal. The message is the error code plus, at most, a code-written detail
 * (a schema name, a byte count) — never key material, the phone-number suffix or any
 * decrypted content.
 */
public final class BackupException extends Exception {
    public final BackupError error;

    public BackupException(BackupError error) {
        super(error.code);
        this.error = error;
    }

    public BackupException(BackupError error, String detail) {
        super(error.code + ": " + detail);
        this.error = error;
    }
}
