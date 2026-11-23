package com.mike.metatron.whatsapp;

/**
 * Turns an identifier into its FORMAT for the probe report — digits become '#', letters
 * become 'a' — so the screen shows the shape of a chat ID or person key and never the
 * number or name in it. Only fixed vocabulary survives: the domain after '@' when it is a
 * plain lowercase server name (s.whatsapp.net, g.us, lid), and a few URI schemes.
 */
final class ProbeMask {
    private static final String[] KEPT_PREFIXES = {
            "content://com.android.contacts/", "tel:", "mailto:", "name:", "content://", "https://", "http://",
    };

    private ProbeMask() {}

    static String format(String s) {
        if (s == null) return "(none)";
        if (s.isEmpty()) return "(empty)";
        String prefix = "";
        for (String p : KEPT_PREFIXES) {
            if (s.startsWith(p)) {
                prefix = p;
                s = s.substring(p.length());
                break;
            }
        }
        String domain = "";
        int at = s.lastIndexOf('@');
        if (at >= 0 && s.substring(at + 1).matches("[a-z][a-z.]{0,30}")) {
            domain = s.substring(at);
            s = s.substring(0, at);
        }
        StringBuilder b = new StringBuilder(prefix);
        for (int i = 0; i < s.length(); i++) {
            char c = s.charAt(i);
            if (Character.isDigit(c)) b.append('#');
            else if (Character.isLetter(c)) b.append('a');
            else b.append(c);
        }
        return compress(b.toString()) + domain;
    }

    /** Runs longer than 4 of '#' or 'a' become e.g. "#{11}", so the length shows but the line stays short. */
    private static String compress(String s) {
        StringBuilder b = new StringBuilder();
        int i = 0;
        while (i < s.length()) {
            char c = s.charAt(i);
            int j = i;
            while (j < s.length() && s.charAt(j) == c) j++;
            int run = j - i;
            if ((c == '#' || c == 'a') && run > 4) b.append(c).append('{').append(run).append('}');
            else for (int k = 0; k < run; k++) b.append(c);
            i = j;
        }
        return b.toString();
    }
}
