package com.mike.metatron.whatsapp;

/**
 * The file prefix: a length byte, an optional feature-table marker, and the protobuf
 * header (format description §§ 3–4).
 *
 * Only what decryption needs is extracted — which cipher block is present, and the
 * crypt15 IV. Field 4 (`info`, which carries the phone-number suffix) is skipped unread.
 * Anything this parser does not fully understand is `unknown_format`, never a fallback.
 */
final class BackupHeader {
    static final int IV_LENGTH = 16;

    /** Offset of the first ciphertext byte. */
    final int dataStart;
    final byte[] iv;
    final boolean featureMarker;

    private BackupHeader(int dataStart, byte[] iv, boolean featureMarker) {
        this.dataStart = dataStart;
        this.iv = iv;
        this.featureMarker = featureMarker;
    }

    /** The most prefix bytes parsing can need: the length byte, the marker, a 255-byte header. */
    static final int MAX_PREFIX = 2 + 255;

    /**
     * @param prefix   the first bytes of the file (up to {@link #MAX_PREFIX})
     * @param prefixLen how many of them are valid
     */
    static BackupHeader parse(byte[] prefix, int prefixLen) throws BackupException {
        if (prefixLen < 2) throw new BackupException(BackupError.UNKNOWN_FORMAT);
        int n = prefix[0] & 0xff;
        boolean marker = prefix[1] == 0x01;
        int start = marker ? 2 : 1;
        int end = start + n;
        if (end > prefixLen) throw new BackupException(BackupError.UNKNOWN_FORMAT);

        Reader r = new Reader(prefix, start, end);
        boolean sawC14 = false;
        byte[] iv = null;
        while (r.more()) {
            long key = r.varint();
            int field = (int) (key >>> 3);
            int wire = (int) (key & 7);
            if (field == 2) {
                if (wire != 2) throw new BackupException(BackupError.UNKNOWN_FORMAT);
                r.bytes();
                sawC14 = true;
            } else if (field == 3) {
                if (wire != 2 || iv != null) throw new BackupException(BackupError.UNKNOWN_FORMAT);
                iv = parseC15(r.bytes());
            } else {
                r.skip(field, wire);
            }
        }
        if (sawC14 && iv != null) throw new BackupException(BackupError.UNKNOWN_FORMAT);
        if (sawC14) throw new BackupException(BackupError.CRYPT14_END_TO_END_OFF);
        if (iv == null) throw new BackupException(BackupError.UNKNOWN_FORMAT);
        return new BackupHeader(end, iv, marker);
    }

    private static byte[] parseC15(byte[] msg) throws BackupException {
        Reader r = new Reader(msg, 0, msg.length);
        byte[] iv = null;
        while (r.more()) {
            long key = r.varint();
            int field = (int) (key >>> 3);
            int wire = (int) (key & 7);
            if (field == 1) {
                if (wire != 2 || iv != null) throw new BackupException(BackupError.UNKNOWN_FORMAT);
                iv = r.bytes();
            } else {
                r.skip(field, wire);
            }
        }
        if (iv == null || iv.length != IV_LENGTH) throw new BackupException(BackupError.UNKNOWN_FORMAT);
        return iv;
    }

    /** Protobuf wire-format reader over a byte range — varint, fixed32/64, length-delimited. */
    private static final class Reader {
        private final byte[] buf;
        private int pos;
        private final int end;

        Reader(byte[] buf, int start, int end) {
            this.buf = buf;
            this.pos = start;
            this.end = end;
        }

        boolean more() {
            return pos < end;
        }

        long varint() throws BackupException {
            long v = 0;
            for (int shift = 0; shift < 64; shift += 7) {
                if (pos >= end) throw new BackupException(BackupError.UNKNOWN_FORMAT);
                int b = buf[pos++] & 0xff;
                v |= (long) (b & 0x7f) << shift;
                if ((b & 0x80) == 0) return v;
            }
            throw new BackupException(BackupError.UNKNOWN_FORMAT);
        }

        byte[] bytes() throws BackupException {
            long len = varint();
            if (len < 0 || len > end - pos) throw new BackupException(BackupError.UNKNOWN_FORMAT);
            byte[] out = new byte[(int) len];
            System.arraycopy(buf, pos, out, 0, out.length);
            pos += out.length;
            return out;
        }

        /** Skips an unknown field (§ 4: ignore unknown fields). Field 0 and groups are malformed. */
        void skip(int field, int wire) throws BackupException {
            if (field == 0) throw new BackupException(BackupError.UNKNOWN_FORMAT);
            switch (wire) {
                case 0: varint(); return;
                case 1: advance(8); return;
                case 2: {
                    long len = varint();
                    if (len < 0 || len > end - pos) throw new BackupException(BackupError.UNKNOWN_FORMAT);
                    pos += (int) len;
                    return;
                }
                case 5: advance(4); return;
                default: throw new BackupException(BackupError.UNKNOWN_FORMAT);
            }
        }

        private void advance(int n) throws BackupException {
            if (n > end - pos) throw new BackupException(BackupError.UNKNOWN_FORMAT);
            pos += n;
        }
    }
}
